from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render

from tournament.models import TournamentRosterPlayer

from .forms import ProfileForm, RegistrationForm
from .models import User


def _build_profile_context(user):
    roster_players = TournamentRosterPlayer.objects.filter(
        models.Q(player__id=user.id) | models.Q(player__full_name__iexact=user.full_name)
    ).select_related('roster__team', 'roster__tournament').order_by('-roster__tournament__created_at')

    participation = []
    seen = set()
    for item in roster_players:
        key = (item.roster.tournament_id, item.roster.team_id)
        if key in seen:
            continue
        seen.add(key)
        participation.append({
            'tournament': item.roster.tournament,
            'team': item.roster.team,
        })

    return {
        'user': user,
        'player': None,
        'tournaments_count': len({item['tournament'] for item in participation}),
        'teams_count': len({item['team'] for item in participation}),
        'participation': participation,
        'is_own_profile': False,
    }


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешно завершена')
            return redirect('accounts:profile')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            if not user.is_active:
                messages.error(request, 'Данный аккаунт заблокирован')
                return render(request, 'accounts/login.html')
            login(request, user)
            messages.success(request, 'Вы вошли в систему')
            return redirect('accounts:profile')
        messages.error(request, 'Неверный email или пароль')
    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('tournament:index')


@login_required
def profile_view(request):
    context = _build_profile_context(request.user)
    context['is_own_profile'] = True
    return render(request, 'accounts/profile.html', context)


@login_required
def user_detail_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    context = _build_profile_context(user)
    context['is_own_profile'] = request.user.id == user.id
    context['is_admin'] = request.user.is_staff or request.user.is_superuser
    if request.method == 'POST' and context['is_admin'] and request.user.id != user.id:
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        action = 'заблокирован' if not user.is_active else 'разблокирован'
        messages.success(request, f'Пользователь {user.full_name or user.email} успешно {action}')
        return redirect('accounts:user_detail', user_id=user.id)
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def users_list_view(request):
    search = request.GET.get('search', '').strip()
    users = User.objects.order_by('full_name', 'email')
    if search:
        users = users.filter(
            models.Q(full_name__icontains=search) |
            models.Q(email__icontains=search)
        )
    return render(request, 'accounts/users_list.html', {'users': users, 'search': search})
