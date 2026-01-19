from django.urls import path
from . import views, admin_views

app_name = 'tournament'

urlpatterns = [
    # Публичные страницы
    path('', views.index, name='index'),
    path('tournament/<int:tournament_id>/', views.tournament_detail, name='tournament_detail'),

    # Авторизация в админ-панели
    path('admin-panel/login/', admin_views.admin_login, name='admin_login'),
    path('admin-panel/logout/', admin_views.admin_logout, name='admin_logout'),

    # Кастомная админка
    path('admin-panel/', admin_views.admin_dashboard, name='admin_dashboard'),

    # Команды
    path('admin-panel/teams/', admin_views.admin_teams_list, name='admin_teams_list'),
    path('admin-panel/teams/create/', admin_views.admin_team_create, name='admin_team_create'),
    path('admin-panel/teams/<int:team_id>/edit/', admin_views.admin_team_edit, name='admin_team_edit'),
    path('admin-panel/teams/<int:team_id>/delete/', admin_views.admin_team_delete, name='admin_team_delete'),

    # Места проведения
    path('admin-panel/venues/', admin_views.admin_venues_list, name='admin_venues_list'),
    path('admin-panel/venues/create/', admin_views.admin_venue_create, name='admin_venue_create'),
    path('admin-panel/venues/<int:venue_id>/edit/', admin_views.admin_venue_edit, name='admin_venue_edit'),
    path('admin-panel/venues/<int:venue_id>/delete/', admin_views.admin_venue_delete, name='admin_venue_delete'),

    # Группы турниров
    path('admin-panel/groups/', admin_views.admin_groups_list, name='admin_groups_list'),
    path('admin-panel/groups/create/', admin_views.admin_group_create, name='admin_group_create'),
    path('admin-panel/groups/<int:group_id>/edit/', admin_views.admin_group_edit, name='admin_group_edit'),
    path('admin-panel/groups/<int:group_id>/delete/', admin_views.admin_group_delete, name='admin_group_delete'),

    # Турниры
    path('admin-panel/tournaments/', admin_views.admin_tournaments_list, name='admin_tournaments_list'),
    path('admin-panel/tournaments/create/', admin_views.admin_tournament_create, name='admin_tournament_create'),
    path('admin-panel/tournaments/<int:tournament_id>/edit/', admin_views.admin_tournament_edit, name='admin_tournament_edit'),
    path('admin-panel/tournaments/<int:tournament_id>/delete/', admin_views.admin_tournament_delete, name='admin_tournament_delete'),

    # Матчи
    path('admin-panel/matches/', admin_views.admin_matches_list, name='admin_matches_list'),
    path('admin-panel/matches/create/', admin_views.admin_match_create, name='admin_match_create'),
    path('admin-panel/matches/<int:match_id>/edit/', admin_views.admin_match_edit, name='admin_match_edit'),
    path('admin-panel/matches/<int:match_id>/delete/', admin_views.admin_match_delete, name='admin_match_delete'),
]