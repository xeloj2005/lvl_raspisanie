from django.core.management.base import BaseCommand
from tournament.models import Tournament
from tournament.views import check_and_generate_playoff


class Command(BaseCommand):
    help = 'Генерирует плэйофф для всех турниров'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tournament-id',
            type=int,
            help='ID конкретного турнира для генерации плэйофф'
        )

    def handle(self, *args, **options):
        tournament_id = options.get('tournament_id')

        if tournament_id:
            # Генерируем для конкретного турнира
            try:
                tournament = Tournament.objects.get(id=tournament_id)
                result = check_and_generate_playoff(tournament)
                if result:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Плэйофф успешно сгенерирован для "{tournament.name}"')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠ Не удалось сгенерировать плэйофф для "{tournament.name}"')
                    )
            except Tournament.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'✗ Турнир с ID {tournament_id} не найден'))
        else:
            # Генерируем для всех турниров с плэйофф
            tournaments = Tournament.objects.filter(has_playoff=True)
            count = 0
            for tournament in tournaments:
                result = check_and_generate_playoff(tournament)
                if result:
                    count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Плэйофф для "{tournament.name}"')
                    )

            self.stdout.write(
                self.style.SUCCESS(f'Плэйофф сгенерирован для {count} турниров')
            )
