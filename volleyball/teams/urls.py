from django.urls import path

from . import views

app_name = 'teams'

urlpatterns = [
    path('', views.teams_list, name='teams_list'),
    path('create/', views.team_create, name='team_create'),
    path('<int:team_id>/', views.team_detail, name='team_detail'),
    path('<int:team_id>/edit/', views.team_edit, name='team_edit'),
    path('<int:team_id>/members/', views.team_members_manage, name='team_members_manage'),
]
