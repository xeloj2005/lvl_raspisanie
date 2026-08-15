from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('full_name', 'Администратор')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField('Email', unique=True)
    full_name = models.CharField('ФИО', max_length=255)
    phone = models.CharField('Телефон', max_length=50, blank=True)
    vk = models.CharField('VK', max_length=255, blank=True)
    telegram = models.CharField('Telegram', max_length=255, blank=True)
    max = models.CharField('Max', max_length=255, blank=True)
    height = models.PositiveSmallIntegerField('Рост', null=True, blank=True)
    photo = models.ImageField('Фото', upload_to='users/', blank=True, null=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    rank = models.CharField('Разряд', max_length=100, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = UserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.full_name or self.email

    @property
    def initials(self):
        if not self.full_name:
            return self.email[:2].upper() if self.email else 'U'
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.full_name[:2].upper()

    @property
    def avatar_url(self):
        if self.photo and hasattr(self.photo, 'url'):
            return self.photo.url
        return ''

    @property
    def contact_ready(self):
        return bool(self.phone or self.vk or self.telegram or self.max)
