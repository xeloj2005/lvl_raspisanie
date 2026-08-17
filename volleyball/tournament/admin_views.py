from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.db.models import Q, Count
from .models import  Venue, TournamentGroup, Tournament, Match, TournamentTeamRoster, TournamentRosterPlayer,  Referee, generate_unique_protocol_code
from .views import check_and_generate_playoff
from django.db import IntegrityError
from django.urls import reverse

User = get_user_model()

def is_staff(user):
    """Проверка что пользователь - администратор"""
    return user.is_staff

def parse_set_scores(request, tournament, is_finished):
    if not is_finished:
        return None

    max_sets = tournament.get_max_sets()
    set_scores = []

    for i in range(1, max_sets + 1):
        score_a_str = request.POST.get(f'set-a-{i}') or request.POST.get(f'set_a_{i}')
        score_b_str = request.POST.get(f'set-b-{i}') or request.POST.get(f'set_b_{i}')

        if score_a_str or score_b_str:
            try:
                score_a = int(score_a_str or 0)
                score_b = int(score_b_str or 0)
            except (ValueError, TypeError):
                continue

            if score_a > 0 or score_b > 0:
                set_scores.append({'a': score_a, 'b': score_b})

    return set_scores or None


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
        'rosters_count': TournamentTeamRoster.objects.count(),
        'players_count': TournamentRosterPlayer.objects.count(),
        'referees_count': Referee.objects.count(),
        'users_count': User.objects.count(),
        'active_nav': 'dashboard',
        'back_href': None,
        'back_title': None,
    }
    return render(request, 'tournament/admin/dashboard.html', context)


@login_required
@user_passes_test(is_staff)
def admin_users_list(request):
    users = User.objects.order_by('full_name', 'email')
    return render(request, 'tournament/admin/users_list.html', {
        'users': users,
        'active_nav': 'users',
        'back_href': reverse('tournament:admin_dashboard'),
        'back_title': 'Панель администратора',
    })


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
        'active_nav': 'teams',
        'back_href': reverse('tournament:admin_dashboard'),
        'back_title': 'Панель администратора',

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

    return render(request, 'tournament/admin/team_form.html', {
        'team': None,
        'active_nav': 'teams',
        'back_href': reverse('tournament:admin_teams_list'),
        'back_title': 'Назад к списку команд',
    })

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

    return render(request, 'tournament/admin/team_form.html', {
        'team': team,
        'active_nav': 'teams',
        'back_href': reverse('tournament:admin_teams_list'),
        'back_title': 'Назад к списку команд',
    })

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
        'active_nav': 'teams',
        'back_href': reverse('tournament:admin_teams_list'),
        'back_title': 'Назад к списку команд',
    }
    return render(request, 'tournament/admin/team_confirm_delete.html', context)




# ============= УПРАВЛЕНИЕ СОСТАВАМИ КОМАНД =============

@login_required
@user_passes_test(is_staff)
def admin_team_members(request, team_id):
    """Показать и добавить участников команды"""
    team = get_object_or_404(Team, id=team_id)
    search = request.GET.get('search','').strip()

    memberships = team.memberships.select_related('user').order_by('-joined_at')
    if search:
        memberships = memberships.filter(
            Q(user__full_name__icontains=search) | Q(user__email__icontains=search)
        )

    if request.method == 'POST':
        # Adding a member
        user_id = request.POST.get('user_id')
        email = request.POST.get('email','').strip().lower()
        roles = request.POST.getlist('roles') or ['MEMBER']

        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                user = None
        elif email:
            # fuzzy search like public manager: exact email first, then fallback to contains in email/full_name
            if '@' in email:
                try:
                    user = User.objects.get(email__iexact=email)
                except User.DoesNotExist:
                    matches = User.objects.filter(Q(email__icontains=email) | Q(full_name__icontains=email)).order_by('full_name')[:6]
                    if matches.count() == 1:
                        user = matches.first()
                    elif matches.count() > 1:
                        msgs = ', '.join([f"{u.full_name} <{u.email}>" for u in matches])
                        messages.error(request, f'Найдено несколько пользователей: {msgs}. Уточните email.')
                        return redirect('tournament:admin_team_members', team_id=team.id)
                    else:
                        messages.error(request, 'Пользователь с таким email не найден')
                        return redirect('tournament:admin_team_members', team_id=team.id)
            else:
                matches = User.objects.filter(Q(full_name__icontains=email) | Q(email__icontains=email)).order_by('full_name')[:6]
                if matches.count() == 1:
                    user = matches.first()
                elif matches.count() > 1:
                    msgs = ', '.join([f"{u.full_name} <{u.email}>" for u in matches])
                    messages.error(request, f'Найдено несколько пользователей: {msgs}. Уточните ввод (полное имя или email).')
                    return redirect('tournament:admin_team_members', team_id=team.id)
                else:
                    messages.error(request, 'Пользователь не найден. Укажите точный email или полное имя.')
                    return redirect('tournament:admin_team_members', team_id=team.id)

        if not user:
            messages.error(request, 'Пользователь не найден. Укажите существующий email или выберите пользователя.')
            return redirect('tournament:admin_team_members', team_id=team.id)

        membership, created = team.memberships.get_or_create(user=user, defaults={'roles': roles})
        if not created:
            # merge roles
            current = set(membership.roles or [])
            current.update(roles)
            membership.roles = list(current)
            membership.is_active = True
            membership.save(update_fields=['roles','is_active'])
            messages.info(request, 'Роли обновлены для существующего участника')
        else:
            membership.roles = roles
            membership.save()
            messages.success(request, 'Пользователь добавлен в команду')

        return redirect('tournament:admin_team_members', team_id=team.id)

    users_qs = User.objects.order_by('full_name')[:50]

    return render(request, 'tournament/admin/team_members.html', {
        'team': team,
        'memberships': memberships,
        'users': users_qs,
        'search': search,
        'active_nav': 'teams',
        'back_href': reverse('tournament:admin_teams_list'),
        'back_title': 'Назад к списку команд',
    })


@login_required
@user_passes_test(is_staff)
def admin_team_member_edit(request, team_id, membership_id):
    team = get_object_or_404(Team, id=team_id)
    membership = get_object_or_404(team.memberships.model, id=membership_id, team=team)

    if request.method == 'POST':
        roles = request.POST.getlist('roles') or []
        is_active = request.POST.get('is_active') == 'on'
        membership.roles = roles
        membership.is_active = is_active
        membership.save(update_fields=['roles','is_active'])
        messages.success(request, 'Данные участника обновлены')
        return redirect('tournament:admin_team_members', team_id=team.id)

    return render(request, 'tournament/admin/team_member_form.html', {
        'team': team,
        'membership': membership,
        'active_nav': 'teams',
        'back_href': reverse('tournament:admin_team_members', args=[team.id]),
        'back_title': 'Назад к составу команды',
    })


@login_required
@user_passes_test(is_staff)
def admin_team_member_remove(request, team_id, membership_id):
    team = get_object_or_404(Team, id=team_id)
    membership = get_object_or_404(team.memberships.model, id=membership_id, team=team)
    if request.method == 'POST':
        membership.delete()
        messages.success(request, 'Участник удалён из команды')
    return redirect('tournament:admin_team_members', team_id=team.id)
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
        'active_nav': 'venues',
        'back_href': reverse('tournament:admin_dashboard'),
        'back_title': 'Панель администратора',
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

    return render(request, 'tournament/admin/venue_form.html', {
        'venue': None,
        'active_nav': 'venues',
        'back_href': reverse('tournament:admin_venues_list'),
        'back_title': 'Назад к списку мест',
    })


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

    return render(request, 'tournament/admin/venue_form.html', {
        'venue': venue,
        'active_nav': 'venues',
        'back_href': reverse('tournament:admin_venues_list'),
        'back_title': 'Назад к списку мест',
    })


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
        'active_nav': 'venues',
        'back_href': reverse('tournament:admin_venues_list'),
        'back_title': 'Назад к списку мест',
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
        'active_nav': 'groups',
        'back_href': reverse('tournament:admin_dashboard'),
        'back_title': 'Панель администратора',
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

    return render(request, 'tournament/admin/group_form.html', {
        'group': None,
        'active_nav': 'groups',
        'back_href': reverse('tournament:admin_groups_list'),
        'back_title': 'Назад к списку групп',
    })


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

    return render(request, 'tournament/admin/group_form.html', {
        'group': group,
        'active_nav': 'groups',
        'back_href': reverse('tournament:admin_groups_list'),
        'back_title': 'Назад к списку групп',
    })


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
        'active_nav': 'groups',
        'back_href': reverse('tournament:admin_groups_list'),
        'back_title': 'Назад к списку групп',
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
        'active_nav': 'tournaments',
        'back_href': reverse('tournament:admin_dashboard'),
        'back_title': 'Панель администратора',
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
        if tournament_type == 'SHORT':
            has_playoff = False
            playoff_teams = None
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
        'active_nav': 'tournaments',
        'back_href': reverse('tournament:admin_tournaments_list'),
        'back_title': 'Назад к списку турниров',
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
        if tournament_type == 'SHORT':
            has_playoff = False
            playoff_teams = None
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
        'active_nav': 'tournaments',
        'back_href': reverse('tournament:admin_tournaments_list'),
        'back_title': 'Назад к списку турниров',
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
        'active_nav': 'tournaments',
        'back_href': reverse('tournament:admin_tournaments_list'),
        'back_title': 'Назад к списку турниров',
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
        'active_nav': 'matches',
        'back_href': reverse('tournament:admin_dashboard'),
        'back_title': 'Панель администратора',
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
                set_scores = parse_set_scores(request, tournament, is_finished)

                match = Match(
                    tournament=tournament,
                    team_a=team_a,
                    team_b=team_b,
                    venue=venue,
                    stage=stage,
                    round_number=int(round_number) if round_number and stage == 'REGULAR' else None,
                    is_finished=is_finished,
                    sets_a=int(sets_a) if sets_a else None,
                    sets_b=int(sets_b) if sets_b else None,
                    set_scores=set_scores,
                    protocol_code=generate_unique_protocol_code(),
                    protocol_code_active=True,
                )

                if date_str:
                    from datetime import datetime
                    try:
                        match.date_time = datetime.fromisoformat(date_str)
                    except ValueError:
                        pass

                match.full_clean()
                match.save()

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
        'active_nav': 'matches',
        'back_href': reverse('tournament:admin_matches_list'),
        'back_title': 'Назад к списку матчей',
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

                set_scores = parse_set_scores(request, tournament, is_finished)

                match.tournament = tournament
                match.team_a = team_a
                match.team_b = team_b
                match.venue = venue
                match.stage = stage
                match.round_number = int(round_number) if round_number and stage == 'REGULAR' else None
                match.is_finished = is_finished
                match.sets_a = int(sets_a) if sets_a else None
                match.sets_b = int(sets_b) if sets_b else None
                match.set_scores = set_scores

                if date_str:
                    from datetime import datetime
                    try:
                        match.date_time = datetime.fromisoformat(date_str)
                    except ValueError:
                        pass

                match.full_clean()
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
        'active_nav': 'matches',
        'back_href': reverse('tournament:admin_matches_list'),
        'back_title': 'Назад к списку матчей',
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
        'active_nav': 'matches',
        'back_href': reverse('tournament:admin_matches_list'),
        'back_title': 'Назад к списку матчей',
    }
    return render(request, 'tournament/admin/match_confirm_delete.html', context)

@login_required
@user_passes_test(is_staff)
def players_list(request):
    # Players are now represented by User accounts. Redirect to users management.
    return redirect('tournament:admin_users_list')


@login_required
@user_passes_test(is_staff)
def player_create(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        birth_date = request.POST.get('birth_date') or None
        rank = request.POST.get('rank', '').strip()

        if not full_name:
            messages.error(request, 'Введите ФИО игрока')
        else:
            Player.objects.create(
                full_name=full_name,
                birth_date=birth_date,
                rank=rank,
            )
            messages.success(request, 'Игрок успешно добавлен')
            return redirect('tournament:admin_players_list')

    return render(request, 'tournament/admin/player_form.html', {
        'active_nav': 'players',
        'back_href': reverse('tournament:admin_players_list'),
        'back_title': 'Назад к списку игроков',
    })


@login_required
@user_passes_test(is_staff)
def player_edit(request, pk):
    player = get_object_or_404(Player, pk=pk)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        birth_date = request.POST.get('birth_date') or None
        rank = request.POST.get('rank', '').strip()

        if not full_name:
            messages.error(request, 'Введите ФИО игрока')
        else:
            player.full_name = full_name
            player.birth_date = birth_date
            player.rank = rank
            player.save()

            messages.success(request, 'Данные игрока сохранены')
            return redirect('tournament:admin_players_list')

    return render(request, 'tournament/admin/player_form.html', {
        'player': player,
        'active_nav': 'players',
        'back_href': reverse('tournament:admin_players_list'),
        'back_title': 'Назад к списку игроков',
    })


@login_required
@user_passes_test(is_staff)
def player_delete(request, pk):
    player = get_object_or_404(Player, pk=pk)

    if request.method == 'POST':
        player.delete()
        messages.success(request, 'Игрок удалён')
        return redirect('tournament:admin_players_list')

    return render(request, 'tournament/admin/player_confirm_delete.html', {
        'player': player,
        'active_nav': 'players',
        'back_href': reverse('tournament:admin_players_list'),
        'back_title': 'Назад к списку игроков',
    })

@login_required
@user_passes_test(is_staff)
def rosters_list(request, team_id=None):
    """Список составов. Если team_id передан — показываем составы только для команды."""
    rosters = TournamentTeamRoster.objects.select_related('tournament', 'team')
    if team_id:
        rosters = rosters.filter(team_id=team_id)
    rosters = rosters.annotate(players_count=Count('roster_players')).order_by('tournament__name', 'team__name')

    return render(request, 'tournament/admin/rosters_list.html', {
        'rosters': rosters,
        'active_nav': 'rosters',
        'back_href': reverse('tournament:admin_dashboard'),
        'back_title': 'Панель администратора',
        'team_id': team_id,
    })


@login_required
@user_passes_test(is_staff)
def roster_create(request, team_id=None):
    tournaments = Tournament.objects.prefetch_related('teams').order_by('name')

    if request.method == 'POST':
        tournament_id = request.POST.get('tournament')
        team_id_post = request.POST.get('team') or team_id

        if not tournament_id:
            messages.error(request, 'Выберите турнир')
        elif not team_id_post:
            messages.error(request, 'Выберите команду')
        else:
            tournament = get_object_or_404(Tournament, pk=tournament_id)
            team = get_object_or_404(Team, pk=team_id_post)

            if not tournament.teams.filter(pk=team.pk).exists():
                messages.error(request, 'Эта команда не добавлена в выбранный турнир')
            else:
                roster, created = TournamentTeamRoster.objects.get_or_create(
                    tournament=tournament,
                    team=team,
                )

                if created:
                    messages.success(request, 'Состав создан')
                else:
                    messages.info(request, 'Состав уже существует, открыто редактирование')

                return redirect('tournament:admin_roster_edit', pk=roster.pk)

    return render(request, 'tournament/admin/roster_form.html', {
        'tournaments': tournaments,
        'active_nav': 'rosters',
        'back_href': reverse('tournament:admin_rosters_list'),
        'back_title': 'Назад к списку составов',
        'team_id': team_id,
    })


@login_required
@user_passes_test(is_staff)
def roster_edit(request, pk):
    roster = get_object_or_404(
        TournamentTeamRoster.objects.select_related('tournament', 'team'),
        pk=pk
    )

    # if team_id comes from URL, ensure it matches roster.team_id

    roster_players = TournamentRosterPlayer.objects.select_related('player').filter(
        roster=roster
    ).order_by('player__full_name')

    used_player_ids = TournamentRosterPlayer.objects.filter(
        roster__tournament=roster.tournament
    ).exclude(
        roster=roster
    ).values_list('player_id', flat=True)

    current_player_ids = roster_players.values_list('player_id', flat=True)

    available_players = Player.objects.exclude(
        id__in=used_player_ids
    ).exclude(
        id__in=current_player_ids
    ).order_by('full_name')

    return render(request, 'tournament/admin/roster_edit.html', {
        'roster': roster,
        'roster_players': roster_players,
        'available_players': available_players,
        'active_nav': 'rosters',
        'back_href': reverse('tournament:admin_rosters_list'),
        'back_title': 'Назад к списку составов',
    })


@login_required
@user_passes_test(is_staff)
def roster_delete(request, team_id, pk):
    roster = get_object_or_404(
        TournamentTeamRoster.objects.select_related('tournament', 'team'),
        pk=pk
    )

    if request.method == 'POST':
        roster.delete()
        messages.success(request, 'Состав удалён')
        return redirect('tournament:admin_rosters_list')

    return render(request, 'tournament/admin/roster_confirm_delete.html', {
        'roster': roster,
        'active_nav': 'rosters',
        'back_href': reverse('tournament:admin_rosters_list'),
        'back_title': 'Назад к списку составов',
    })


@login_required
@user_passes_test(is_staff)
def roster_player_add(request, team_id, pk):
    roster = get_object_or_404(TournamentTeamRoster, pk=pk)

    if request.method == 'POST':
        player_id = request.POST.get('player')

        if not player_id:
            messages.error(request, 'Выберите игрока')
            return redirect('tournament:admin_roster_edit', pk=roster.pk)

        player = get_object_or_404(Player, pk=player_id)

        conflict = TournamentRosterPlayer.objects.filter(
            roster__tournament=roster.tournament,
            player=player
        ).exclude(roster=roster).exists()

        if conflict:
            messages.error(request, 'Этот игрок уже заявлен за другую команду в данном турнире')
            return redirect('tournament:admin_roster_edit', pk=roster.pk)

        roster_player, created = TournamentRosterPlayer.objects.get_or_create(
            roster=roster,
            player=player,
        )

        if created:
            messages.success(request, 'Игрок добавлен в состав')
        else:
            messages.info(request, 'Игрок уже находится в этом составе')

    return redirect('tournament:admin_roster_edit', pk=roster.pk)


@login_required
@user_passes_test(is_staff)
def roster_player_remove(request, roster_pk, player_pk):
    roster_player = get_object_or_404(
        TournamentRosterPlayer,
        roster_id=roster_pk,
        player_id=player_pk
    )

    if request.method == 'POST':
        roster_player.delete()
        messages.success(request, 'Игрок удалён из состава')

    return redirect('tournament:admin_roster_edit', pk=roster_pk)

# Redirect helpers for backward-compatible old roster URLs -> new team-scoped URLs
@login_required
@user_passes_test(is_staff)
def admin_rosters_redirect(request):
    # If a team parameter is present in GET, prefer it; otherwise redirect to admin teams list
    team_id = request.GET.get('team')
    if team_id:
        return redirect('tournament:admin_rosters_list')
    return redirect('tournament:admin_teams_list')

@login_required
@user_passes_test(is_staff)
def admin_roster_create_redirect(request):
    team_id = request.GET.get('team')
    if team_id:
        return redirect('tournament:admin_roster_create')
    return redirect('tournament:admin_rosters_list')

@login_required
@user_passes_test(is_staff)
def admin_roster_edit_redirect(request, pk):
    # try to find roster and redirect to edit
    try:
        roster = TournamentTeamRoster.objects.get(pk=pk)
        return redirect('tournament:admin_roster_edit', pk=pk)
    except TournamentTeamRoster.DoesNotExist:
        return redirect('tournament:admin_rosters_list')

@login_required
@user_passes_test(is_staff)
def admin_roster_delete_redirect(request, pk):
    try:
        roster = TournamentTeamRoster.objects.get(pk=pk)
        return redirect('tournament:admin_roster_delete', pk=pk)
    except TournamentTeamRoster.DoesNotExist:
        return redirect('tournament:admin_rosters_list')

@login_required
@user_passes_test(is_staff)
def admin_roster_player_add_redirect(request, pk):
    try:
        roster = TournamentTeamRoster.objects.get(pk=pk)
        return redirect('tournament:admin_roster_edit', pk=pk)
    except TournamentTeamRoster.DoesNotExist:
        return redirect('tournament:admin_rosters_list')

@login_required
@user_passes_test(is_staff)
def admin_roster_player_remove_redirect(request, roster_pk, player_pk):
    try:
        roster = TournamentTeamRoster.objects.get(pk=roster_pk)
        return redirect('tournament:admin_roster_edit', pk=roster_pk)
    except TournamentTeamRoster.DoesNotExist:
        return redirect('tournament:admin_rosters_list')


@login_required
@user_passes_test(is_staff)
def referees_list(request):
    referees = Referee.objects.select_related('user').order_by('full_name')
    return render(request, 'tournament/admin/referees_list.html', {
        'referees': referees,
        'active_nav': 'referees',
        'back_href': reverse('tournament:admin_dashboard'),
        'back_title': 'Панель администратора',
    })


@login_required
@user_passes_test(is_staff)
def referee_create(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        full_name = request.POST.get('full_name', '').strip()
        password = request.POST.get('password', '').strip()

        if not email:
            messages.error(request, 'Введите email')
        elif not full_name:
            messages.error(request, 'Введите ФИО')
        elif not password:
            messages.error(request, 'Введите пароль')
        elif User.objects.filter(username=email).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
        else:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password
            )
            Referee.objects.create(
                user=user,
                full_name=full_name
            )
            messages.success(request, 'Судья успешно создан')
            return redirect('tournament:admin_referees_list')

    return render(request, 'tournament/admin/referee_form.html', {
        'active_nav': 'referees',
        'back_href': reverse('tournament:admin_referees_list'),
        'back_title': 'Назад к списку судей',
    })

def referee_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'referee_profile'):
            messages.info(request, 'Раздел судьи будет подключён следующим этапом')
            return redirect('tournament:admin_login')
        return redirect('tournament:admin_dashboard')

    if request.method == 'POST':
        email = request.POST.get('username', '').strip().lower()
        password = request.POST.get('password', '')

        user = authenticate(request, username=email, password=password)

        if user is None:
            messages.error(request, 'Неверный логин или пароль')
        elif not hasattr(user, 'referee_profile'):
            messages.error(request, 'У пользователя нет прав судьи')
        elif not user.referee_profile.is_active:
            messages.error(request, 'Профиль судьи отключён')
        else:
            login(request, user)
            return redirect('tournament:index')

    return render(request, 'tournament/admin/login.html', {
        'login_title': 'Вход для судьи',
        'submit_text': 'Войти как судья',
        'is_referee_login': True,
    })

@login_required
def referee_logout(request):
    logout(request)
    return redirect('tournament:index')
