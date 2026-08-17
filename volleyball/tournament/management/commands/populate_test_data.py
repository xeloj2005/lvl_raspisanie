from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta, date

from tournament.models import (
    TournamentGroup,
    Venue,
    Team,
    Player,
    Tournament,
    Match,
    StandingsCache,
    TournamentTeamRoster,
    TournamentRosterPlayer,
)


class Command(BaseCommand):
    help = 'Заполняет базу тестовыми данными: турниры, команды, игроки, составы, матчи'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить существующие тестовые данные перед заполнением'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        clear = options['clear']

        if clear:
            self.stdout.write(self.style.WARNING('Удаление существующих тестовых данных...'))
            TournamentRosterPlayer.objects.all().delete()
            TournamentTeamRoster.objects.all().delete()
            Match.objects.all().delete()
            StandingsCache.objects.all().delete()
            Tournament.objects.all().delete()
            Player.objects.all().delete()
            Team.objects.all().delete()
            Venue.objects.all().delete()
            TournamentGroup.objects.all().delete()

        self.stdout.write('Создание групп турниров...')
        group_main = TournamentGroup.objects.create(
            name='Сезон 2026',
            order=1
        )
        group_youth = TournamentGroup.objects.create(
            name='Летние турниры 2026',
            order=2
        )

        self.stdout.write('Создание площадок...')
        venue_1 = Venue.objects.create(
            name='ФОК Центральный',
            address='г. Лиепая, ул. Спортивная, 1'
        )
        venue_2 = Venue.objects.create(
            name='Школа №7',
            address='г. Лиепая, ул. Молодёжная, 12'
        )

        self.stdout.write('Создание команд...')
        teams = {
            'meteor': Team.objects.create(name='Метеор', gender='M'),
            'burevestnik': Team.objects.create(name='Буревестник', gender='M'),
            'fakel': Team.objects.create(name='Факел', gender='M'),
            'dynamo': Team.objects.create(name='Динамо', gender='M'),
            'iskra': Team.objects.create(name='Искра', gender='F'),
            'volna': Team.objects.create(name='Волна', gender='F'),
            'aurora': Team.objects.create(name='Аврора', gender='F'),
            'zvezda': Team.objects.create(name='Звезда', gender='F'),
        }

        self.stdout.write('Создание игроков...')
        players_data = [
            ('Иванов Иван Иванович', date(2001, 5, 12), '1 разряд'),
            ('Петров Пётр Сергеевич', date(2000, 7, 3), 'КМС'),
            ('Сидоров Алексей Викторович', date(2002, 1, 18), '2 разряд'),
            ('Кузнецов Дмитрий Олегович', date(1999, 9, 9), '1 разряд'),
            ('Фёдоров Максим Андреевич', date(2003, 2, 27), '3 разряд'),
            ('Морозов Артём Игоревич', date(2001, 11, 15), '2 разряд'),
            ('Соколов Николай Романович', date(1998, 6, 21), 'КМС'),
            ('Васильев Егор Павлович', date(2004, 8, 30), '1 разряд'),
            ('Алексеева Мария Игоревна', date(2002, 4, 10), '1 разряд'),
            ('Смирнова Анна Сергеевна', date(2001, 12, 5), 'КМС'),
            ('Козлова Виктория Павловна', date(2003, 3, 14), '2 разряд'),
            ('Новикова Дарья Олеговна', date(2000, 10, 1), '1 разряд'),
            ('Павлова Екатерина Денисовна', date(1999, 6, 25), 'КМС'),
            ('Орлова София Андреевна', date(2004, 7, 11), '3 разряд'),
            ('Михайлова Полина Викторовна', date(2002, 9, 2), '2 разряд'),
            ('Белова Алина Романовна', date(2001, 1, 19), '1 разряд'),
            ('Григорьев Роман Павлович', date(2000, 2, 11), '1 разряд'),
            ('Ершов Кирилл Максимович', date(2003, 5, 6), '2 разряд'),
            ('Титов Владислав Игоревич', date(2001, 8, 17), 'КМС'),
            ('Николаев Степан Олегович', date(2004, 11, 29), '3 разряд'),
            ('Жукова Кристина Сергеевна', date(2000, 4, 28), '1 разряд'),
            ('Лебедева Юлия Андреевна', date(2002, 6, 8), '2 разряд'),
            ('Семенова Арина Павловна', date(2003, 9, 13), '1 разряд'),
            ('Гусева Валерия Игоревна', date(2001, 12, 22), 'КМС'),
        ]

        players = []
        for full_name, birth_date, rank in players_data:
            players.append(
                Player.objects.create(
                    full_name=full_name,
                    birth_date=birth_date,
                    rank=rank
                )
            )

        self.stdout.write('Создание турниров...')
        tournament_m = Tournament.objects.create(
            name='Мужская лига весна 2026',
            group=group_main,
            gender='M',
            tournament_type='LEAGUE',
            number_of_rounds=1,
            has_playoff=False,
            order=1
        )
        tournament_f = Tournament.objects.create(
            name='Женский кубок лета 2026',
            group=group_youth,
            gender='F',
            tournament_type='LEAGUE',
            number_of_rounds=1,
            has_playoff=False,
            order=2
        )

        tournament_m.teams.add(
            teams['meteor'],
            teams['burevestnik'],
            teams['fakel'],
            teams['dynamo'],
        )
        tournament_f.teams.add(
            teams['iskra'],
            teams['volna'],
            teams['aurora'],
            teams['zvezda'],
        )

        self.stdout.write('Создание составов на турниры...')

        # Мужской турнир
        roster_meteor = TournamentTeamRoster.objects.create(
            tournament=tournament_m,
            team=teams['meteor']
        )
        roster_burevestnik = TournamentTeamRoster.objects.create(
            tournament=tournament_m,
            team=teams['burevestnik']
        )
        roster_fakel = TournamentTeamRoster.objects.create(
            tournament=tournament_m,
            team=teams['fakel']
        )
        roster_dynamo = TournamentTeamRoster.objects.create(
            tournament=tournament_m,
            team=teams['dynamo']
        )

        # Женский турнир
        roster_iskra = TournamentTeamRoster.objects.create(
            tournament=tournament_f,
            team=teams['iskra']
        )
        roster_volna = TournamentTeamRoster.objects.create(
            tournament=tournament_f,
            team=teams['volna']
        )
        roster_aurora = TournamentTeamRoster.objects.create(
            tournament=tournament_f,
            team=teams['aurora']
        )
        roster_zvezda = TournamentTeamRoster.objects.create(
            tournament=tournament_f,
            team=teams['zvezda']
        )

        # Назначаем игроков в составы
        # Мужчины: players[0:12] + [16:20]
        men_players = players[0:8] + players[16:20]
        women_players = players[8:16] + players[20:24]

        roster_map_m = {
            roster_meteor: men_players[0:3],
            roster_burevestnik: men_players[3:6],
            roster_fakel: men_players[6:8],
            roster_dynamo: men_players[8:12],
        }

        roster_map_f = {
            roster_iskra: women_players[0:3],
            roster_volna: women_players[3:6],
            roster_aurora: women_players[6:8],
            roster_zvezda: women_players[8:12],
        }

        # Чтобы было не слишком пусто, добросим ещё по игроку в команды с 2 игроками
        extra_assignments = [
            (roster_fakel, men_players[12 - 1] if len(men_players) >= 12 else men_players[-1]),
            (roster_aurora, women_players[12 - 1] if len(women_players) >= 12 else women_players[-1]),
        ]

        for roster, roster_players in roster_map_m.items():
            for player in roster_players:
                TournamentRosterPlayer.objects.get_or_create(
                    roster=roster,
                    player=player
                )

        for roster, roster_players in roster_map_f.items():
            for player in roster_players:
                TournamentRosterPlayer.objects.get_or_create(
                    roster=roster,
                    player=player
                )

        # Без дублирования внутри турнира
        for roster, player in extra_assignments:
            if not TournamentRosterPlayer.objects.filter(
                roster__tournament=roster.tournament,
                player=player
            ).exists():
                TournamentRosterPlayer.objects.create(
                    roster=roster,
                    player=player
                )

        self.stdout.write('Создание матчей...')
        now = timezone.now()

        Match.objects.create(
            tournament=tournament_m,
            team_a=teams['meteor'],
            team_b=teams['burevestnik'],
            venue=venue_1,
            date_time=now + timedelta(days=1),
            stage='REGULAR',
            round_number=1,
            sets_a=3,
            sets_b=1,
            set_scores=[{'a': 25, 'b': 20}, {'a': 23, 'b': 25}, {'a': 25, 'b': 19}, {'a': 25, 'b': 21}],
            is_finished=True,
        )
        Match.objects.create(
            tournament=tournament_m,
            team_a=teams['fakel'],
            team_b=teams['dynamo'],
            venue=venue_2,
            date_time=now + timedelta(days=2),
            stage='REGULAR',
            round_number=1,
            sets_a=2,
            sets_b=3,
            set_scores=[{'a': 21, 'b': 25}, {'a': 25, 'b': 22}, {'a': 25, 'b': 19}, {'a': 20, 'b': 25}, {'a': 12, 'b': 15}],
            is_finished=True,
        )
        Match.objects.create(
            tournament=tournament_f,
            team_a=teams['iskra'],
            team_b=teams['volna'],
            venue=venue_1,
            date_time=now + timedelta(days=3),
            stage='REGULAR',
            round_number=1,
            sets_a=3,
            sets_b=0,
            set_scores=[{'a': 25, 'b': 17}, {'a': 25, 'b': 22}, {'a': 25, 'b': 18}],
            is_finished=True,
        )
        Match.objects.create(
            tournament=tournament_f,
            team_a=teams['aurora'],
            team_b=teams['zvezda'],
            venue=venue_2,
            date_time=now + timedelta(days=4),
            stage='REGULAR',
            round_number=1,
            sets_a=None,
            sets_b=None,
            set_scores=[],
            is_finished=False,
        )

        self.stdout.write('Создание базового кеша таблицы...')
        for team in tournament_m.teams.all():
            StandingsCache.objects.get_or_create(
                tournament=tournament_m,
                team=team,
                defaults={
                    'played': 0,
                    'won': 0,
                    'lost': 0,
                    'sets_won': 0,
                    'sets_lost': 0,
                    'points': 0,
                }
            )

        for team in tournament_f.teams.all():
            StandingsCache.objects.get_or_create(
                tournament=tournament_f,
                team=team,
                defaults={
                    'played': 0,
                    'won': 0,
                    'lost': 0,
                    'sets_won': 0,
                    'sets_lost': 0,
                    'points': 0,
                }
            )

        self.stdout.write(self.style.SUCCESS('Тестовые данные успешно созданы'))
        self.stdout.write(self.style.SUCCESS('Создано: 2 турнира, 8 команд, 24 игрока, составы и матчи'))