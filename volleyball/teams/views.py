from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .models import Team, TeamMembership, TeamRole, create_team_with_owner


def user_is_team_manager(user, team):
    """Проверка прав на управление командой."""
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    if team.creator_id and user.id == team.creator_id:
        return True

    try:
        membership = team.memberships.filter(
            user=user,
            is_active=True,
        ).first()
    except Exception:
        membership = None

    if membership is None:
        return False

    return TeamRole.CAPTAIN in (membership.roles or []) or TeamRole.ADMIN in (membership.roles or [])


@login_required
def teams_list(request):
    teams = Team.objects.order_by('name')
    return render(request, 'tournament/team_list.html', {'teams': teams})


@login_required
def team_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        gender = request.POST.get('gender', '')

        if not name:
            messages.error(request, 'Название команды обязательно')
        elif not gender:
            messages.error(request, 'Пол команды обязателен')
        else:
            team = create_team_with_owner(name=name, gender=gender, creator=request.user)
            messages.success(request, f'Команда "{team.name}" успешно создана')
            return redirect('tournament:team_detail', team_id=team.id)

    return render(request, 'tournament/team_form.html', {'team': None})


@login_required
def team_detail(request, team_id):
    team = get_object_or_404(Team.objects.prefetch_related('memberships__user'), id=team_id)
    memberships = team.memberships.select_related('user').all()
    is_creator = request.user == team.creator
    can_edit = user_is_team_manager(request.user, team)
    user_in_team = memberships.filter(user=request.user, is_active=True).exists()

    if request.method == 'POST' and 'join' in request.POST:
        if not user_in_team:
            TeamMembership.objects.create(
                team=team,
                user=request.user,
                roles=[TeamRole.PLAYER],
                is_active=True,
            )
            messages.success(request, 'Вы присоединились к команде')
            return redirect('tournament:team_detail', team_id=team.id)

    return render(request, 'tournament/team_detail.html', {
        'team': team,
        'memberships': memberships,
        'can_edit': can_edit,
        'is_creator': is_creator,
        'user_in_team': user_in_team,
    })


@login_required
def team_edit(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    if not user_is_team_manager(request.user, team):
        return HttpResponseForbidden('Нет прав')

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
            messages.success(request, 'Команда обновлена')
            return redirect('tournament:team_detail', team_id=team.id)

    return render(request, 'tournament/team_form.html', {'team': team})


@login_required
def team_members_manage(request, team_id):
    """Управление участниками команды."""
    team = get_object_or_404(Team.objects.prefetch_related('memberships__user'), id=team_id)
    if not user_is_team_manager(request.user, team):
        return HttpResponseForbidden('Нет прав')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            email = request.POST.get('email', '').strip().lower()
            roles = request.POST.getlist('roles') or [TeamRole.PLAYER]

            if not email:
                messages.error(request, 'Укажите email')
                return redirect('tournament:team_members_manage', team_id=team.id)

            User = get_user_model()
            user = None

            if '@' in email:
                try:
                    user = User.objects.get(email__iexact=email)
                except User.DoesNotExist:
                    matches = User.objects.filter(
                        Q(email__icontains=email) | Q(full_name__icontains=email)
                    ).order_by('full_name')[:6]
                    if matches.count() == 1:
                        user = matches.first()
                    elif matches.count() > 1:
                        msgs = ', '.join([f"{u.full_name} <{u.email}>" for u in matches])
                        messages.error(request, f'Найдено несколько пользователей: {msgs}. Уточните email.')
                        return redirect('tournament:team_members_manage', team_id=team.id)
                    else:
                        messages.error(request, 'Пользователь с таким email не найден')
                        return redirect('tournament:team_members_manage', team_id=team.id)
            else:
                matches = User.objects.filter(
                    Q(full_name__icontains=email) | Q(email__icontains=email)
                ).order_by('full_name')[:6]
                if matches.count() == 1:
                    user = matches.first()
                elif matches.count() > 1:
                    msgs = ', '.join([f"{u.full_name} <{u.email}>" for u in matches])
                    messages.error(request, f'Найдено несколько пользователей: {msgs}. Уточните ввод (полное имя или email).')
                    return redirect('tournament:team_members_manage', team_id=team.id)
                else:
                    messages.error(request, 'Пользователь не найден. Укажите точный email или полное имя.')
                    return redirect('tournament:team_members_manage', team_id=team.id)

            membership, created = TeamMembership.objects.get_or_create(
                team=team,
                user=user,
                defaults={'roles': roles, 'is_active': True},
            )
            if not created:
                current = set(membership.roles or [])
                current.update(roles)
                membership.roles = list(current)
                membership.is_active = True
                membership.save(update_fields=['roles', 'is_active'])
                messages.info(request, 'Роли обновлены для существующего участника')
            else:
                messages.success(request, 'Пользователь добавлен в команду')
            return redirect('tournament:team_members_manage', team_id=team.id)

        if action == 'remove':
            membership_id = request.POST.get('membership_id')
            try:
                membership = team.memberships.get(id=membership_id)
                membership.delete()
                messages.success(request, 'Участник удалён')
            except Exception:
                messages.error(request, 'Не удалось удалить участника')
            return redirect('tournament:team_members_manage', team_id=team.id)

    memberships = team.memberships.select_related('user').all()
    users_qs = get_user_model().objects.order_by('full_name')[:50]
    return render(request, 'tournament/team_members_manage.html', {
        'team': team,
        'memberships': memberships,
        'users': users_qs,
    })
