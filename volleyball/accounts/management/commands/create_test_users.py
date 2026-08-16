from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = 'Create demo users for development and testing'

    def handle(self, *args, **options):
        users = [
            {
                'email': 'admin@volleyball.local',
                'full_name': 'Администратор Система',
                'phone': '+79990000001',
                'password': 'Admin123!',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'email': 'captain@volleyball.local',
                'full_name': 'Алексей Смирнов',
                'phone': '+79990000002',
                'password': 'Player123!',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'email': 'player@volleyball.local',
                'full_name': 'Мария Петрова',
                'phone': '+79990000003',
                'password': 'Player123!',
                'is_staff': False,
                'is_superuser': False,
            },
        ]

        for data in users:
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'full_name': data['full_name'],
                    'phone': data['phone'],
                    'is_staff': data['is_staff'],
                    'is_superuser': data['is_superuser'],
                },
            )
            if created:
                user.set_password(data['password'])
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created user: {user.email}'))
            else:
                self.stdout.write(f'User already exists: {user.email}')

        self.stdout.write(self.style.SUCCESS('Test users are ready.'))
