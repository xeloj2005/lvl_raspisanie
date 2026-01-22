from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from tournament.models import Team, Venue, TournamentGroup, Tournament, Match
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Загружает данные женских дивизионов из info.txt'

    def handle(self, *args, **options):
        # Создаем группу турниров
        group, _ = TournamentGroup.objects.get_or_create(
            name='Женские дивизионы',
            defaults={'order': 10}
        )
        
        # Создаем место проведения по умолчанию
        venue, _ = Venue.objects.get_or_create(
            name='Спортивный зал',
            defaults={'address': 'Основной адрес'}
        )
        
        self.load_division_1(group, venue)
        self.load_division_2(group, venue)
        self.load_division_3(group, venue)
        
        self.stdout.write(self.style.SUCCESS('✓ Все дивизионы загружены успешно'))

    def load_division_1(self, group, venue):
        """Загружает 1 Дивизион женщины 1 круг"""
        # Команды
        team_names = ['СПАРТАК СКСХОС', 'CUCINA', 'NORDOST', 'КГУФКСТ', 'ЮВЕНТА', 'КОСМОС']
        teams = {}
        for name in team_names:
            team, _ = Team.objects.get_or_create(
                name=name,
                defaults={'gender': 'F'}
            )
            teams[name] = team
        
        # Турнир
        tournament, created = Tournament.objects.get_or_create(
            name='1 Дивизион женщины',
            group=group,
            defaults={
                'gender': 'F',
                'tournament_type': 'LEAGUE',
                'number_of_rounds': 1,
                'has_playoff': False,
                'order': 1
            }
        )
        tournament.teams.set(teams.values())
        
        if not created:
            self.stdout.write(f'Турнир "{tournament.name}" уже существует')
            return
        
        # Предварительный тур
        preliminary_matches = [
            ('СПАРТАК СКСХОС', 'NORDOST'),
            ('КГУФКСТ', 'КОСМОС'),
            ('КГУФКСТ', 'CUCINA'),
            ('ЮВЕНТА', 'СПАРТАК СКСХОС'),
            ('CUCINA', 'КОСМОС'),
            ('ЮВЕНТА', 'NORDOST'),
        ]
        
        for team_a_name, team_b_name in preliminary_matches:
            Match.objects.get_or_create(
                tournament=tournament,
                team_a=teams[team_a_name],
                team_b=teams[team_b_name],
                stage='PRELIMINARY',
                defaults={'venue': venue}
            )
        
        # Регулярные туры
        tours = {
            1: [
                ('СПАРТАК СКСХОС', 'КОСМОС', '30.11.2025'),
                ('CUCINA', 'ЮВЕНТА', '30.11.2025'),
                ('КГУФКСТ', 'NORDOST', '07.12.2025'),
            ],
            2: [
                ('СПАРТАК СКСХОС', 'CUCINA', '14.12.2025'),
            ],
            3: [
                ('NORDOST', 'СПАРТАК СКСХОС', '21.12.2025'),
                ('КГУФКСТ', 'ЮВЕНТА', '21.12.2025'),
            ],
            4: [
                ('КОСМОС', 'ЮВЕНТА', '18.01.2026'),
                ('СПАРТАК СКСХОС', 'КГУФКСТ', '18.01.2026'),
                ('CUCINA', 'NORDOST', '18.01.2026'),
            ],
            5: [
                ('NORDOST', 'КОСМОС', '25.01.2025'),
            ],
            6: [
                ('КОСМОС', 'СПАРТАК СКСХОС', '01.02.2026'),
                ('ЮВЕНТА', 'CUCINA', '01.02.2026'),
                ('КГУФКСТ', 'NORDOST', '01.02.2026'),
            ],
            7: [
                ('NORDOST', 'ЮВЕНТА', '15.02.2026'),
                ('CUCINA', 'СПАРТАК СКСХОС', '15.02.2026'),
                ('КГУФКСТ', 'КОСМОС', '15.02.2026'),
            ],
            8: [
                ('КОСМОС', 'CUCINA', '01.03.2026'),
                ('ЮВЕНТА', 'КГУФКСТ', '01.03.2026'),
            ],
            9: [
                ('ЮВЕНТА', 'КОСМОС', '15.03.2026'),
                ('КГУФКСТ', 'СПАРТАК СКСХОС', '15.03.2026'),
                ('NORDOST', 'CUCINA', '15.03.2026'),
            ],
            10: [
                ('КОСМОС', 'NORDOST', '29.03.2026'),
                ('CUCINA', 'КГУФКСТ', '29.03.2026'),
                ('СПАРТАК СКСХОС', 'ЮВЕНТА', '29.03.2026'),
            ],
        }
        
        for round_num, matches in tours.items():
            for team_a_name, team_b_name, date_str in matches:
                try:
                    date = datetime.strptime(date_str, '%d.%m.%Y')
                except:
                    date = None
                
                Match.objects.get_or_create(
                    tournament=tournament,
                    team_a=teams[team_a_name],
                    team_b=teams[team_b_name],
                    stage='REGULAR',
                    round_number=round_num,
                    defaults={
                        'venue': venue,
                        'date_time': date
                    }
                )
        
        self.stdout.write(self.style.SUCCESS(f'✓ 1 Дивизион загружен: {tournament.name}'))

    def load_division_2(self, group, venue):
        """Загружает 2 Дивизион женщины 2 круга"""
        team_names = ['КУБГУ', 'КЛЮКВА', 'СПАРТАК', 'ШТОРМ', 'РОСТЕЛЕКОМ', 'АРЕНА КОЛИЗЕЙ', 'КУБГТУ']
        teams = {}
        for name in team_names:
            team, _ = Team.objects.get_or_create(
                name=name,
                defaults={'gender': 'F'}
            )
            teams[name] = team
        
        tournament, created = Tournament.objects.get_or_create(
            name='2 Дивизион женщины',
            group=group,
            defaults={
                'gender': 'F',
                'tournament_type': 'LEAGUE',
                'number_of_rounds': 2,
                'has_playoff': False,
                'order': 2
            }
        )
        tournament.teams.set(teams.values())
        
        if not created:
            self.stdout.write(f'Турнир "{tournament.name}" уже существует')
            return
        
        # Предварительный тур
        preliminary_matches = [
            ('АРЕНА КОЛИЗЕЙ', 'КУБГТУ'),
            ('СПАРТАК', 'ШТОРМ'),
            ('РОСТЕЛЕКОМ', 'КЛЮКВА'),
        ]
        
        for team_a_name, team_b_name in preliminary_matches:
            Match.objects.get_or_create(
                tournament=tournament,
                team_a=teams[team_a_name],
                team_b=teams[team_b_name],
                stage='PRELIMINARY',
                defaults={'venue': venue}
            )
        
        # Регулярные туры
        tours = {
            1: [
                ('КЛЮКВА', 'КУБГТУ', '30.11.2025'),
                ('СПАРТАК', 'АРЕНА КОЛИЗЕЙ', '07.12.2025'),
                ('ШТОРМ', 'РОСТЕЛЕКОМ', '30.11.2025'),
            ],
            2: [
                ('АРЕНА КОЛИЗЕЙ', 'ШТОРМ', '14.12.2025'),
                ('КУБГТУ', 'СПАРТАК', '14.12.2025'),
                ('КУБГУ', 'КЛЮКВА', '14.12.2025'),
            ],
            3: [
                ('СПАРТАК', 'КУБГУ', '21.12.2025'),
                ('ШТОРМ', 'КУБГТУ', '21.12.2025'),
                ('РОСТЕЛЕКОМ', 'АРЕНА КОЛИЗЕЙ', '21.12.2025'),
            ],
            4: [
                ('КУБГТУ', 'РОСТЕЛЕКОМ', '18.01.2026'),
                ('КУБГУ', 'ШТОРМ', '18.01.2026'),
                ('КЛЮКВА', 'СПАРТАК', '18.01.2026'),
            ],
            5: [
                ('ШТОРМ', 'КЛЮКВА', '25.01.2026'),
                ('РОСТЕЛЕКОМ', 'КУБГУ', '25.01.2026'),
            ],
            6: [
                ('КУБГУ', 'АРЕНА КОЛИЗЕЙ', '08.02.2026'),
                ('КЛЮКВА', 'РОСТЕЛЕКОМ', '08.02.2026'),
            ],
            7: [
                ('РОСТЕЛЕКОМ', 'СПАРТАК', '15.02.2026'),
                ('АРЕНА КОЛИЗЕЙ', 'КЛЮКВА', '15.02.2026'),
                ('КУБГТУ', 'КУБГУ', '15.02.2026'),
            ],
            8: [
                ('КУБГТУ', 'КЛЮКВА', '22.02.2026'),
                ('АРЕНА КОЛИЗЕЙ', 'СПАРТАК', '22.02.2026'),
                ('РОСТЕЛЕКОМ', 'ШТОРМ', '22.02.2026'),
            ],
            9: [
                ('ШТОРМ', 'АРЕНА КОЛИЗЕЙ', '01.03.2026'),
                ('СПАРТАК', 'КУБГТУ', '01.03.2026'),
                ('КЛЮКВА', 'КУБГУ', '01.03.2026'),
            ],
            10: [
                ('КУБГУ', 'СПАРТАК', '15.03.2026'),
                ('КУБГТУ', 'ШТОРМ', '15.03.2026'),
                ('АРЕНА КОЛИЗЕЙ', 'РОСТЕЛЕКОМ', '15.03.2026'),
            ],
            11: [
                ('РОСТЕЛЕКОМ', 'КУБГТУ', '22.03.2026'),
                ('ШТОРМ', 'КУБГУ', '22.03.2026'),
                ('СПАРТАК', 'КЛЮКВА', '22.03.2026'),
            ],
            12: [
                ('КЛЮКВА', 'ШТОРМ', '29.03.2026'),
                ('КУБГУ', 'РОСТЕЛЕКОМ', '29.03.2026'),
                ('КУБГТУ', 'АРЕНА КОЛИЗЕЙ', '29.03.2026'),
            ],
            13: [
                ('АРЕНА КОЛИЗЕЙ', 'КУБГУ', '05.04.2026'),
                ('ШТОРМ', 'СПАРТАК', '05.04.2026'),
            ],
            14: [
                ('СПАРТАК', 'РОСТЕЛЕКОМ', '12.04.2026'),
                ('КЛЮКВА', 'АРЕНА КОЛИЗЕЙ', '12.04.2026'),
                ('КУБГУ', 'КУБГТУ', '12.04.2026'),
            ],
        }
        
        for round_num, matches in tours.items():
            for team_a_name, team_b_name, date_str in matches:
                try:
                    date = datetime.strptime(date_str, '%d.%m.%Y')
                except:
                    date = None
                
                Match.objects.get_or_create(
                    tournament=tournament,
                    team_a=teams[team_a_name],
                    team_b=teams[team_b_name],
                    stage='REGULAR',
                    round_number=round_num,
                    defaults={
                        'venue': venue,
                        'date_time': date
                    }
                )
        
        self.stdout.write(self.style.SUCCESS(f'✓ 2 Дивизион загружен: {tournament.name}'))

    def load_division_3(self, group, venue):
        """Загружает 3 Дивизион женщины"""
        team_names = ['ПЛАН Б', 'ОМЕГА', 'ФОРТУНА', 'МАГНИТ', 'ДОЛОМИТСТРОЙ', 'СКАЙС']
        teams = {}
        for name in team_names:
            team, _ = Team.objects.get_or_create(
                name=name,
                defaults={'gender': 'F'}
            )
            teams[name] = team
        
        tournament, created = Tournament.objects.get_or_create(
            name='3 Дивизион женщины',
            group=group,
            defaults={
                'gender': 'F',
                'tournament_type': 'LEAGUE',
                'number_of_rounds': 1,
                'has_playoff': False,
                'order': 3
            }
        )
        tournament.teams.set(teams.values())
        
        if not created:
            self.stdout.write(f'Турнир "{tournament.name}" уже существует')
            return
        
        # Предварительный тур
        preliminary_matches = [
            ('ОМЕГА', 'ДОЛОМИТСТРОЙ'),
            ('ПЛАН Б', 'СКАЙС'),
            ('ФОРТУНА', 'ПЛАН Б'),
            ('ОМЕГА', 'МАГНИТ'),
            ('МАГНИТ', 'ДОЛОМИТСТРОЙ'),
            ('СКАЙС', 'ФОРТУНА'),
        ]
        
        for team_a_name, team_b_name in preliminary_matches:
            Match.objects.get_or_create(
                tournament=tournament,
                team_a=teams[team_a_name],
                team_b=teams[team_b_name],
                stage='PRELIMINARY',
                defaults={'venue': venue}
            )
        
        # Регулярные туры
        tours = {
            1: [
                ('ФОРТУНА', 'ДОЛОМИТСТРОЙ', '07.12.2025'),
                ('ОМЕГА', 'СКАЙС', '30.11.2025'),
                ('МАГНИТ', 'ПЛАН Б', '07.12.2025'),
            ],
            2: [
                ('ДОЛОМИТСТРОЙ', 'ПЛАН Б', '14.12.2025'),
                ('СКАЙС', 'МАГНИТ', '14.12.2025'),
                ('ФОРТУНА', 'ОМЕГА', '14.12.2025'),
            ],
            3: [
                ('МАГНИТ', 'ФОРТУНА', '21.12.2025'),
                ('ДОЛОМИТСТРОЙ', 'СКАЙС', '21.12.2025'),
                ('ПЛАН Б', 'ОМЕГА', '21.12.2025'),
            ],
            6: [
                ('ДОЛОМИТСТРОЙ', 'ФОРТУНА', '18.01.2026'),
                ('СКАЙС', 'ОМЕГА', '18.01.2026'),
                ('ПЛАН Б', 'МАГНИТ', '18.01.2026'),
            ],
            7: [
                ('ПЛАН Б', 'ДОЛОМИТСТРОЙ', '25.01.2025'),
                ('МАГНИТ', 'СКАЙС', '25.01.2025'),
                ('ОМЕГА', 'ФОРТУНА', '25.01.2025'),
            ],
            8: [
                ('ДОЛОМИТСТРОЙ', 'ОМЕГА', '01.02.2026'),
                ('ФОРТУНА', 'МАГНИТ', '01.02.2026'),
                ('СКАЙС', 'ПЛАН Б', '01.02.2026'),
            ],
            9: [
                ('СКАЙС', 'ДОЛОМИТСТРОЙ', '15.02.2026'),
                ('ПЛАН Б', 'ФОРТУНА', '15.02.2026'),
                ('МАГНИТ', 'ОМЕГА', '15.02.2026'),
            ],
            10: [
                ('ДОЛОМИТСТРОЙ', 'МАГНИТ', '01.03.2026'),
                ('ОМЕГА', 'ПЛАН Б', '01.03.2026'),
                ('ФОРТУНА', 'СКАЙС', '01.03.2026'),
            ],
        }
        
        for round_num, matches in tours.items():
            for team_a_name, team_b_name, date_str in matches:
                try:
                    date = datetime.strptime(date_str, '%d.%m.%Y')
                except:
                    date = None
                
                Match.objects.get_or_create(
                    tournament=tournament,
                    team_a=teams[team_a_name],
                    team_b=teams[team_b_name],
                    stage='REGULAR',
                    round_number=round_num,
                    defaults={
                        'venue': venue,
                        'date_time': date
                    }
                )
        
        self.stdout.write(self.style.SUCCESS(f'✓ 3 Дивизион загружен: {tournament.name}'))
