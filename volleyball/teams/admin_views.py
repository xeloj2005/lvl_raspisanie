from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Team, TeamMembership

User = get_user_model()


def is_staff(user):
    return user.is_staff


@login_required
@user_passes_test(is_staff)
def admin_teams_list(request):
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
    return render(request, 'teams/admin/teams_list.html', context)


@login_required
@user_passes_test(is_staff)
def admin_team_create(request):
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

    return render(request, 'teams/admin/team_form.html', {
        'team': None,
        'active_nav': 'teams',
        'back_href': reverse('tournament:admin_teams_list'),
        'back_title': 'Назад к списку команд',
    })


@login_required
@user_passes_test(is_staff)
def admin_team_edit(request, team_id):
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

    return render(request, 'teams/admin/team_form.html', {
        'team': team,
        'active_nav': 'teams',
        'back_href': reverse('tournament:admin_teams_list'),
        'back_title': 'Назад к списку команд',
    })


@login_required
@user_passes_test(is_staff)
def admin_team_delete(request, team_id):
    team = get_object_or_404(Team, id=team_id)

    if request.method == 'POST':
        team_name = team.name
        team.delete()
        messages.success(request, f'Команда "{team_name}" успешно удалена')
        return redirect('tournament:admin_teams_list')

    tournaments_count = team.tournaments.count()
    matches_count = team.matches_as_team_a.count() + team.matches_as_team_b.count()

    context = {
        'team': team,
        'tournaments_count': tournaments_count,
        'matches_count': matches_count,
        'active_nav': 'teams',
        'back_href': reverse('tournament:admin_teams_list'),
        'back_title': 'Назад к списку команд',
    }
    return render(request, 'teams/admin/team_confirm_delete.html', context)


@login_required
@user_passes_test(is_staff)
def admin_team_members(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    search = request.GET.get('search', '').strip()

    memberships = team.memberships.select_related('user').order_by('-joined_at')
    if search:
        memberships = memberships.filter(
            Q(user__full_name__icontains=search) | Q(user__email__icontains=search)
        )

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        email = request.POST.get('email', '').strip().lower()
        roles = request.POST.getlist('roles') or ['MEMBER']

        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                user = None
        elif email:
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
            current = set(membership.roles or [])
            current.update(roles)
            membership.roles = list(current)
            membership.is_active = True
            membership.save(update_fields=['roles', 'is_active'])
            messages.info(request, 'Роли обновлены для существующего участника')
        else:
            membership.roles = roles
            membership.save()
            messages.success(request, 'Пользователь добавлен в команду')

        return redirect('tournament:admin_team_members', team_id=team.id)

    users_qs = User.objects.order_by('full_name')[:50]
    return render(request, 'teams/admin/team_members.html', {
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
        membership.save(update_fields=['roles', 'is_active'])
        messages.success(request, 'Данные участника обновлены')
        return redirect('tournament:admin_team_members', team_id=team.id)

    return render(request, 'teams/admin/team_member_form.html', {
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
