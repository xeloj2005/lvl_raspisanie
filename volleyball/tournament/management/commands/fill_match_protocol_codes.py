from django.core.management.base import BaseCommand
from django.db import transaction

from volleyball.tournament.models import Match, generate_unique_protocol_code


class Command(BaseCommand):
    help = 'Заполняет protocol_code и protocol_code_active у существующих матчей'

    def add_arguments(self, parser):
        parser.add_argument(
            '--only-empty',
            action='store_true',
            help='Обновлять только матчи без protocol_code'
        )
        parser.add_argument(
            '--reactivate',
            action='store_true',
            help='Дополнительно активировать код у матчей'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        only_empty = options['only_empty']
        reactivate = options['reactivate']

        if only_empty:
            matches = Match.objects.filter(protocol_code__isnull=True) | Match.objects.filter(protocol_code='')
            matches = matches.distinct().order_by('id')
        else:
            matches = Match.objects.all().order_by('id')

        updated_count = 0

        for match in matches:
            changed = False

            if not match.protocol_code:
                match.protocol_code = generate_unique_protocol_code()
                changed = True

            if reactivate and not match.protocol_code_active:
                match.protocol_code_active = True
                changed = True
            elif match.protocol_code_active is None:
                match.protocol_code_active = True
                changed = True

            if changed:
                match.save(update_fields=['protocol_code', 'protocol_code_active'])
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Матч #{match.id}: code={match.protocol_code}, active={match.protocol_code_active}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f'Готово. Обновлено матчей: {updated_count}')
        )