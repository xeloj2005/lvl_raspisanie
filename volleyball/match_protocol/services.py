from copy import deepcopy

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from tournament.models import TournamentTeamRoster
from tournament.views import check_and_generate_playoff

from .models import (
    MatchLineup,
    MatchLineupPosition,
    MatchProtocolEvent,
    MatchProtocolSession,
    MatchProtocolSet,
    MatchProtocolSetLineup,
    MatchSquad,
    MatchSquadPlayer,
)


SETS_TO_WIN_DEFAULT = 3
REGULAR_SET_POINTS = 25
DECIDING_SET_POINTS = 15
MAX_TIMEOUTS_PER_SET = 2
MAX_SUBSTITUTIONS_PER_SET = 6


# -------------------------
# Базовые helpers существующего потока
# -------------------------

def get_or_create_session(match):
    session, _ = MatchProtocolSession.objects.get_or_create(match=match)
    return session


def get_team_by_side(match, side):
    return match.team_a if side == "A" else match.team_b


def other_side(side):
    return "B" if side == "A" else "A"


def get_or_create_squad(session, side):
    team = get_team_by_side(session.match, side)
    tournament_roster = TournamentTeamRoster.objects.get(
        tournament=session.match.tournament,
        team=team,
    )

    squad, _ = MatchSquad.objects.get_or_create(
        session=session,
        side=side,
        defaults={"tournament_roster": tournament_roster},
    )

    if squad.tournament_roster_id != tournament_roster.id:
        squad.tournament_roster = tournament_roster
        squad.save(update_fields=["tournament_roster"])

    return squad


def get_roster_players_for_side(match, side):
    team = get_team_by_side(match, side)
    tournament_roster = TournamentTeamRoster.objects.get(
        tournament=match.tournament,
        team=team,
    )
    return tournament_roster.roster_players.select_related("player").all().order_by("player__full_name")


def build_existing_map(squad):
    entries = squad.players.select_related("roster_player__player").all()
    return {entry.roster_player_id: entry for entry in entries}


def build_post_state(roster_players, post_data):
    state = {}
    for rp in roster_players:
        state[rp.id] = {
            "is_active": post_data.get(f"active_{rp.id}") == "1",
            "match_number": post_data.get(f"number_{rp.id}", "").strip(),
            "is_libero": post_data.get(f"libero_{rp.id}") == "1",
            "is_captain": post_data.get(f"captain_{rp.id}") == "1",
        }
    return state


def parse_number(raw_value):
    raw_value = (raw_value or "").strip()
    if not raw_value:
        return None
    try:
        value = int(raw_value)
    except ValueError:
        raise ValidationError("Номер игрока должен быть целым числом.")
    if value <= 0:
        raise ValidationError("Номер игрока должен быть положительным.")
    return value


def build_payload(roster_players, post_data):
    payload = []

    for rp in roster_players:
        item = {
            "roster_player": rp,
            "is_active": post_data.get(f"active_{rp.id}") == "1",
            "match_number": parse_number(post_data.get(f"number_{rp.id}", "")),
            "is_libero": post_data.get(f"libero_{rp.id}") == "1",
            "is_captain": post_data.get(f"captain_{rp.id}") == "1",
        }
        payload.append(item)

    return payload


def validate_payload(payload):
    active_items = [item for item in payload if item["is_active"]]

    if len(active_items) < 6:
        raise ValidationError("В заявке должно быть минимум 6 игроков.")

    captains = [item for item in active_items if item["is_captain"]]
    if len(captains) != 1:
        raise ValidationError("Должен быть выбран ровно один капитан.")

    liberos = [item for item in active_items if item["is_libero"]]
    if len(liberos) > 2:
        raise ValidationError("Допускается не более двух либеро.")

    numbers = []
    for item in active_items:
        if item["match_number"] is None:
            raise ValidationError("У каждого игрока в заявке должен быть указан номер.")
        numbers.append(item["match_number"])

    if len(numbers) != len(set(numbers)):
        raise ValidationError("Номера игроков не должны повторяться.")

    for item in payload:
        if not item["is_active"] and (item["is_libero"] or item["is_captain"]):
            raise ValidationError("Капитан и либеро должны быть включены в заявку.")

    return True


@transaction.atomic
def save_squad(match, side, post_data):
    session = get_or_create_session(match)
    squad = get_or_create_squad(session, side)
    roster_players = get_roster_players_for_side(match, side)

    payload = build_payload(roster_players, post_data)
    validate_payload(payload)

    squad.players.all().delete()

    MatchSquadPlayer.objects.bulk_create([
        MatchSquadPlayer(
            squad=squad,
            roster_player=item["roster_player"],
            is_active=item["is_active"],
            match_number=item["match_number"],
            is_libero=item["is_libero"],
            is_captain=item["is_captain"],
        )
        for item in payload
    ])

    squad.is_submitted = True
    squad.submitted_at = timezone.now()
    squad.save(update_fields=["is_submitted", "submitted_at"])

    if side == "A":
        session.squad_a_completed = True
        session.current_step = MatchProtocolSession.STEP_SQUAD_B
        session.save(update_fields=["squad_a_completed", "current_step", "updated_at"])
    else:
        session.squad_b_completed = True
        session.current_step = MatchProtocolSession.STEP_LINEUP_A
        session.save(update_fields=["squad_b_completed", "current_step", "updated_at"])

    return session, squad


def get_or_create_lineup(session, side, set_number=1):
    lineup, _ = MatchLineup.objects.get_or_create(
        session=session,
        side=side,
        set_number=set_number,
    )
    return lineup


def get_lineup_candidates(match, side):
    session = get_or_create_session(match)
    squad = get_or_create_squad(session, side)

    return (
        squad.players
        .select_related("roster_player__player")
        .filter(is_active=True, is_libero=False)
        .order_by("match_number", "id")
    )


def build_lineup_state(lineup):
    positions = {}
    for item in lineup.positions.select_related("squad_player__roster_player__player").all():
        positions[item.position] = {
            "entry_id": item.squad_player_id,
            "number": item.squad_player.match_number,
            "name": item.squad_player.roster_player.player.full_name,
        }
    return positions


def validate_lineup_payload(candidate_map, payload):
    filled = []
    used_entry_ids = set()

    for position in range(1, 7):
        raw_value = (payload.get(position) or "").strip()
        if not raw_value:
            raise ValidationError("Нужно заполнить все 6 позиций на поле.")

        try:
            entry_id = int(raw_value)
        except ValueError:
            raise ValidationError("Некорректный состав расстановки.")

        if entry_id in used_entry_ids:
            raise ValidationError("Один и тот же игрок не может стоять в двух позициях.")

        squad_player = candidate_map.get(entry_id)
        if not squad_player:
            raise ValidationError("В расстановке найден недопустимый игрок.")

        if not squad_player.is_active:
            raise ValidationError("В расстановке может быть только игрок из заявки.")

        if squad_player.is_libero:
            raise ValidationError("Либеро нельзя ставить в стартовую расстановку.")

        used_entry_ids.add(entry_id)
        filled.append((position, squad_player))

    if len(filled) != 6:
        raise ValidationError("На поле должно быть ровно 6 игроков.")

    return filled


@transaction.atomic
def save_lineup(match, side, post_data, set_number=1):
    session = get_or_create_session(match)
    lineup = get_or_create_lineup(session, side, set_number=set_number)

    candidates = list(get_lineup_candidates(match, side))
    candidate_map = {item.id: item for item in candidates}

    payload = {
        position: post_data.get(f"position_{position}", "")
        for position in range(1, 7)
    }

    validated = validate_lineup_payload(candidate_map, payload)

    lineup.positions.all().delete()

    MatchLineupPosition.objects.bulk_create([
        MatchLineupPosition(
            lineup=lineup,
            position=position,
            squad_player=squad_player,
        )
        for position, squad_player in validated
    ])

    lineup.is_submitted = True
    lineup.submitted_at = timezone.now()
    lineup.save(update_fields=["is_submitted", "submitted_at"])

    if side == "A":
        session.lineup_a_completed = True
        session.current_step = MatchProtocolSession.STEP_LINEUP_B
        session.save(update_fields=["lineup_a_completed", "current_step", "updated_at"])
    else:
        session.lineup_b_completed = True
        session.current_step = MatchProtocolSession.STEP_PROTOCOL
        session.save(update_fields=["lineup_b_completed", "current_step", "updated_at"])

    return session, lineup


# -------------------------
# Новый блок: сеты и табло
# -------------------------

def get_sets_to_win(session):
    return getattr(session, "sets_to_win", None) or SETS_TO_WIN_DEFAULT


def get_target_points_for_set(set_number):
    return DECIDING_SET_POINTS if set_number == 5 else REGULAR_SET_POINTS


def get_or_create_protocol_set(session, set_number):
    protocol_set, _ = MatchProtocolSet.objects.get_or_create(
        session=session,
        set_number=set_number,
        defaults={
            "side_a_is_left": True,
            "first_server_side": "A",
        },
    )
    return protocol_set


def get_starting_lineup_from_saved_lineup(session, side, set_number):
    saved_lineup = MatchLineup.objects.filter(
        session=session,
        side=side,
        set_number=set_number,
        is_submitted=True,
    ).first()
    if not saved_lineup:
        raise ValidationError("Сначала нужно сохранить расстановку на сет.")

    positions = saved_lineup.positions.select_related(
        "squad_player__roster_player__player"
    ).order_by("position")

    if positions.count() != 6:
        raise ValidationError("Расстановка должна содержать 6 игроков.")

    return positions


@transaction.atomic
def initialize_protocol_set_from_saved_lineups(match, set_number, side_a_is_left=True, first_server_side="A"):
    session = get_or_create_session(match)
    protocol_set = get_or_create_protocol_set(session, set_number)

    if protocol_set.lineups.exists():
        return protocol_set

    protocol_set.side_a_is_left = side_a_is_left
    protocol_set.first_server_side = first_server_side
    protocol_set.save(update_fields=["side_a_is_left", "first_server_side"])

    created = []

    for side in ("A", "B"):
        starting_positions = get_starting_lineup_from_saved_lineup(session, side, set_number)
        for item in starting_positions:
            created.append(
                MatchProtocolSetLineup(
                    protocol_set=protocol_set,
                    side=side,
                    position=item.position,
                    squad_player=item.squad_player,
                )
            )

    MatchProtocolSetLineup.objects.bulk_create(created)
    return protocol_set


def get_current_set_number(session):
    last_finished = session.sets.filter(is_finished=True).count()
    return last_finished + 1


def get_or_build_current_protocol_set(match):
    session = get_or_create_session(match)
    set_number = get_current_set_number(session)
    protocol_set = get_or_create_protocol_set(session, set_number)
    return session, protocol_set


def get_initial_rotation(protocol_set, side):
    positions = list(
        protocol_set.lineups
        .filter(side=side)
        .select_related("squad_player__roster_player__player")
        .order_by("position")
    )

    if len(positions) != 6:
        raise ValidationError("Для этого сета не заполнена стартовая расстановка.")

    rotation = {}
    for item in positions:
        rotation[item.position] = item.squad_player
    return rotation


def rotate_clockwise(rotation):
    old = dict(rotation)
    return {
        1: old[2],
        2: old[3],
        3: old[4],
        4: old[5],
        5: old[6],
        6: old[1],
    }


def get_captain_number_for_side(match, side):
    session = get_or_create_session(match)
    squad = get_or_create_squad(session, side)
    player = squad.players.filter(is_captain=True, is_active=True).first()
    return player.match_number if player else None


def get_libero_numbers_for_side(match, side):
    session = get_or_create_session(match)
    squad = get_or_create_squad(session, side)
    return list(
        squad.players.filter(is_libero=True, is_active=True)
        .order_by("match_number")
        .values_list("match_number", flat=True)
    )


def get_available_substitutes_for_side(state, side):
    current_ids = {player.id for player in state["rotation"][side].values()}
    available = []

    for item in state["all_active_non_libero"][side]:
        if item.id in current_ids:
            continue
        if item.id in state["bench_entered_ids"][side]:
            continue

        available.append(item)

    return available


def get_team_sets_won_from_finished_sets(session):
    sets_a = 0
    sets_b = 0

    for protocol_set in session.sets.filter(is_finished=True).order_by("set_number"):
        state = reconstruct_set_state(protocol_set)
        if state["score"]["A"] > state["score"]["B"]:
            sets_a += 1
        else:
            sets_b += 1

    return sets_a, sets_b


def reconstruct_set_state(protocol_set):
    rotation = {
        "A": get_initial_rotation(protocol_set, "A"),
        "B": get_initial_rotation(protocol_set, "B"),
    }

    all_active_non_libero = {
        "A": list(
            protocol_set.session.squads.get(side="A").players
            .select_related("roster_player__player")
            .filter(is_active=True, is_libero=False)
            .order_by("match_number", "id")
        ),
        "B": list(
            protocol_set.session.squads.get(side="B").players
            .select_related("roster_player__player")
            .filter(is_active=True, is_libero=False)
            .order_by("match_number", "id")
        ),
    }

    state = {
        "score": {"A": 0, "B": 0},
        "server_side": protocol_set.first_server_side,
        "rotation": rotation,
        "timeouts": {"A": 0, "B": 0},
        "substitutions": {"A": 0, "B": 0},
        "bench_entered_ids": {"A": set(), "B": set()},
        "point_history": [],
        "timeout_history": [],
        "substitution_history": [],
        "side_a_is_left": protocol_set.side_a_is_left,
        "side_switch_triggered": protocol_set.side_switch_triggered,
        "all_active_non_libero": all_active_non_libero,
        "is_finished": protocol_set.is_finished,
    }

    events = list(protocol_set.events.order_by("sequence_number", "id"))

    for event in events:
        if event.event_type == MatchProtocolEvent.EVENT_POINT:
            side = event.side
            opponent = other_side(side)

            state["score"][side] += 1

            server_number = state["rotation"][state["server_side"]][1].match_number
            state["point_history"].append({
                "sequence": event.sequence_number,
                "side": side,
                "score_a": state["score"]["A"],
                "score_b": state["score"]["B"],
                "server_side": state["server_side"],
                "server_number": server_number,
            })

            if side != state["server_side"]:
                state["server_side"] = side
                state["rotation"][side] = rotate_clockwise(state["rotation"][side])

            if protocol_set.set_number == 5 and not state["side_switch_triggered"]:
                if state["score"]["A"] >= 8 or state["score"]["B"] >= 8:
                    state["side_a_is_left"] = not state["side_a_is_left"]
                    state["side_switch_triggered"] = True

        elif event.event_type == MatchProtocolEvent.EVENT_TIMEOUT:
            side = event.side
            state["timeouts"][side] += 1
            state["timeout_history"].append({
                "sequence": event.sequence_number,
                "side": side,
                "score_a": state["score"]["A"],
                "score_b": state["score"]["B"],
            })

        elif event.event_type == MatchProtocolEvent.EVENT_SUBSTITUTION:
            side = event.side
            payload = event.payload or {}

            out_id = payload.get("out_player_id")
            in_id = payload.get("in_player_id")

            out_player = None
            out_position = None

            for pos, player in state["rotation"][side].items():
                if player.id == out_id:
                    out_player = player
                    out_position = pos
                    break

            if out_player is None or out_position is None:
                raise ValidationError("Некорректная замена в журнале событий.")

            in_player = next(
                (p for p in state["all_active_non_libero"][side] if p.id == in_id),
                None
            )
            if in_player is None:
                raise ValidationError("Некорректный входящий игрок в журнале событий.")

            state["rotation"][side][out_position] = in_player
            state["substitutions"][side] += 1
            state["bench_entered_ids"][side].add(in_player.id)

            state["substitution_history"].append({
                "sequence": event.sequence_number,
                "side": side,
                "score_a": state["score"]["A"],
                "score_b": state["score"]["B"],
                "out_number": out_player.match_number,
                "in_number": in_player.match_number,
            })

        elif event.event_type == MatchProtocolEvent.EVENT_SIDE_SWITCH:
            state["side_a_is_left"] = not state["side_a_is_left"]
            state["side_switch_triggered"] = True

        elif event.event_type == MatchProtocolEvent.EVENT_SET_FINISH:
            state["is_finished"] = True

    return state


def is_valid_set_finish(set_number, score_a, score_b):
    target = get_target_points_for_set(set_number)
    max_score = max(score_a, score_b)
    min_score = min(score_a, score_b)
    return max_score >= target and (max_score - min_score) >= 2


def get_next_event_sequence(protocol_set):
    last = protocol_set.events.order_by("-sequence_number").first()
    return 1 if last is None else last.sequence_number + 1


def create_event(protocol_set, event_type, side=None, payload=None):
    state = reconstruct_set_state(protocol_set)
    server_number_before = state["rotation"][state["server_side"]][1].match_number

    event = MatchProtocolEvent.objects.create(
        protocol_set=protocol_set,
        sequence_number=get_next_event_sequence(protocol_set),
        event_type=event_type,
        side=side,
        score_a_before=state["score"]["A"],
        score_b_before=state["score"]["B"],
        score_a_after=state["score"]["A"],
        score_b_after=state["score"]["B"],
        server_side_before=state["server_side"],
        server_number_before=server_number_before,
        payload=payload or {},
    )

    updated = reconstruct_set_state(protocol_set)

    event.score_a_after = updated["score"]["A"]
    event.score_b_after = updated["score"]["B"]
    event.save(update_fields=["score_a_after", "score_b_after"])

    return event


def ensure_protocol_set_initialized(match):
    session, protocol_set = get_or_build_current_protocol_set(match)

    if not protocol_set.lineups.exists():
        if protocol_set.set_number in (1, 5):
            raise ValidationError("Для этого сета нужно сначала выбрать сторону и первую подачу.")
        previous = session.sets.filter(set_number=protocol_set.set_number - 1).first()
        if not previous:
            raise ValidationError("Невозможно автоматически инициализировать сет.")

        initialize_protocol_set_from_saved_lineups(
            match=match,
            set_number=protocol_set.set_number,
            side_a_is_left=not previous.side_a_is_left,
            first_server_side=other_side(previous.first_server_side),
        )
        protocol_set.refresh_from_db()

    return session, protocol_set


@transaction.atomic
def configure_set_start(match, set_number, side_a_is_left, first_server_side):
    session = get_or_create_session(match)
    protocol_set = get_or_create_protocol_set(session, set_number)

    initialize_protocol_set_from_saved_lineups(
        match=match,
        set_number=set_number,
        side_a_is_left=side_a_is_left,
        first_server_side=first_server_side,
    )
    return protocol_set


@transaction.atomic
def add_point(match, side):
    session, protocol_set = ensure_protocol_set_initialized(match)
    state = reconstruct_set_state(protocol_set)

    if protocol_set.is_finished:
        raise ValidationError("Сет уже завершён.")

    create_event(protocol_set, MatchProtocolEvent.EVENT_POINT, side=side)

    state = reconstruct_set_state(protocol_set)
    if protocol_set.set_number == 5 and state["side_switch_triggered"] and not protocol_set.side_switch_triggered:
        protocol_set.side_switch_triggered = True
        protocol_set.side_a_is_left = state["side_a_is_left"]
        protocol_set.save(update_fields=["side_switch_triggered", "side_a_is_left"])

    return protocol_set


@transaction.atomic
def take_timeout(match, side):
    _, protocol_set = ensure_protocol_set_initialized(match)
    state = reconstruct_set_state(protocol_set)

    if protocol_set.is_finished:
        raise ValidationError("Сет уже завершён.")

    if state["timeouts"][side] >= MAX_TIMEOUTS_PER_SET:
        raise ValidationError("У команды уже использованы оба тайм-аута в этом сете.")

    create_event(protocol_set, MatchProtocolEvent.EVENT_TIMEOUT, side=side)
    return protocol_set


@transaction.atomic
def make_substitution(match, side, out_player_id, in_player_id):
    _, protocol_set = ensure_protocol_set_initialized(match)
    state = reconstruct_set_state(protocol_set)

    if protocol_set.is_finished:
        raise ValidationError("Сет уже завершён.")

    if state["substitutions"][side] >= MAX_SUBSTITUTIONS_PER_SET:
        raise ValidationError("У команды уже использованы все 6 замен в этом сете.")

    try:
        out_player_id = int(out_player_id)
        in_player_id = int(in_player_id)
    except (TypeError, ValueError):
        raise ValidationError("Некорректные данные замены.")

    current_on_court_ids = {player.id for player in state["rotation"][side].values()}
    if out_player_id not in current_on_court_ids:
        raise ValidationError("Заменяемый игрок должен находиться на площадке.")

    available_ids = {player.id for player in get_available_substitutes_for_side(state, side)}
    if in_player_id not in available_ids:
        raise ValidationError("Выбранный игрок недоступен для замены.")

    create_event(
        protocol_set,
        MatchProtocolEvent.EVENT_SUBSTITUTION,
        side=side,
        payload={
            "out_player_id": out_player_id,
            "in_player_id": in_player_id,
        },
    )
    return protocol_set


@transaction.atomic
def undo_last_event(match):
    _, protocol_set = ensure_protocol_set_initialized(match)

    if protocol_set.is_finished:
        raise ValidationError("Нельзя отменить действие после подтверждения сета.")

    last_event = protocol_set.events.order_by("-sequence_number", "-id").first()
    if not last_event:
        raise ValidationError("В текущем сете ещё нет действий для отмены.")

    last_event.delete()
    return protocol_set


def get_match_result_snapshot(session):
    sets_a, sets_b = get_team_sets_won_from_finished_sets(session)

    set_scores = []
    for protocol_set in session.sets.filter(is_finished=True).order_by("set_number"):
        state = reconstruct_set_state(protocol_set)
        set_scores.append({
            "a": state["score"]["A"],
            "b": state["score"]["B"],
        })

    return {
        "sets_a": sets_a,
        "sets_b": sets_b,
        "set_scores": set_scores,
    }


@transaction.atomic
def confirm_set_result(match):
    session, protocol_set = ensure_protocol_set_initialized(match)
    state = reconstruct_set_state(protocol_set)

    if protocol_set.is_finished:
        raise ValidationError("Сет уже подтверждён.")

    if not is_valid_set_finish(protocol_set.set_number, state["score"]["A"], state["score"]["B"]):
        raise ValidationError("Сет нельзя завершить: счёт невалиден для окончания партии.")

    create_event(protocol_set, MatchProtocolEvent.EVENT_SET_FINISH)

    protocol_set.is_finished = True
    protocol_set.confirmed_at = timezone.now()
    protocol_set.side_a_is_left = state["side_a_is_left"]
    protocol_set.side_switch_triggered = state["side_switch_triggered"]
    protocol_set.save(update_fields=["is_finished", "confirmed_at", "side_a_is_left", "side_switch_triggered"])

    snapshot = get_match_result_snapshot(session)
    sets_a = snapshot["sets_a"]
    sets_b = snapshot["sets_b"]

    match.sets_a = sets_a
    match.sets_b = sets_b
    match.set_scores = snapshot["set_scores"]

    winner_sets_needed = get_sets_to_win(session)
    match_finished = sets_a >= winner_sets_needed or sets_b >= winner_sets_needed

    if match_finished:
        match.is_finished = True
        match.protocol_code_active = False
    else:
        match.is_finished = False

    match.save(update_fields=["sets_a", "sets_b", "set_scores", "is_finished", "protocol_code_active"])

    if match_finished:
        check_and_generate_playoff(match.tournament)

    return {
        "match_finished": match_finished,
        "next_set_number": protocol_set.set_number + 1,
    }


def build_scoreboard_context(match):
    session, protocol_set = ensure_protocol_set_initialized(match)
    state = reconstruct_set_state(protocol_set)

    sets_a, sets_b = get_team_sets_won_from_finished_sets(session)
    server_side = state["server_side"]
    server_number = state["rotation"][server_side][1].match_number

    def build_team_block(side):
        rotation = state["rotation"][side]
        court = []
        for pos in range(1, 7):
            player = rotation[pos]
            court.append({
                "position": pos,
                "entry_id": player.id,
                "number": player.match_number,
                "name": player.roster_player.player.full_name,
                "is_server": (side == server_side and pos == 1),
            })

        return {
            "side": side,
            "team": get_team_by_side(match, side),
            "score": state["score"][side],
            "sets": sets_a if side == "A" else sets_b,
            "libero_numbers": get_libero_numbers_for_side(match, side),
            "captain_number": get_captain_number_for_side(match, side),
            "rotation": court,
            "timeouts_used": state["timeouts"][side],
            "substitutions_used": state["substitutions"][side],
            "available_substitutes": [
                {
                    "entry_id": p.id,
                    "number": p.match_number,
                    "name": p.roster_player.player.full_name,
                }
                for p in get_available_substitutes_for_side(state, side)
            ],
        }

    return {
        "session": session,
        "protocol_set": protocol_set,
        "team_a_block": build_team_block("A"),
        "team_b_block": build_team_block("B"),
        "server_side": server_side,
        "server_number": server_number,
        "side_a_is_left": state["side_a_is_left"],
        "point_history": state["point_history"],
        "timeout_history": state["timeout_history"],
        "substitution_history": state["substitution_history"],
        "is_set_finish_available": is_valid_set_finish(
            protocol_set.set_number,
            state["score"]["A"],
            state["score"]["B"],
        ),
    }

def get_set_winner_side(protocol_set):
    state = reconstruct_set_state(protocol_set)
    if state["score"]["A"] > state["score"]["B"]:
        return "A"
    return "B"


def build_single_set_summary(protocol_set):
    state = reconstruct_set_state(protocol_set)
    winner_side = "A" if state["score"]["A"] > state["score"]["B"] else "B"

    return {
        "set_number": protocol_set.set_number,
        "score_a": state["score"]["A"],
        "score_b": state["score"]["B"],
        "winner_side": winner_side,
        "side_a_is_left": state["side_a_is_left"],
        "first_server_side": protocol_set.first_server_side,
        "point_history": state["point_history"],
        "timeout_history": state["timeout_history"],
        "substitution_history": state["substitution_history"],
    }


def build_match_summary_context(match):
    session = get_or_create_session(match)

    finished_sets = list(
        session.sets.filter(is_finished=True).order_by("set_number")
    )

    sets = [build_single_set_summary(protocol_set) for protocol_set in finished_sets]

    sets_a, sets_b = get_team_sets_won_from_finished_sets(session)

    return {
        "session": session,
        "sets": sets,
        "sets_a": sets_a,
        "sets_b": sets_b,
        "team_a": match.team_a,
        "team_b": match.team_b,
    }