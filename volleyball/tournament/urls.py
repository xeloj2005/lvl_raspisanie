from django.urls import path
from . import views
from . import admin_views
from teams.views import team_create, team_detail, team_edit, team_members_manage, teams_list

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
    path('admin-panel/teams/<int:team_id>/members/', admin_views.admin_team_members, name='admin_team_members'),
    path('admin-panel/teams/<int:team_id>/members/<int:member_id>/edit/', admin_views.admin_team_member_edit, name='admin_team_member_edit'),
    path('admin-panel/teams/<int:team_id>/members/<int:member_id>/remove/', admin_views.admin_team_member_remove, name='admin_team_member_remove'),

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
    path('admin-panel/players/', admin_views.players_list, name='admin_players_list'),
    path('admin-panel/players/create/', admin_views.player_create, name='admin_player_create'),
    path('admin-panel/players/<int:pk>/edit/', admin_views.player_edit, name='admin_player_edit'),
    path('admin-panel/players/<int:pk>/delete/', admin_views.player_delete, name='admin_player_delete'),
    path('admin-panel/users/', admin_views.admin_users_list, name='admin_users_list'),
    path('admin-panel/rosters/', admin_views.rosters_list, name='admin_rosters_list'),
    path('admin-panel/rosters/create/', admin_views.roster_create, name='admin_roster_create'),
    path('admin-panel/rosters/<int:pk>/edit/', admin_views.roster_edit, name='admin_roster_edit'),
    path('admin-panel/rosters/<int:pk>/delete/', admin_views.roster_delete, name='admin_roster_delete'),
    path('admin-panel/rosters/<int:pk>/players/add/', admin_views.roster_player_add, name='admin_roster_player_add'),
    path('admin-panel/rosters/<int:roster_pk>/players/<int:player_pk>/remove/', admin_views.roster_player_remove, name='admin_roster_player_remove'),
    #судья
    path('referee/login/', admin_views.referee_login, name='referee_login'),
    path('referee/logout/', admin_views.referee_logout, name='referee_logout'),
    path('admin-panel/referees/', admin_views.referees_list, name='admin_referees_list'),
    path('admin-panel/referees/create/', admin_views.referee_create, name='admin_referee_create'),

    # Команды — логика вынесена в teams app, но legacy-вьюшки сохраняем в tournament namespace
    path('teams/', teams_list, name='teams_list'),
    path('teams/create/', team_create, name='team_create'),
    path('teams/<int:team_id>/', team_detail, name='team_detail'),
    path('teams/<int:team_id>/edit/', team_edit, name='team_edit'),
    path('teams/<int:team_id>/members/', team_members_manage, name='team_members_manage'),

    path('protocol/', views.protocol_code_entry, name='code_entry'),
]