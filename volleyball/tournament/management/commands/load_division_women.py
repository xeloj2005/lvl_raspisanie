from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from tournament.models import Team, Venue, TournamentGroup, Tournament, Match
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Загружает данные мужских дивизионов из info.txt'

    def handle(self, *args, **options):
        # Создаем группу турниров
        group, _ = TournamentGroup.objects.get_or_create(
            name='Мужские дивизионы',
            defaults={'order': 20}
        )
        
        # Создаем место проведения по умолчанию
        venue, _ = Venue.objects.get_or_create(
            name='Спортивный зал',
            defaults={'address': 'Основной адрес'}
        )
        
        self.load_division_2_men(group, venue)
        self.load_division_3_men(group, venue)
        
        self.stdout.write(self.style.SUCCESS('✓ Все дивизионы загружены успешно'))

    def load_division_2_men(self, group, venue):
        """Загружает 2 Дивизион мужчины"""
        # Команды
        team_names = ['КУБГТУ', 'КАВКАЗ', 'ВЕНЕЦ', 'КБУ', 'ХАОС', 'КОСМОС', 'ROKUSSPORT', 
                      'АРЕНА КОЛИЗЕЙ', 'КВВУ', 'TOP GUN', 'МЕДИКИ', 'ЭЛЬВИРС']
        teams = {}
        for name in team_names:
            team, _ = Team.objects.get_or_create(
                name=name,
                defaults={'gender': 'M'}
            )
            teams[name] = team
        
        # Турнир
        tournament, created = Tournament.objects.get_or_create(
            name='2 Дивизион мужчины',
            group=group,
            defaults={
                'gender': 'M',
                'tournament_type': 'LEAGUE',
                'number_of_rounds': 1,
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
            ('TOP GUN', 'КАВКАЗ', '29.03.2026'),
            ('МЕДИКИ', 'ЭЛЬВИРС', '22.03.2026'),
            ('ROKUSSPORT', 'АРЕНА КОЛИЗЕЙ', '21.12.2025'),
            ('МЕДИКИ', 'ВЕНЕЦ', '07.12.2025'),
            ('АРЕНА КОЛИЗЕЙ', 'КОСМОС', '07.12.2025'),
            ('КОСМОС', 'ROKUSSPORT', '30.11.2025'),
            ('КБУ', 'КВВУ', '30.11.2025'),
            ('КАВКАЗ', 'МЕДИКИ', '30.11.2025'),
            ('ВЕНЕЦ', 'TOP GUN', '30.11.2025'),
            ('ХАОС', 'АРЕНА КОЛИЗЕЙ', '30.11.2025'),
        ]
        
        for team_a_name, team_b_name, date_str in preliminary_matches:
            try:
                date = datetime.strptime(date_str, '%d.%m.%Y')
            except:
                date = None
            
            Match.objects.get_or_create(
                tournament=tournament,
                team_a=teams[team_a_name],
                team_b=teams[team_b_name],
                stage='PRELIMINARY',
                defaults={'venue': venue, 'date_time': date}
            )
        
        # Регулярные туры
        tours = {
            2: [
                ('КУБГТУ', 'КАВКАЗ', '07.12.2025'),
                ('TOP GUN', 'КБУ', '07.12.2025'),
                ('КВВУ', 'ХАОС', '07.12.2025'),
                ('ЭЛЬВИРС', 'ROKUSSPORT', '07.12.2025'),
            ],
            3: [
                ('ВЕНЕЦ', 'КУБГТУ', '21.12.2025'),
                ('КБУ', 'МЕДИКИ', '21.12.2025'),
                ('ХАОС', 'TOP GUN', '21.12.2025'),
                ('КОСМОС', 'КВВУ', '21.12.2025'),
                ('КАВКАЗ', 'ЭЛЬВИРС', '21.12.2025'),
            ],
            4: [
                ('КУБГТУ', 'КБУ', '18.01.2026'),
                ('КАВКАЗ', 'ВЕНЕЦ', '18.01.2026'),
                ('МЕДИКИ', 'ХАОС', '18.01.2026'),
                ('TOP GUN', 'КОСМОС', '18.01.2026'),
                ('КВВУ', 'ROKUSSPORT', '18.01.2026'),
                ('ЭЛЬВИРС', 'АРЕНА КОЛИЗЕЙ', '18.01.2026'),
            ],
            5: [
                ('ХАОС', 'КУБГТУ', '01.02.2026'),
                ('КБУ', 'КАВКАЗ', '01.02.2026'),
                ('КОСМОС', 'МЕДИКИ', '01.02.2026'),
                ('ROKUSSPORT', 'TOP GUN', '01.02.2026'),
                ('АРЕНА КОЛИЗЕЙ', 'КВВУ', '01.02.2026'),
                ('ЭЛЬВИРС', 'ВЕНЕЦ', '01.02.2026'),
            ],
            6: [
                ('КУБГТУ', 'КОСМОС', '08.02.2026'),
                ('КАВКАЗ', 'ХАОС', '08.02.2026'),
                ('ВЕНЕЦ', 'КБУ', '08.02.2026'),
                ('МЕДИКИ', 'ROKUSSPORT', '08.02.2026'),
                ('TOP GUN', 'АРЕНА КОЛИЗЕЙ', '08.02.2026'),
                ('КВВУ', 'ЭЛЬВИРС', '08.02.2026'),
            ],
            7: [
                ('ROKUSSPORT', 'КУБГТУ', '22.02.2026'),
                ('КОСМОС', 'КАВКАЗ', '22.02.2026'),
                ('ВЕНЕЦ', 'ХАОС', '22.02.2026'),
                ('АРЕНА КОЛИЗЕЙ', 'МЕДИКИ', '22.02.2026'),
                ('КВВУ', 'TOP GUN', '22.02.2026'),
                ('КБУ', 'ЭЛЬВИРС', '22.02.2026'),
            ],
            8: [
                ('КУБГТУ', 'АРЕНА КОЛИЗЕЙ', '01.03.2026'),
                ('КАВКАЗ', 'ROKUSSPORT', '01.03.2026'),
                ('ВЕНЕЦ', 'КОСМОС', '01.03.2026'),
                ('КБУ', 'ХАОС', '01.03.2026'),
                ('МЕДИКИ', 'КВВУ', '01.03.2026'),
                ('ЭЛЬВИРС', 'TOP GUN', '01.03.2026'),
            ],
            9: [
                ('КВВУ', 'КУБГТУ', '15.03.2026'),
                ('АРЕНА КОЛИЗЕЙ', 'КАВКАЗ', '15.03.2026'),
                ('ROKUSSPORT', 'ВЕНЕЦ', '15.03.2026'),
                ('КОСМОС', 'КБУ', '15.03.2026'),
                ('TOP GUN', 'МЕДИКИ', '15.03.2026'),
                ('ХАОС', 'ЭЛЬВИРС', '15.03.2026'),
            ],
            10: [
                ('КУБГТУ', 'TOP GUN', '22.03.2026'),
                ('КАВКАЗ', 'КВВУ', '22.03.2026'),
                ('ВЕНЕЦ', 'АРЕНА КОЛИЗЕЙ', '22.03.2026'),
                ('КБУ', 'ROKUSSPORT', '22.03.2026'),
                ('ХАОС', 'КОСМОС', '22.03.2026'),
            ],
            11: [
                ('МЕДИКИ', 'КУБГТУ', '29.03.2026'),
                ('КВВУ', 'ВЕНЕЦ', '29.03.2026'),
                ('АРЕНА КОЛИЗЕЙ', 'КБУ', '29.03.2026'),
                ('ROKUSSPORT', 'ХАОС', '29.03.2026'),
                ('ЭЛЬВИРС', 'КОСМОС', '29.03.2026'),
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
        
        self.stdout.write(self.style.SUCCESS(f'✓ 2 Дивизион мужчины загружен: {tournament.name}'))

    def load_division_3_men(self, group, venue):
        """Загружает 3 Дивизион мужчины"""
        team_names = ['ЕВЕРСКИЙ РАЙОН', 'ОЛИМП', 'КУБГУ', 'ГВАРДИЯ СШОР №1', 'КВВАУЛ', 
                      'РОСТЕЛЕКОМ', 'БУРЕВЕСТНИК', 'МАГНИТ', 'ВАСЮРИНСКАЯ', 'КРОПОТКИН ЮГ', 'SNOWBALL']
        teams = {}
        for name in team_names:
            team, _ = Team.objects.get_or_create(
                name=name,
                defaults={'gender': 'M'}
            )
            teams[name] = team
        
        tournament, created = Tournament.objects.get_or_create(
            name='3 Дивизион мужчины',
            group=group,
            defaults={
                'gender': 'M',
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
            ('SNOWBALL', 'КВВАУЛ'),
            ('КРОПОТКИН ЮГ', 'ГВАРДИЯ СШОР №1'),
            ('ЕВЕРСКИЙ РАЙОН', 'ОЛИМП'),
            ('РОСТЕЛЕКОМ', 'БУРЕВЕСТНИК'),
            ('КУБГУ', 'КРОПОТКИН ЮГ'),
            ('МАГНИТ', 'ВАСЮРИНСКАЯ'),
            ('КРОПОТКИН ЮГ', 'МАГНИТ'),
            ('КУБГУ', 'ГВАРДИЯ СШОР №1'),
            ('ЕВЕРСКИЙ РАЙОН', 'РОСТЕЛЕКОМ'),
            ('БУРЕВЕСТНИК', 'ЕВЕРСКИЙ РАЙОН'),
            ('РОСТЕЛЕКОМ', 'ОЛИМП'),
            ('ВАСЮРИНСКАЯ', 'КРОПОТКИН ЮГ'),
            ('ОЛИМП', 'БУРЕВЕСТНИК'),
            ('КУБГУ', 'МАГНИТ'),
            ('ВАСЮРИНСКАЯ', 'КУБГУ'),
            ('МАГНИТ', 'ГВАРДИЯ СШОР №1'),
            ('ГВАРДИЯ СШОР №1', 'ВАСЮРИНСКАЯ'),
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
                ('ОЛИМП', 'SNOWBALL', '30.11.2025'),
                ('МАГНИТ', 'РОСТЕЛЕКОМ', '07.12.2025'),
                ('КВВАУЛ', 'МАГНИТ', '30.11.2025'),
            ],
            2: [
                ('SNOWBALL', 'КУБГУ', '07.12.2025'),
                ('ВАСЮРИНСКАЯ', 'КВВАУЛ', '07.12.2025'),
            ],
            3: [
                ('КУБГУ', 'ЕВЕРСКИЙ РАЙОН', '21.12.2025'),
                ('ГВАРДИЯ СШОР №1', 'SNOWBALL', '21.12.2025'),
                ('КВВАУЛ', 'КРОПОТКИН ЮГ', '21.12.2025'),
                ('РОСТЕЛЕКОМ', 'ВАСЮРИНСКАЯ', '21.12.2025'),
                ('БУРЕВЕСТНИК', 'МАГНИТ', '21.12.2025'),
            ],
            4: [
                ('ЕВЕРСКИЙ РАЙОН', 'ГВАРДИЯ СШОР №1', '18.01.2026'),
                ('ОЛИМП', 'КУБГУ', '18.01.2026'),
                ('КРОПОТКИН ЮГ', 'РОСТЕЛЕКОМ', '18.01.2026'),
                ('ВАСЮРИНСКАЯ', 'БУРЕВЕСТНИК', '18.01.2026'),
            ],
            5: [
                ('КВВАУЛ', 'ЕВЕРСКИЙ РАЙОН', '01.02.2026'),
                ('ГВАРДИЯ СШОР №1', 'ОЛИМП', '01.02.2026'),
                ('РОСТЕЛЕКОМ', 'SNOWBALL', '01.02.2026'),
                ('БУРЕВЕСТНИК', 'КРОПОТКИН ЮГ', '01.02.2026'),
            ],
            6: [
                ('ОЛИМП', 'КВВАУЛ', '08.02.2026'),
                ('SNOWBALL', 'БУРЕВЕСТНИК', '08.02.2026'),
            ],
            7: [
                ('КВВАУЛ', 'КУБГУ', '22.02.2026'),
                ('МАГНИТ', 'SNOWBALL', '22.02.2026'),
            ],
            8: [
                ('ЕВЕРСКИЙ РАЙОН', 'МАГНИТ', '01.03.2026'),
                ('КУБГУ', 'РОСТЕЛЕКОМ', '01.03.2026'),
                ('ГВАРДИЯ СШОР №1', 'КВВАУЛ', '01.03.2026'),
                ('SNOWBALL', 'ВАСЮРИНСКАЯ', '01.03.2026'),
            ],
            9: [
                ('ВАСЮРИНСКАЯ', 'ЕВЕРСКИЙ РАЙОН', '15.03.2026'),
                ('МАГНИТ', 'ОЛИМП', '15.03.2026'),
                ('БУРЕВЕСТНИК', 'КУБГУ', '15.03.2026'),
                ('РОСТЕЛЕКОМ', 'ГВАРДИЯ СШОР №1', '15.03.2026'),
                ('КРОПОТКИН ЮГ', 'SNOWBALL', '15.03.2026'),
            ],
            10: [
                ('ЕВЕРСКИЙ РАЙОН', 'КРОПОТКИН ЮГ', '22.03.2026'),
                ('ОЛИМП', 'ВАСЮРИНСКАЯ', '22.03.2026'),
                ('ГВАРДИЯ СШОР №1', 'БУРЕВЕСТНИК', '22.03.2026'),
                ('КВВАУЛ', 'РОСТЕЛЕКОМ', '22.03.2026'),
            ],
            11: [
                ('SNOWBALL', 'ЕВЕРСКИЙ РАЙОН', '29.03.2026'),
                ('КРОПОТКИН ЮГ', 'ОЛИМП', '29.03.2026'),
                ('БУРЕВЕСТНИК', 'КВВАУЛ', '29.03.2026'),
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
        
        self.stdout.write(self.style.SUCCESS(f'✓ 3 Дивизион мужчины загружен: {tournament.name}'))
