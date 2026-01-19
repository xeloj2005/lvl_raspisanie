from django.contrib import admin
from .models import TournamentGroup, Venue, Team, Tournament, Match, StandingsCache


@admin.register(TournamentGroup)
class TournamentGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'created_at']
    list_editable = ['order']
    search_fields = ['name']


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'address']
    search_fields = ['name', 'address']


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'gender', 'get_tournaments_count']
    list_filter = ['gender']
    search_fields = ['name']

    def get_tournaments_count(self, obj):
        return obj.tournaments.count()

    get_tournaments_count.short_description = 'Турниров'


class MatchInline(admin.TabularInline):
    model = Match
    extra = 0
    fields = ['team_a', 'team_b', 'date_time', 'venue', 'stage', 'round_number', 'sets_a', 'sets_b', 'is_finished']
    autocomplete_fields = ['team_a', 'team_b', 'venue']


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'group', 'gender', 'tournament_type', 'number_of_rounds', 'has_playoff', 'created_at']
    list_filter = ['gender', 'tournament_type', 'has_playoff', 'group']
    search_fields = ['name']
    filter_horizontal = ['teams']
    inlines = [MatchInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'group', 'gender', 'order')
        }),
        ('Параметры турнира', {
            'fields': ('tournament_type', 'number_of_rounds', 'has_playoff', 'playoff_teams')
        }),
        ('Команды', {
            'fields': ('teams',)
        }),
    )


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'tournament', 'date_time', 'venue', 'stage', 'round_number', 'get_score_display',
                    'is_finished']
    list_filter = ['tournament', 'stage', 'is_finished', 'date_time']
    search_fields = ['team_a__name', 'team_b__name']
    autocomplete_fields = ['team_a', 'team_b', 'venue']
    date_hierarchy = 'date_time'

    fieldsets = (
        ('Основная информация', {
            'fields': ('tournament', 'team_a', 'team_b', 'venue', 'date_time')
        }),
        ('Этап', {
            'fields': ('stage', 'round_number')
        }),
        ('Результат', {
            'fields': ('sets_a', 'sets_b', 'set_scores', 'is_finished')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tournament', 'team_a', 'team_b', 'venue')


@admin.register(StandingsCache)
class StandingsCacheAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'team', 'played', 'won', 'lost', 'sets_won', 'sets_lost', 'points']
    list_filter = ['tournament']
    search_fields = ['team__name']
    readonly_fields = ['played', 'won', 'lost', 'sets_won', 'sets_lost', 'points']

    def has_add_permission(self, request):
        return False