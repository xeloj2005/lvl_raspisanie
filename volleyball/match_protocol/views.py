from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from tournament.models import Match

from .services import (
    add_point,
    build_existing_map,
    build_lineup_state,
    build_post_state,
    build_scoreboard_context,
    configure_set_start,
    confirm_set_result,
    get_lineup_candidates,
    get_or_build_current_protocol_set,
    get_or_create_lineup,
    get_or_create_session,
    get_or_create_squad,
    get_roster_players_for_side,
    get_team_by_side,
    make_substitution,
    save_lineup,
    save_squad,
    take_timeout,
    undo_last_event,
build_match_summary_context
)


def get_match_for_protocol_or_404(match_id):
    return get_object_or_404(
        Match.objects.select_related("tournament", "team_a", "team_b", "venue"),
        pk=match_id,
    )


def build_rows(roster_players, existing_map, post_state):
    rows = []

    for rp in roster_players:
        existing = existing_map.get(rp.id)
        post_row = post_state.get(rp.id) if post_state else None

        if post_row:
            match_number = post_row.get("match_number", "")
            is_libero = post_row.get("is_libero", False)
            is_captain = post_row.get("is_captain", False)
        elif existing:
            match_number = existing.match_number or ""
            is_libero = existing.is_libero
            is_captain = existing.is_captain
        else:
            match_number = ""
            is_libero = False
            is_captain = False

        rows.append({
            "id": rp.id,
            "full_name": rp.player.full_name,
            "match_number": match_number,
            "is_libero": is_libero,
            "is_captain": is_captain,
        })

    return rows


def squad_step(request, match_id, side):
    side = (side or "").upper()
    if side not in ("A", "B"):
        raise Http404("Неизвестная сторона.")

    match = get_match_for_protocol_or_404(match_id)

    session = get_or_create_session(match)
    squad = get_or_create_squad(session, side)
    roster_players = get_roster_players_for_side(match, side)

    post_state = None

    if request.method == "POST":
        try:
            save_squad(match, side, request.POST)

            if side == "A":
                messages.success(request, f"Заявка команды «{match.team_a.name}» сохранена.")
                return redirect("match_protocol:squad_step", match_id=match.id, side="B")

            messages.success(request, f"Заявка команды «{match.team_b.name}» сохранена.")
            return redirect("match_protocol:lineup_step", match_id=match.id, side="A")

        except ValidationError as exc:
            messages.error(request, exc.message)
            post_state = build_post_state(roster_players, request.POST)

    team = get_team_by_side(match, side)
    existing_map = build_existing_map(squad)

    context = {
        "match": match,
        "session": session,
        "squad": squad,
        "side": side,
        "team": team,
        "team_name": team.name,
        "rows": build_rows(roster_players, existing_map, post_state),
        "step_title": f"Заявка команды «{team.name}»",
        "step_hint": "Укажите игровые номера и отметьте либеро и капитана. Капитан может быть только один.",
    }
    return render(request, "match_protocol/squad_step.html", context)


def lineup_step(request, match_id, side):
    side = (side or "").upper()
    if side not in ("A", "B"):
        raise Http404("Неизвестная сторона.")

    match = get_match_for_protocol_or_404(match_id)
    session = get_or_create_session(match)
    team = get_team_by_side(match, side)

    if side == "A" and not session.squad_b_completed:
        return redirect("match_protocol:squad_step", match_id=match.id, side="B")

    lineup = get_or_create_lineup(session, side, set_number=get_or_build_current_protocol_set(match)[1].set_number)
    candidates = list(get_lineup_candidates(match, side))

    if request.method == "POST":
        try:
            current_set_number = get_or_build_current_protocol_set(match)[1].set_number
            save_lineup(match, side, request.POST, set_number=current_set_number)

            if side == "A":
                return redirect("match_protocol:lineup_step", match_id=match.id, side="B")

            current_set_number = get_or_build_current_protocol_set(match)[1].set_number

            if current_set_number in (1, 5):
                return redirect("match_protocol:set_setup_step", match_id=match.id, set_number=current_set_number)

            return redirect("match_protocol:scoreboard", match_id=match.id)

        except ValidationError as exc:
            messages.error(request, exc.message)

    position_map = build_lineup_state(lineup)

    positions = []
    for pos in range(1, 7):
        positions.append({
            "position": pos,
            "entry_id": position_map.get(pos, {}).get("entry_id", ""),
            "number": position_map.get(pos, {}).get("number", ""),
            "name": position_map.get(pos, {}).get("name", ""),
        })

    cards = []
    used_entry_ids = {item["entry_id"] for item in positions if item["entry_id"]}
    for player in candidates:
        cards.append({
            "entry_id": player.id,
            "number": player.match_number,
            "name": player.roster_player.player.full_name,
            "used": player.id in used_entry_ids,
        })

    context = {
        "match": match,
        "session": session,
        "side": side,
        "team": team,
        "team_name": team.name,
        "positions": positions,
        "cards": cards,
        "step_title": f"Расстановка команды «{team.name}»",
        "step_hint": "Нажимайте на карточки игроков снизу. Они будут занимать позиции на поле по очереди с 1 по 6.",
    }
    return render(request, "match_protocol/lineup_step.html", context)


def set_setup_step(request, match_id, set_number):
    match = get_match_for_protocol_or_404(match_id)
    session = get_or_create_session(match)

    if set_number not in (1, 5):
        raise Http404("Настройка нужна только для 1-го и 5-го сетов.")

    if request.method == "POST":
        side_a_is_left = request.POST.get("side_a_is_left") == "1"
        first_server_side = request.POST.get("first_server_side")

        if first_server_side not in ("A", "B"):
            messages.error(request, "Выберите, какая команда подаёт первой.")
        else:
            try:
                configure_set_start(
                    match=match,
                    set_number=set_number,
                    side_a_is_left=side_a_is_left,
                    first_server_side=first_server_side,
                )
                return redirect("match_protocol:scoreboard", match_id=match.id)
            except ValidationError as exc:
                messages.error(request, exc.message)

    context = {
        "match": match,
        "set_number": set_number,
    }
    return render(request, "match_protocol/set_setup_step.html", context)


def scoreboard(request, match_id):
    match = get_match_for_protocol_or_404(match_id)

    try:
        context = build_scoreboard_context(match)
    except ValidationError as exc:
        messages.error(request, exc.message)
        current_set_number = get_or_build_current_protocol_set(match)[1].set_number

        if current_set_number in (1, 5):
            return redirect("match_protocol:set_setup_step", match_id=match.id, set_number=current_set_number)

        return redirect("match_protocol:lineup_step", match_id=match.id, side="A")

    context["match"] = match
    return render(request, "match_protocol/scoreboard.html", context)


@require_POST
def action_add_point(request, match_id, side):
    match = get_match_for_protocol_or_404(match_id)
    try:
        add_point(match, side.upper())
    except ValidationError as exc:
        messages.error(request, exc.message)
    return redirect("match_protocol:scoreboard", match_id=match.id)


@require_POST
def action_timeout(request, match_id, side):
    match = get_match_for_protocol_or_404(match_id)
    try:
        take_timeout(match, side.upper())
    except ValidationError as exc:
        messages.error(request, exc.message)
    return redirect("match_protocol:scoreboard", match_id=match.id)


@require_POST
def action_substitution(request, match_id, side):
    match = get_match_for_protocol_or_404(match_id)
    try:
        make_substitution(
            match=match,
            side=side.upper(),
            out_player_id=request.POST.get("out_player_id"),
            in_player_id=request.POST.get("in_player_id"),
        )
    except ValidationError as exc:
        messages.error(request, exc.message)
    return redirect("match_protocol:scoreboard", match_id=match.id)


@require_POST
def action_undo(request, match_id):
    match = get_match_for_protocol_or_404(match_id)
    try:
        undo_last_event(match)
    except ValidationError as exc:
        messages.error(request, exc.message)
    return redirect("match_protocol:scoreboard", match_id=match.id)


@require_POST
def action_confirm_set(request, match_id):
    match = get_match_for_protocol_or_404(match_id)

    try:
        result = confirm_set_result(match)
    except ValidationError as exc:
        messages.error(request, exc.message)
        return redirect("match_protocol:scoreboard", match_id=match.id)

    if result["match_finished"]:
        messages.success(request, "Матч завершён и результат сохранён.")
        return redirect("match_protocol:protocol_summary", match_id=match.id)

    next_set_number = result["next_set_number"]
    messages.success(request, f"Сет завершён. Подготовьте расстановку на {next_set_number}-й сет.")
    return redirect("match_protocol:lineup_step", match_id=match.id, side="A")


def protocol_summary(request, match_id):
    match = get_match_for_protocol_or_404(match_id)
    context = build_match_summary_context(match)
    context["match"] = match
    return render(request, "match_protocol/protocol_summary.html", context)