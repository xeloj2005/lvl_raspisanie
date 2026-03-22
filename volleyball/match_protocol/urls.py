from django.urls import path
from . import views

app_name = "match_protocol"

urlpatterns = [
    path("match/<int:match_id>/squad/<str:side>/", views.squad_step, name="squad_step"),
    path("match/<int:match_id>/lineup/<str:side>/", views.lineup_step, name="lineup_step"),
    path("match/<int:match_id>/set-setup/<int:set_number>/", views.set_setup_step, name="set_setup_step"),
    path("match/<int:match_id>/scoreboard/", views.scoreboard, name="scoreboard"),

    path("match/<int:match_id>/action/point/<str:side>/", views.action_add_point, name="action_add_point"),
    path("match/<int:match_id>/action/timeout/<str:side>/", views.action_timeout, name="action_timeout"),
    path("match/<int:match_id>/action/substitution/<str:side>/", views.action_substitution, name="action_substitution"),
    path("match/<int:match_id>/action/undo/", views.action_undo, name="action_undo"),
    path("match/<int:match_id>/action/confirm-set/", views.action_confirm_set, name="action_confirm_set"),

    path("match/<int:match_id>/summary/", views.protocol_summary, name="protocol_summary"),
]