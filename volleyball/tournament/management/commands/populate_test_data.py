from django.core.management.base import BaseCommand
from tournament.models import Team, Venue, TournamentGroup, Tournament, Match
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Загружает тестовые данные для двух турниров'

    def handle(self, *args, **options):
        # Очищаем старые данные (опционально)
        # Match.objects.all().delete()
        # Tournament.objects.all().delete()
        
        # Создаем площадки
        venue1, _ = Venue.objects.get_or_create(
            name='Спорткомплекс "Олимп"',
            defaults={'address': 'ул. Ленина, 10'}
        )
        venue2, _ = Venue.objects.get_or_create(
            name='Дворец спорта "Динамо"',
            defaults={'address': 'пр. Октября, 25'}
        )
        self.stdout.write(self.style.SUCCESS(f'✓ Созданы площадки'))

        # Создаем команды (мужские)
        team_m1, _ = Team.objects.get_or_create(
            name='Динамо',
            defaults={'gender': 'M'}
        )
        team_m2, _ = Team.objects.get_or_create(
            name='Спартак',
            defaults={'gender': 'M'}
        )
        team_m3, _ = Team.objects.get_or_create(
            name='ЦСКА',
            defaults={'gender': 'M'}
        )
        team_m4, _ = Team.objects.get_or_create(
            name='Локомотив',
            defaults={'gender': 'M'}
        )

        # Создаем команды (женские)
        team_f1, _ = Team.objects.get_or_create(
            name='Динамо (Ж)',
            defaults={'gender': 'F'}
        )
        team_f2, _ = Team.objects.get_or_create(
            name='Спартак (Ж)',
            defaults={'gender': 'F'}
        )
        team_f3, _ = Team.objects.get_or_create(
            name='ЦСКА (Ж)',
            defaults={'gender': 'F'}
        )
        team_f4, _ = Team.objects.get_or_create(
            name='Локомотив (Ж)',
            defaults={'gender': 'F'}
        )
        self.stdout.write(self.style.SUCCESS(f'✓ Созданы команды'))

        # Создаем группы турниров
        group1, _ = TournamentGroup.objects.get_or_create(
            name='Зимний чемпионат 2026',
            defaults={'order': 1}
        )
        group2, _ = TournamentGroup.objects.get_or_create(
            name='Летний кубок 2026',
            defaults={'order': 2}
        )
        self.stdout.write(self.style.SUCCESS(f'✓ Созданы группы турниров'))

        # Создаем турнир 1 - Мужской (с плэйоффом)
        tournament1, created = Tournament.objects.get_or_create(
            name='Мужской Чемпионат',
            group=group1,
            defaults={
                'gender': 'M',
                'tournament_type': 'LEAGUE',
                'number_of_rounds': 3,
                'has_playoff': True,
                'playoff_teams': 4,
            }
        )
        tournament1.teams.set([team_m1, team_m2, team_m3, team_m4])
        self.stdout.write(self.style.SUCCESS(f'✓ Создан турнир 1: {tournament1.name}'))

        # Создаем турнир 2 - Женский (без плэйофф)
        tournament2, created = Tournament.objects.get_or_create(
            name='Женский Чемпионат',
            group=group2,
            defaults={
                'gender': 'F',
                'tournament_type': 'LEAGUE',
                'number_of_rounds': 2,
                'has_playoff': False,
            }
        )
        tournament2.teams.set([team_f1, team_f2, team_f3, team_f4])
        self.stdout.write(self.style.SUCCESS(f'✓ Создан турнир 2: {tournament2.name}'))

        # Создаем матчи для турнира 1 (мужской) - 3 круга x 6 матчей = 18 матчей
        base_date = datetime.now()
        
        # Регулярный тур - все матчи 3 кругов
        match_data_m = [
            # Круг 1
            (team_m1, team_m2, 1, [(25, 20), (25, 22), (25, 18)]),  # 3:0
            (team_m1, team_m3, 1, [(25, 22), (23, 25), (25, 20), (25, 24)]),  # 3:1
            (team_m1, team_m4, 1, [(25, 18), (24, 26), (25, 21), (25, 20)]),  # 3:1
            (team_m2, team_m3, 1, [(25, 20), (25, 22), (25, 18)]),  # 3:0
            (team_m2, team_m4, 1, [(20, 25), (22, 25), (19, 25)]),  # 0:3
            (team_m3, team_m4, 1, [(25, 23), (25, 20), (25, 19)]),  # 3:0
            
            # Круг 2
            (team_m1, team_m2, 2, [(25, 21), (25, 23), (25, 19)]),  # 3:0
            (team_m1, team_m3, 2, [(23, 25), (25, 20), (25, 22), (25, 21)]),  # 3:1
            (team_m1, team_m4, 2, [(25, 17), (25, 19), (25, 20)]),  # 3:0
            (team_m2, team_m3, 2, [(25, 24), (20, 25), (25, 23)]),  # 3:1
            (team_m2, team_m4, 2, [(21, 25), (23, 25), (20, 25)]),  # 0:3
            (team_m3, team_m4, 2, [(25, 22), (25, 21), (25, 20)]),  # 3:0
            
            # Круг 3
            (team_m1, team_m2, 3, [(25, 19), (25, 21), (25, 20)]),  # 3:0
            (team_m1, team_m3, 3, [(25, 20), (25, 19), (25, 21)]),  # 3:0
            (team_m1, team_m4, 3, [(25, 16), (25, 18), (25, 19)]),  # 3:0
            (team_m2, team_m3, 3, [(25, 22), (22, 25), (25, 20), (25, 18)]),  # 3:1
            (team_m2, team_m4, 3, [(19, 25), (21, 25), (18, 25)]),  # 0:3
            (team_m3, team_m4, 3, [(25, 21), (25, 22), (25, 20)]),  # 3:0
        ]

        for team_a, team_b, round_num, scores in match_data_m:
            sets_a = sum(1 for a, b in scores if a > b)
            sets_b = sum(1 for a, b in scores if b > a)
            
            match, _ = Match.objects.get_or_create(
                tournament=tournament1,
                team_a=team_a,
                team_b=team_b,
                stage='REGULAR',
                round_number=round_num,
                defaults={
                    'venue': venue1,
                    'date_time': base_date + timedelta(days=round_num),
                    'is_finished': True,
                    'sets_a': sets_a,
                    'sets_b': sets_b,
                    'set_scores': [{'a': a, 'b': b} for a, b in scores],
                }
            )

        self.stdout.write(self.style.SUCCESS(f'✓ Созданы все {len(match_data_m)} матчей регулярного тура турнира 1'))

        # Создаем матчи для турнира 2 (женский)
        match_data_f = [
            (team_f1, team_f2, 1, [(25, 20), (25, 22), (25, 18)]),  # 3:0
            (team_f3, team_f4, 1, [(22, 25), (20, 25), (19, 25)]),  # 0:3
            (team_f1, team_f3, 2, [(25, 23), (25, 20), (25, 19)]),  # 3:0
            (team_f2, team_f4, 2, [(25, 22), (24, 26), (25, 23)]),  # 3:1
        ]

        for team_a, team_b, round_num, scores in match_data_f:
            match, _ = Match.objects.get_or_create(
                tournament=tournament2,
                team_a=team_a,
                team_b=team_b,
                stage='REGULAR',
                round_number=round_num,
                defaults={
                    'venue': venue2,
                    'date_time': base_date + timedelta(days=round_num),
                    'is_finished': True,
                    'sets_a': sum(1 for a, b in scores if a > b),
                    'sets_b': sum(1 for a, b in scores if b > a),
                    'set_scores': [{'a': a, 'b': b} for a, b in scores],
                }
            )

        self.stdout.write(self.style.SUCCESS(f'✓ Созданы матчи регулярного тура турнира 2'))

        # Добавляем матчи плэйофф для турнира 1
        playoff_matches = [
            ('QUARTER', None, team_m1, team_m4, [(25, 20), (25, 22), (25, 18)]),
            ('QUARTER', None, team_m2, team_m3, [(22, 25), (20, 25), (19, 25)]),
            ('SEMI', None, team_m1, team_m3, [(25, 23), (25, 20), (25, 19)]),
            ('SEMI', None, team_m2, team_m4, [(25, 22), (24, 26), (25, 23)]),
            ('FINAL', None, team_m1, team_m2, [(25, 20), (25, 22), (25, 18)]),
            ('THIRD', None, team_m3, team_m4, [(20, 25), (22, 25), (19, 25)]),
        ]

        for stage, round_num, team_a, team_b, scores in playoff_matches:
            match, _ = Match.objects.get_or_create(
                tournament=tournament1,
                team_a=team_a,
                team_b=team_b,
                stage=stage,
                round_number=round_num,
                defaults={
                    'venue': venue1,
                    'date_time': base_date + timedelta(days=10),
                    'is_finished': True,
                    'sets_a': sum(1 for a, b in scores if a > b),
                    'sets_b': sum(1 for a, b in scores if b > a),
                    'set_scores': [{'a': a, 'b': b} for a, b in scores],
                }
            )

        self.stdout.write(self.style.SUCCESS(f'✓ Созданы матчи плэйофф турнира 1'))

        self.stdout.write(self.style.SUCCESS('\n✅ Тестовые данные успешно загружены!'))
        self.stdout.write(f'\n📊 Статистика:')
        self.stdout.write(f'  • Команд: {Team.objects.count()}')
        self.stdout.write(f'  • Площадок: {Venue.objects.count()}')
        self.stdout.write(f'  • Турниров: {Tournament.objects.count()}')
        self.stdout.write(f'  • Матчей: {Match.objects.count()}')
