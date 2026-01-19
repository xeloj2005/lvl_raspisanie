from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q, Count
from .models import Team, Venue, TournamentGroup, Tournament, Match
from .views import check_and_generate_playoff


def is_staff(user):
    """Проверка что пользователь - администратор"""
    return user.is_staff


@login_required
@user_passes_test(is_staff)
def admin_dashboard(request):
    """Главная страница админки"""
    context = {
        'teams_count': Team.objects.count(),
        'venues_count': Venue.objects.count(),
        'groups_count': TournamentGroup.objects.count(),
        'tournaments_count': Tournament.objects.count(),
        'matches_count': Match.objects.count(),
    }
    return render(request, 'tournament/admin/dashboard.html', context)


# ============= КОМАНДЫ =============

@login_required
@user_passes_test(is_staff)
def admin_teams_list(request):
    """Список команд"""
    search = request.GET.get('search', '')
    gender_filter = request.GET.get('gender', '')

    teams = Team.objects.all()

    if search:
        teams = teams.filter(name__icontains=search)

    if gender_filter:
        teams = teams.filter(gender=gender_filter)

    teams = teams.order_by('name')

    context = {
        'teams': teams,
        'search': search,
        'gender_filter': gender_filter,
    }
    return render(request, 'tournament/admin/teams_list.html', context)


@login_required
@user_passes_test(is_staff)
def admin_team_create(request):
    """Создание команды"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        gender = request.POST.get('gender', '')

        if not name:
            messages.error(request, 'Название команды обязательно')
        elif not gender:
            messages.error(request, 'Пол команды обязателен')
        else:
            Team.objects.create(name=name, gender=gender)
            messages.success(request, f'Команда "{name}" успешно создана')
            return redirect('tournament:admin_teams_list')

    return render(request, 'tournament/admin/team_form.html', {'team': None})


@login_required
@user_passes_test(is_staff)
def admin_team_edit(request, team_id):
    """Редактирование команды"""
    team = get_object_or_404(Team, id=team_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        gender = request.POST.get('gender', '')

        if not name:
            messages.error(request, 'Название команды обязательно')
        elif not gender:
            messages.error(request, 'Пол команды обязателен')
        else:
            team.name = name
            team.gender = gender
            team.save()
            messages.success(request, f'Команда "{name}" успешно обновлена')
            return redirect('tournament:admin_teams_list')

    return render(request, 'tournament/admin/team_form.html', {'team': team})


@login_required
@user_passes_test(is_staff)
def admin_team_delete(request, team_id):
    """Удаление команды"""
    team = get_object_or_404(Team, id=team_id)

    if request.method == 'POST':
        team_name = team.name
        team.delete()
        messages.success(request, f'Команда "{team_name}" успешно удалена')
        return redirect('tournament:admin_teams_list')

    # Проверяем связи
    tournaments_count = team.tournaments.count()
    matches_count = Match.objects.filter(Q(team_a=team) | Q(team_b=team)).count()

    context = {
        'team': team,
        'tournaments_count': tournaments_count,
        'matches_count': matches_count,
    }
    return render(request, 'tournament/admin/team_confirm_delete.html', context)


# ============= МЕСТА ПРОВЕДЕНИЯ =============

@login_required
@user_passes_test(is_staff)
def admin_venues_list(request):
    """Список мест проведения"""
    search = request.GET.get('search', '')

    venues = Venue.objects.all()

    if search:
        venues = venues.filter(Q(name__icontains=search) | Q(address__icontains=search))

    venues = venues.order_by('name')

    context = {
        'venues': venues,
        'search': search,
    }
    return render(request, 'tournament/admin/venues_list.html', context)


@login_required
@user_passes_test(is_staff)
def admin_venue_create(request):
    """Создание места проведения"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()

        if not name:
            messages.error(request, 'Название места обязательно')
        else:
            Venue.objects.create(name=name, address=address)
            messages.success(request, f'Место "{name}" успешно создано')
            return redirect('tournament:admin_venues_list')

    return render(request, 'tournament/admin/venue_form.html', {'venue': None})


@login_required
@user_passes_test(is_staff)
def admin_venue_edit(request, venue_id):
    """Редактирование места проведения"""
    venue = get_object_or_404(Venue, id=venue_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()

        if not name:
            messages.error(request, 'Название места обязательно')
        else:
            venue.name = name
            venue.address = address
            venue.save()
            messages.success(request, f'Место "{name}" успешно обновлено')
            return redirect('tournament:admin_venues_list')

    return render(request, 'tournament/admin/venue_form.html', {'venue': venue})


@login_required
@user_passes_test(is_staff)
def admin_venue_delete(request, venue_id):
    """Удаление места проведения"""
    venue = get_object_or_404(Venue, id=venue_id)

    if request.method == 'POST':
        venue_name = venue.name
        venue.delete()
        messages.success(request, f'Место "{venue_name}" успешно удалено')
        return redirect('tournament:admin_venues_list')

    # Проверяем связи
    matches_count = venue.match_set.count()

    context = {
        'venue': venue,
        'matches_count': matches_count,
    }
    return render(request, 'tournament/admin/venue_confirm_delete.html', context)


# ============= ГРУППЫ ТУРНИРОВ =============

@login_required
@user_passes_test(is_staff)
def admin_groups_list(request):
    """Список групп турниров"""
    search = request.GET.get('search', '')

    groups = TournamentGroup.objects.annotate(tournaments_count=Count('tournaments'))

    if search:
        groups = groups.filter(name__icontains=search)

    groups = groups.order_by('order', 'name')

    context = {
        'groups': groups,
        'search': search,
    }
    return render(request, 'tournament/admin/groups_list.html', context)


@login_required
@user_passes_test(is_staff)
def admin_group_create(request):
    """Создание группы турниров"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        order = request.POST.get('order', 0)

        if not name:
            messages.error(request, 'Название группы обязательно')
        else:
            try:
                order = int(order)
            except (ValueError, TypeError):
                order = 0

            TournamentGroup.objects.create(name=name, order=order)
            messages.success(request, f'Группа "{name}" успешно создана')
            return redirect('tournament:admin_groups_list')

    return render(request, 'tournament/admin/group_form.html', {'group': None})


@login_required
@user_passes_test(is_staff)
def admin_group_edit(request, group_id):
    """Редактирование группы турниров"""
    group = get_object_or_404(TournamentGroup, id=group_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        order = request.POST.get('order', 0)

        if not name:
            messages.error(request, 'Название группы обязательно')
        else:
            try:
                order = int(order)
            except (ValueError, TypeError):
                order = 0

            group.name = name
            group.order = order
            group.save()
            messages.success(request, f'Группа "{name}" успешно обновлена')
            return redirect('tournament:admin_groups_list')

    return render(request, 'tournament/admin/group_form.html', {'group': group})


@login_required
@user_passes_test(is_staff)
def admin_group_delete(request, group_id):
    """Удаление группы турниров"""
    group = get_object_or_404(TournamentGroup, id=group_id)

    if request.method == 'POST':
        group_name = group.name
        group.delete()
        messages.success(request, f'Группа "{group_name}" успешно удалена')
        return redirect('tournament:admin_groups_list')

    # Проверяем связи
    tournaments_count = group.tournaments.count()

    context = {
        'group': group,
        'tournaments_count': tournaments_count,
    }
    return render(request, 'tournament/admin/group_confirm_delete.html', context)


# ============= АВТОРИЗАЦИЯ =============

def admin_login(request):
    """Страница входа в админ-панель"""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('tournament:admin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_staff:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.first_name or user.username}!')
                return redirect('tournament:admin_dashboard')
            else:
                messages.error(request, 'У вас нет доступа к админ-панели')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    
    return render(request, 'tournament/admin/login.html')


@login_required
def admin_logout(request):
    """Выход из админ-панели"""
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('tournament:admin_login')


# ============= ТУРНИРЫ =============

@login_required
@user_passes_test(is_staff)
def admin_tournaments_list(request):
    """Список турниров"""
    search = request.GET.get('search', '')
    group_filter = request.GET.get('group', '')
    gender_filter = request.GET.get('gender', '')

    tournaments = Tournament.objects.prefetch_related('group', 'teams')

    if search:
        tournaments = tournaments.filter(name__icontains=search)

    if group_filter:
        tournaments = tournaments.filter(group_id=group_filter)

    if gender_filter:
        tournaments = tournaments.filter(gender=gender_filter)

    tournaments = tournaments.order_by('order', 'name')
    groups = TournamentGroup.objects.all()

    context = {
        'tournaments': tournaments,
        'groups': groups,
        'search': search,
        'group_filter': group_filter,
        'gender_filter': gender_filter,
    }
    return render(request, 'tournament/admin/tournaments_list.html', context)


@login_required
@user_passes_test(is_staff)
def admin_tournament_create(request):
    """Создание турнира"""
    groups = TournamentGroup.objects.all()
    teams = Team.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        group_id = request.POST.get('group')
        gender = request.POST.get('gender', '')
        tournament_type = request.POST.get('tournament_type', 'LEAGUE')
        number_of_rounds = request.POST.get('number_of_rounds', '1')
        has_playoff = request.POST.get('has_playoff') == 'on'
        playoff_teams = request.POST.get('playoff_teams')
        team_ids = request.POST.getlist('teams')
        order = request.POST.get('order', '0')

        errors = []
        if not name:
            errors.append('Название турнира обязательно')
        if not group_id:
            errors.append('Группа обязательна')
        if not gender:
            errors.append('Пол турнира обязателен')

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                group = TournamentGroup.objects.get(id=group_id)
                tournament = Tournament.objects.create(
                    name=name,
                    group=group,
                    gender=gender,
                    tournament_type=tournament_type,
                    number_of_rounds=int(number_of_rounds),
                    has_playoff=has_playoff,
                    playoff_teams=int(playoff_teams) if playoff_teams else None,
                    order=int(order)
                )
                if team_ids:
                    tournament.teams.set(team_ids)
                messages.success(request, f'Турнир "{name}" успешно создан')
                return redirect('tournament:admin_tournaments_list')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')

    context = {
        'tournament': None,
        'groups': groups,
        'teams': teams,
    }
    return render(request, 'tournament/admin/tournament_form.html', context)


@login_required
@user_passes_test(is_staff)
def admin_tournament_edit(request, tournament_id):
    """Редактирование турнира"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    groups = TournamentGroup.objects.all()
    teams = Team.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        group_id = request.POST.get('group')
        gender = request.POST.get('gender', '')
        tournament_type = request.POST.get('tournament_type', 'LEAGUE')
        number_of_rounds = request.POST.get('number_of_rounds', '1')
        has_playoff = request.POST.get('has_playoff') == 'on'
        playoff_teams = request.POST.get('playoff_teams')
        team_ids = request.POST.getlist('teams')
        order = request.POST.get('order', '0')

        errors = []
        if not name:
            errors.append('Название турнира обязательно')
        if not group_id:
            errors.append('Группа обязательна')
        if not gender:
            errors.append('Пол турнира обязателен')

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                group = TournamentGroup.objects.get(id=group_id)
                tournament.name = name
                tournament.group = group
                tournament.gender = gender
                tournament.tournament_type = tournament_type
                tournament.number_of_rounds = int(number_of_rounds)
                tournament.has_playoff = has_playoff
                tournament.playoff_teams = int(playoff_teams) if playoff_teams else None
                tournament.order = int(order)
                tournament.save()
                if team_ids:
                    tournament.teams.set(team_ids)
                else:
                    tournament.teams.clear()
                messages.success(request, f'Турнир "{name}" успешно обновлен')
                return redirect('tournament:admin_tournaments_list')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')

    context = {
        'tournament': tournament,
        'groups': groups,
        'teams': teams,
        'selected_teams': tournament.teams.all(),
    }
    return render(request, 'tournament/admin/tournament_form.html', context)


@login_required
@user_passes_test(is_staff)
def admin_tournament_delete(request, tournament_id):
    """Удаление турнира"""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    if request.method == 'POST':
        # Проверяем связи
        matches_count = tournament.matches.count()

        if matches_count > 0:
            messages.error(request, f'Невозможно удалить турнир: существует {matches_count} матч(ей)')
        else:
            name = tournament.name
            tournament.delete()
            messages.success(request, f'Турнир "{name}" успешно удален')
            return redirect('tournament:admin_tournaments_list')

    context = {
        'tournament': tournament,
        'matches_count': tournament.matches.count(),
    }
    return render(request, 'tournament/admin/tournament_confirm_delete.html', context)


# ============= МАТЧИ =============

@login_required
@user_passes_test(is_staff)
def admin_matches_list(request):
    """Список матчей"""
    search = request.GET.get('search', '')
    tournament_filter = request.GET.get('tournament', '')
    stage_filter = request.GET.get('stage', '')
    finished_filter = request.GET.get('finished', '')

    matches = Match.objects.prefetch_related('tournament', 'team_a', 'team_b', 'venue')

    if search:
        matches = matches.filter(
            Q(team_a__name__icontains=search) |
            Q(team_b__name__icontains=search) |
            Q(venue__name__icontains=search)
        )

    if tournament_filter:
        matches = matches.filter(tournament_id=tournament_filter)

    if stage_filter:
        matches = matches.filter(stage=stage_filter)

    if finished_filter:
        if finished_filter == 'finished':
            matches = matches.filter(is_finished=True)
        elif finished_filter == 'not_finished':
            matches = matches.filter(is_finished=False)

    matches = matches.order_by('-date_time', '-round_number')
    tournaments = Tournament.objects.all()
    stages = Match._meta.get_field('stage').choices

    context = {
        'matches': matches,
        'tournaments': tournaments,
        'stages': stages,
        'search': search,
        'tournament_filter': tournament_filter,
        'stage_filter': stage_filter,
        'finished_filter': finished_filter,
    }
    return render(request, 'tournament/admin/matches_list.html', context)


@login_required
@user_passes_test(is_staff)
def admin_match_create(request):
    """Создание матча"""
    tournaments = Tournament.objects.prefetch_related('teams')
    venues = Venue.objects.all()
    stages = Match._meta.get_field('stage').choices

    if request.method == 'POST':
        tournament_id = request.POST.get('tournament')
        team_a_id = request.POST.get('team_a')
        team_b_id = request.POST.get('team_b')
        venue_id = request.POST.get('venue')
        date_str = request.POST.get('date_time')
        stage = request.POST.get('stage', '')
        round_number = request.POST.get('round_number')
        is_finished = request.POST.get('is_finished') == 'on'
        sets_a = request.POST.get('sets_a')
        sets_b = request.POST.get('sets_b')

        errors = []
        if not tournament_id:
            errors.append('Турнир обязателен')
        if not team_a_id:
            errors.append('Команда А обязательна')
        if not team_b_id:
            errors.append('Команда Б обязательна')
        if not stage:
            errors.append('Этап обязателен')

        if errors:
            for error in errors:
                messages.error(request, error)
        elif team_a_id == team_b_id:
            messages.error(request, 'Команды должны быть разными')
        else:
            try:
                tournament = Tournament.objects.get(id=tournament_id)
                team_a = Team.objects.get(id=team_a_id)
                team_b = Team.objects.get(id=team_b_id)
                venue = Venue.objects.get(id=venue_id) if venue_id else None

                # Обрабатываем set_scores
                set_scores = []
                if is_finished:
                    for i in range(1, 6):
                        score_a_key = f'set-a-{i}'
                        score_b_key = f'set-b-{i}'
                        
                        # Пытаемся получить значения с префиксом "set-"
                        score_a_str = request.POST.get(f'set-a-{i}')
                        score_b_str = request.POST.get(f'set-b-{i}')
                        
                        # Если не найдены, пытаемся старые названия
                        if not score_a_str:
                            score_a_str = request.POST.get(f'set_a_{i}')
                        if not score_b_str:
                            score_b_str = request.POST.get(f'set_b_{i}')
                        
                        if score_a_str or score_b_str:
                            try:
                                score_a = int(score_a_str or 0)
                                score_b = int(score_b_str or 0)
                                if score_a > 0 or score_b > 0:
                                    set_scores.append({
                                        'a': score_a,
                                        'b': score_b
                                    })
                            except (ValueError, TypeError):
                                pass

                match = Match.objects.create(
                    tournament=tournament,
                    team_a=team_a,
                    team_b=team_b,
                    venue=venue,
                    stage=stage,
                    round_number=int(round_number) if round_number and stage == 'REGULAR' else None,
                    is_finished=is_finished,
                    sets_a=int(sets_a) if sets_a else None,
                    sets_b=int(sets_b) if sets_b else None,
                    set_scores=set_scores if set_scores else None,
                )

                if date_str:
                    from datetime import datetime
                    try:
                        match.date_time = datetime.fromisoformat(date_str)
                        match.save()
                    except ValueError:
                        pass

                # Проверяем, нужно ли генерировать плэйофф
                if is_finished:
                    check_and_generate_playoff(match.tournament)

                messages.success(request, 'Матч успешно создан')
                return redirect('tournament:admin_matches_list')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')

    context = {
        'match': None,
        'tournaments': tournaments,
        'venues': venues,
        'stages': stages,
    }
    return render(request, 'tournament/admin/match_form.html', context)


@login_required
@user_passes_test(is_staff)
def admin_match_edit(request, match_id):
    """Редактирование матча"""
    match = get_object_or_404(Match, id=match_id)
    tournaments = Tournament.objects.prefetch_related('teams')
    venues = Venue.objects.all()
    stages = Match._meta.get_field('stage').choices

    if request.method == 'POST':
        tournament_id = request.POST.get('tournament')
        team_a_id = request.POST.get('team_a')
        team_b_id = request.POST.get('team_b')
        venue_id = request.POST.get('venue')
        date_str = request.POST.get('date_time')
        stage = request.POST.get('stage', '')
        round_number = request.POST.get('round_number')
        is_finished = request.POST.get('is_finished') == 'on'
        sets_a = request.POST.get('sets_a')
        sets_b = request.POST.get('sets_b')

        errors = []
        if not tournament_id:
            errors.append('Турнир обязателен')
        if not team_a_id:
            errors.append('Команда А обязательна')
        if not team_b_id:
            errors.append('Команда Б обязательна')
        if not stage:
            errors.append('Этап обязателен')

        if errors:
            for error in errors:
                messages.error(request, error)
        elif team_a_id == team_b_id:
            messages.error(request, 'Команды должны быть разными')
        else:
            try:
                tournament = Tournament.objects.get(id=tournament_id)
                team_a = Team.objects.get(id=team_a_id)
                team_b = Team.objects.get(id=team_b_id)
                venue = Venue.objects.get(id=venue_id) if venue_id else None

                # Обрабатываем set_scores
                set_scores = []
                if is_finished:
                    for i in range(1, 6):
                        score_a_str = request.POST.get(f'set-a-{i}')
                        score_b_str = request.POST.get(f'set-b-{i}')
                        
                        if score_a_str or score_b_str:
                            try:
                                score_a = int(score_a_str or 0)
                                score_b = int(score_b_str or 0)
                                if score_a > 0 or score_b > 0:
                                    set_scores.append({
                                        'a': score_a,
                                        'b': score_b
                                    })
                            except (ValueError, TypeError):
                                pass

                match.tournament = tournament
                match.team_a = team_a
                match.team_b = team_b
                match.venue = venue
                match.stage = stage
                match.round_number = int(round_number) if round_number and stage == 'REGULAR' else None
                match.is_finished = is_finished
                match.sets_a = int(sets_a) if sets_a else None
                match.sets_b = int(sets_b) if sets_b else None
                match.set_scores = set_scores if set_scores else None

                if date_str:
                    from datetime import datetime
                    try:
                        match.date_time = datetime.fromisoformat(date_str)
                    except ValueError:
                        pass

                match.save()
                
                # Проверяем, нужно ли генерировать плэйофф
                if is_finished:
                    check_and_generate_playoff(match.tournament)
                
                messages.success(request, 'Матч успешно обновлен')
                return redirect('tournament:admin_matches_list')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')

    context = {
        'match': match,
        'tournaments': tournaments,
        'venues': venues,
        'stages': stages,
    }
    return render(request, 'tournament/admin/match_form.html', context)


@login_required
@user_passes_test(is_staff)
def admin_match_delete(request, match_id):
    """Удаление матча"""
    match = get_object_or_404(Match, id=match_id)

    if request.method == 'POST':
        match_str = f"{match.team_a.name} - {match.team_b.name}"
        match.delete()
        messages.success(request, f'Матч "{match_str}" успешно удален')
        return redirect('tournament:admin_matches_list')

    context = {
        'match': match,
    }
    return render(request, 'tournament/admin/match_confirm_delete.html', context)