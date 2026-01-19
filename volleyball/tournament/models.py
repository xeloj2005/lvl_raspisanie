from django.db import models
from django.core.validators import MinValueValidator


class TournamentGroup(models.Model):
    """Группа турниров (например: 'Сезон 2024', 'Кубок города')"""
    name = models.CharField('Название группы', max_length=200)
    order = models.IntegerField('Порядок отображения', default=0)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Группа турниров'
        verbose_name_plural = 'Группы турниров'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Venue(models.Model):
    """Место проведения игр"""
    name = models.CharField('Название', max_length=200)
    address = models.TextField('Адрес', blank=True)

    class Meta:
        verbose_name = 'Место проведения'
        verbose_name_plural = 'Места проведения'
        ordering = ['name']

    def __str__(self):
        return self.name


class Team(models.Model):
    """Команда"""
    GENDER_CHOICES = [
        ('M', 'Мужская'),
        ('F', 'Женская'),
    ]

    name = models.CharField('Название', max_length=200)
    gender = models.CharField('Пол', max_length=1, choices=GENDER_CHOICES)

    class Meta:
        verbose_name = 'Команда'
        verbose_name_plural = 'Команды'
        ordering = ['name', 'gender']

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"


class Tournament(models.Model):
    """Турнир"""
    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
    ]

    TOURNAMENT_TYPE_CHOICES = [
        ('LEAGUE', 'Лига (круговая система)'),
    ]

    name = models.CharField('Название', max_length=200)
    group = models.ForeignKey(
        TournamentGroup,
        on_delete=models.CASCADE,
        related_name='tournaments',
        verbose_name='Группа'
    )
    gender = models.CharField('Пол', max_length=1, choices=GENDER_CHOICES)
    tournament_type = models.CharField(
        'Тип турнира',
        max_length=20,
        choices=TOURNAMENT_TYPE_CHOICES,
        default='LEAGUE'
    )
    number_of_rounds = models.IntegerField(
        'Количество кругов',
        default=1,
        validators=[MinValueValidator(1)]
    )
    has_playoff = models.BooleanField('Плейофф', default=False)
    playoff_teams = models.IntegerField(
        'Команд в плейофф',
        choices=[(4, '4 команды'), (8, '8 команд')],
        null=True,
        blank=True
    )
    teams = models.ManyToManyField(
        Team,
        related_name='tournaments',
        verbose_name='Команды',
        blank=True
    )
    order = models.IntegerField('Порядок отображения', default=0)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Турнир'
        verbose_name_plural = 'Турниры'
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.has_playoff and not self.playoff_teams:
            raise ValidationError('Укажите количество команд в плейофф')


class Match(models.Model):
    """Матч"""
    STAGE_CHOICES = [
        ('PRELIMINARY', 'Предварительный этап'),
        ('REGULAR', 'Регулярный тур'),
        ('QUARTER', '1/4 финала'),
        ('SEMI', '1/2 финала'),
        ('THIRD', 'Матч за 3 место'),
        ('FINAL', 'Финал'),
    ]

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name='Турнир'
    )
    team_a = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='matches_as_team_a',
        verbose_name='Команда А'
    )
    team_b = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='matches_as_team_b',
        verbose_name='Команда Б'
    )
    venue = models.ForeignKey(
        Venue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Место проведения'
    )
    date_time = models.DateTimeField('Дата и время', null=True, blank=True)

    # Этап турнира
    stage = models.CharField('Этап', max_length=20, choices=STAGE_CHOICES)
    round_number = models.IntegerField('Номер тура', null=True, blank=True)

    # Счет
    sets_a = models.IntegerField('Сеты команды А', null=True, blank=True)
    sets_b = models.IntegerField('Сеты команды Б', null=True, blank=True)

    # Счет по сетам (сохраняем как JSON строку)
    set_scores = models.JSONField('Счет по сетам', null=True, blank=True, default=list)
    # Формат: [{"a": 25, "b": 20}, {"a": 23, "b": 25}, ...]

    is_finished = models.BooleanField('Завершен', default=False)

    class Meta:
        verbose_name = 'Матч'
        verbose_name_plural = 'Матчи'
        ordering = ['date_time', 'round_number']

    def __str__(self):
        score = ""
        if self.is_finished and self.sets_a is not None:
            score = f" {self.sets_a}:{self.sets_b}"
        return f"{self.team_a.name} - {self.team_b.name}{score}"

    def get_score_display(self):
        """Возвращает форматированный счет матча"""
        if not self.is_finished or self.sets_a is None:
            return "-"

        score_str = f"{self.sets_a}:{self.sets_b}"

        if self.set_scores:
            sets = [f"{s['a']}:{s['b']}" for s in self.set_scores]
            score_str += f" ({', '.join(sets)})"

        return score_str

    def clean(self):
        from django.core.exceptions import ValidationError

        # Проверка пола команд
        if self.team_a.gender != self.tournament.gender:
            raise ValidationError(f'Команда {self.team_a} не подходит по полу для этого турнира')
        if self.team_b.gender != self.tournament.gender:
            raise ValidationError(f'Команда {self.team_b} не подходит по полу для этого турнира')

        # Проверка, что команды разные
        if self.team_a == self.team_b:
            raise ValidationError('Команда не может играть сама с собой')


class StandingsCache(models.Model):
    """Кеш турнирной таблицы (для оптимизации)"""
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='standings_cache',
        verbose_name='Турнир'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        verbose_name='Команда'
    )

    # Статистика
    played = models.IntegerField('Игры', default=0)
    won = models.IntegerField('Победы', default=0)
    lost = models.IntegerField('Поражения', default=0)
    sets_won = models.IntegerField('Выигранные сеты', default=0)
    sets_lost = models.IntegerField('Проигранные сеты', default=0)
    points = models.IntegerField('Очки', default=0)

    class Meta:
        verbose_name = 'Турнирная таблица'
        verbose_name_plural = 'Турнирные таблицы'
        unique_together = ['tournament', 'team']
        ordering = ['-points', '-sets_won']

    def __str__(self):
        return f"{self.tournament.name} - {self.team.name}"