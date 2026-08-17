import uuid
 
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
 
 
class Team(models.Model):
    """Команда. Создаётся любым зарегистрированным пользователем."""
 
    GENDER_CHOICES = [
        ('M', 'Мужская'),
        ('F', 'Женская'),
        ('X', 'Смешанная'),
    ]
 
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_DISBANDED = 'DISBANDED'
    STATUS_BANNED = 'BANNED'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Активна'),
        (STATUS_DISBANDED, 'Роспущена'),
        (STATUS_BANNED, 'Забанена'),
    ]
 
    name = models.CharField('Название', max_length=200)
    gender = models.CharField('Пол', max_length=1, choices=GENDER_CHOICES)
    logo = models.ImageField('Логотип', upload_to='teams/logos/', blank=True, null=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_teams',
        verbose_name='Создатель',
    )
    status = models.CharField('Статус', max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    ban_reason = models.TextField('Причина бана', blank=True)
    banned_at = models.DateTimeField('Дата бана', null=True, blank=True)
 
    class Meta:
        verbose_name = 'Команда'
        verbose_name_plural = 'Команды'
        ordering = ['name', 'gender']
 
    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"
 
    def is_active(self):
        return self.status == self.STATUS_ACTIVE
 
    def disband_if_empty(self):
        """Если в команде не осталось активных участников — распускаем."""
        has_members = self.memberships.filter(is_active=True).exists()
        if not has_members and self.status == self.STATUS_ACTIVE:
            self.status = self.STATUS_DISBANDED
            self.save(update_fields=['status'])
 
    def active_members(self):
        return self.memberships.filter(is_active=True).select_related('user')
 
    def has_role(self, user, role):
        return self.memberships.filter(user=user, is_active=True, roles__contains=role).exists()
 
 
class TeamRole:
    """Роли внутри команды. Не модель — просто константы + choices для форм."""
 
    OWNER = 'OWNER'      # создатель, не может быть снят кроме как роспуском команды
    ADMIN = 'ADMIN'      # управляет составом, приглашениями, подаёт заявки
    CAPTAIN = 'CAPTAIN'  # один на команду — представляет её на площадке
    MANAGER = 'MANAGER'  # орг. вопросы
    COACH = 'COACH'
    PLAYER = 'PLAYER'
 
    CHOICES = [
        (OWNER, 'Владелец'),
        (ADMIN, 'Администратор'),
        (CAPTAIN, 'Капитан'),
        (MANAGER, 'Менеджер'),
        (COACH, 'Тренер'),
        (PLAYER, 'Игрок'),
    ]
    VALID = [OWNER, ADMIN, CAPTAIN, MANAGER, COACH, PLAYER]
 
    # Роли из старой tournament.TeamMembership — на переходный период,
    # чтобы data migration не падала на несовпадении списков.
    LEGACY_MEMBER = 'MEMBER'
    LEGACY_ALL = [LEGACY_MEMBER, CAPTAIN, COACH]
 
 
class TeamMembership(models.Model):
    """Участие пользователя в команде с ролями. Одна активная запись на пару (team, user)."""
 
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships', verbose_name='Команда')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='team_memberships',
        verbose_name='Пользователь',
    )
    roles = models.JSONField('Роли', default=list)
    joined_at = models.DateTimeField('Дата вступления', auto_now_add=True)
    left_at = models.DateTimeField('Дата выхода', null=True, blank=True)
    is_active = models.BooleanField('Активное участие', default=True)
 
    class Meta:
        verbose_name = 'Участие в команде'
        verbose_name_plural = 'Участия в командах'
        # разрешаем повторный join после выхода (is_active=False), но не два активных подряд
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'user'],
                condition=models.Q(is_active=True),
                name='uniq_active_team_membership',
            )
        ]
 
    def __str__(self):
        return f'{self.user} @ {self.team} ({", ".join(self.roles or [])})'
 
    def clean(self):
        if not isinstance(self.roles, (list, tuple)):
            raise ValidationError('Роли должны быть списком')
        for r in self.roles:
            if r not in TeamRole.VALID and r not in TeamRole.LEGACY_ALL:
                raise ValidationError(f'Неизвестная роль: {r}')
 
    def has_role(self, role):
        return role in (self.roles or [])
 
    def add_role(self, role):
        if role not in TeamRole.VALID:
            raise ValueError('Unknown role')
        if role == TeamRole.CAPTAIN:
            # Капитан — один на команду. Снимаем роль с остальных активных участников.
            self._reassign_captain()
        if role not in self.roles:
            self.roles = [*self.roles, role]
            self.save(update_fields=['roles'])
 
    def _reassign_captain(self):
        for m in TeamMembership.objects.filter(team=self.team, is_active=True).exclude(pk=self.pk):
            if TeamRole.CAPTAIN in (m.roles or []):
                m.roles = [r for r in m.roles if r != TeamRole.CAPTAIN]
                m.save(update_fields=['roles'])
 
    def remove_role(self, role):
        if role in (self.roles or []):
            self.roles = [r for r in self.roles if r != role]
            self.save(update_fields=['roles'])
 
 
def create_team_with_owner(*, name, gender, creator, logo=None):
    """Сервис создания команды: автор получает OWNER+ADMIN+CAPTAIN+PLAYER."""
    team = Team.objects.create(name=name, gender=gender, creator=creator, logo=logo)
    TeamMembership.objects.create(
        team=team,
        user=creator,
        roles=[TeamRole.OWNER, TeamRole.ADMIN, TeamRole.CAPTAIN, TeamRole.PLAYER],
    )
    return team
 
 
class TeamInvitation(models.Model):
    """Приглашение в команду: по существующему пользователю или по email."""
 
    STATUS_PENDING = 'PENDING'
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает'),
        (STATUS_ACCEPTED, 'Принято'),
        (STATUS_REJECTED, 'Отклонено'),
        (STATUS_CANCELLED, 'Отменено'),
    ]
 
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='invitations', verbose_name='Команда')
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='team_invitations',
        verbose_name='Приглашённый пользователь',
    )
    invited_email = models.EmailField('Email приглашённого', blank=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_team_invitations',
        verbose_name='Кто пригласил',
    )
    status = models.CharField('Статус', max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
    token = models.UUIDField('Токен', default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    processed_at = models.DateTimeField('Дата обработки', null=True, blank=True)
 
    class Meta:
        verbose_name = 'Приглашение в команду'
        verbose_name_plural = 'Приглашения в команду'
        ordering = ['-created_at']
 
    def __str__(self):
        target = self.invited_user or self.invited_email
        return f'{self.team} → {target} [{self.status}]'
 
    def clean(self):
        if not self.invited_user and not self.invited_email:
            raise ValidationError('Нужно указать пользователя или email')
        if self.invited_user and TeamMembership.objects.filter(
            team=self.team, user=self.invited_user, is_active=True
        ).exists():
            raise ValidationError('Пользователь уже состоит в этой команде')
 
    def accept(self):
        if self.status != self.STATUS_PENDING:
            raise ValidationError('Приглашение уже обработано')
        if not self.invited_user:
            raise ValidationError('Приглашение не привязано к аккаунту — нужно сначала залогиниться по ссылке')
 
        membership, created = TeamMembership.objects.get_or_create(
            team=self.team, user=self.invited_user,
            defaults={'roles': [TeamRole.PLAYER]},
        )
        if not created and not membership.is_active:
            membership.is_active = True
            membership.left_at = None
            membership.roles = membership.roles or [TeamRole.PLAYER]
            membership.save(update_fields=['is_active', 'left_at', 'roles'])
 
        self.status = self.STATUS_ACCEPTED
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at'])
        return membership
 
    def reject(self):
        self.status = self.STATUS_REJECTED
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at'])
 
    def cancel(self):
        self.status = self.STATUS_CANCELLED
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at'])