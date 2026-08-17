from django.contrib import admin

from .models import Team

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'gender', 'get_tournaments_count']
    list_filter = ['gender']
    search_fields = ['name']

    def get_tournaments_count(self, obj):
        return obj.tournaments.count()

    get_tournaments_count.short_description = 'Турниров'
