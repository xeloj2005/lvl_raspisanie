from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
import random

def generate_unique_protocol_code():
    while True:
        code = f"{random.randint(0, 99999999):08d}"
        if not Match.objects.filter(protocol_code=code).exists():
            return code

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
    coach = models.CharField('Тренер', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Команда'
        verbose_name_plural = 'Команды'
        ordering = ['name', 'gender']

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"


class Player(models.Model):
    """Игрок команды"""
    full_name = models.CharField('ФИО', max_length=255)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    rank = models.CharField('Разряд', max_length=100, blank=True)

    class Meta:
        verbose_name = 'Игрок'
        verbose_name_plural = 'Игроки'
        ordering = ['full_name']

    def __str__(self):
        return self.full_name


class Tournament(models.Model):
    """Турнир"""
    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
    ]

    TOURNAMENT_TYPE_CHOICES = [
        ('LEAGUE', 'Лига (круговая система, до 3 побед в партиях)'),
        ('SHORT', 'Короткий турнир (до 2 побед в партиях)'),
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
        if self.has_playoff and not self.playoff_teams:
            raise ValidationError('Укажите количество команд в плейофф')

        if self.is_short_format and self.has_playoff:
            raise ValidationError('Для короткого турнира плейофф не поддерживается')

    @property
    def is_short_format(self):
        return self.tournament_type == 'SHORT'

    def get_max_sets(self):
        return 3 if self.is_short_format else 5

    def get_sets_to_win(self):
        return 2 if self.is_short_format else 3


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

    # Счет по сетам
    set_scores = models.JSONField('Счет по сетам', null=True, blank=True, default=list)
    # Формат: [{"a": 25, "b": 20}, {"a": 23, "b": 25}, ...]

    is_finished = models.BooleanField('Завершен', default=False)

    protocol_code = models.CharField(
        'Код протокола',
        max_length=8,
        unique=True,
        blank=True,
        null=True
    )
    protocol_code_active = models.BooleanField('Код протокола активен', default=False)

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
        # Проверка пола команд
        if self.team_a.gender != self.tournament.gender:
            raise ValidationError(f'Команда {self.team_a} не подходит по полу для этого турнира')
        if self.team_b.gender != self.tournament.gender:
            raise ValidationError(f'Команда {self.team_b} не подходит по полу для этого турнира')

        # Проверка, что команды разные
        if self.team_a == self.team_b:
            raise ValidationError('Команда не может играть сама с собой')

        # Проверка, что команды добавлены в турнир
        if self.team_a_id and not self.tournament.teams.filter(pk=self.team_a_id).exists():
            raise ValidationError(f'Команда {self.team_a} не добавлена в выбранный турнир')
        if self.team_b_id and not self.tournament.teams.filter(pk=self.team_b_id).exists():
            raise ValidationError(f'Команда {self.team_b} не добавлена в выбранный турнир')
        if self.is_finished:
            if self.sets_a is None or self.sets_b is None:
                raise ValidationError('Для завершенного матча нужно указать счет по партиям')

            sets_to_win = self.get_sets_to_win()
            max_sets = self.get_max_sets()

            if self.sets_a < 0 or self.sets_b < 0:
                raise ValidationError('Счет по партиям не может быть отрицательным')

            if self.sets_a > sets_to_win or self.sets_b > sets_to_win:
                raise ValidationError('Некорректный счет по партиям для формата турнира')

            if self.sets_a != sets_to_win and self.sets_b != sets_to_win:
                raise ValidationError('В завершенном матче одна из команд должна набрать победное число партий')

            if self.sets_a + self.sets_b > max_sets:
                raise ValidationError('Слишком много сыгранных партий для формата турнира')

            if self.set_scores:
                if len(self.set_scores) != self.sets_a + self.sets_b:
                    raise ValidationError('Количество партий в детализации не совпадает с итоговым счетом')

                for idx, set_score in enumerate(self.set_scores, start=1):
                    a = set_score.get('a')
                    b = set_score.get('b')

                    if a is None or b is None:
                        raise ValidationError(f'В партии {idx} не заполнен счет')

                    if a < 0 or b < 0:
                        raise ValidationError(f'В партии {idx} счет не может быть отрицательным')

                    if a == b:
                        raise ValidationError(f'В партии {idx} не может быть ничьей')

                    target = 15 if (self.tournament.is_short_format and idx == 3) or (not self.tournament.is_short_format and idx == 5) else 25

                    winner = max(a, b)
                    loser = min(a, b)

                    if winner < target:
                        raise ValidationError(f'В партии {idx} победитель не добрал до {target} очков')

                    if winner - loser < 2:
                        raise ValidationError(f'В партии {idx} разница должна быть минимум 2 очка')

    def get_max_sets(self):
        return self.tournament.get_max_sets()

    def get_sets_to_win(self):
        return self.tournament.get_sets_to_win()

    def get_match_points(self, team):
        """
        Очки за матч для указанной команды.
        LEAGUE:
            3:0 / 3:1 -> 3
            3:2 -> 2
            2:3 -> 1
            иначе 0
        SHORT:
            2:0 -> 3
            2:1 -> 2
            1:2 -> 1
            0:2 -> 0
        """
        if not self.is_finished or self.sets_a is None or self.sets_b is None:
            return 0

        if team == self.team_a:
            won_sets, lost_sets = self.sets_a, self.sets_b
        elif team == self.team_b:
            won_sets, lost_sets = self.sets_b, self.sets_a
        else:
            return 0

        if self.tournament.is_short_format:
            if won_sets == 2 and lost_sets == 0:
                return 3
            if won_sets == 2 and lost_sets == 1:
                return 2
            if won_sets == 1 and lost_sets == 2:
                return 1
            return 0

        if won_sets == 3 and lost_sets in [0, 1]:
            return 3
        if won_sets == 3 and lost_sets == 2:
            return 2
        if won_sets == 2 and lost_sets == 3:
            return 1
        return 0

    def get_set_ratio(self):
        if not self.is_finished or self.sets_a is None or self.sets_b is None:
            return None
        if self.sets_b == 0:
            return float('inf')
        return self.sets_a / self.sets_b


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

class TournamentTeamRoster(models.Model):
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='rosters',
        verbose_name='Турнир'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='rosters',
        verbose_name='Команда'
    )

    class Meta:
        verbose_name = 'Состав команды на турнир'
        verbose_name_plural = 'Составы команд на турнир'
        unique_together = ['tournament', 'team']
        ordering = ['tournament', 'team']

    def __str__(self):
        return f'{self.tournament.name} — {self.team.name}'

    def clean(self):
        if self.team.gender != self.tournament.gender:
            raise ValidationError('Команда не подходит по полу для выбранного турнира')

        if self.team_id and not self.tournament.teams.filter(pk=self.team_id).exists():
            raise ValidationError('Команда не добавлена в выбранный турнир')

class TournamentRosterPlayer(models.Model):
    roster = models.ForeignKey(
        TournamentTeamRoster,
        on_delete=models.CASCADE,
        related_name='roster_players',
        verbose_name='Состав'
    )
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='rosters',
        verbose_name='Игрок'
    )

    class Meta:
        verbose_name = 'Игрок состава'
        verbose_name_plural = 'Игроки состава'
        unique_together = ['roster', 'player']
        ordering = ['player__full_name']

    def __str__(self):
        return self.player.full_name

class Referee(models.Model):
    """Судья"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referee_profile',
        verbose_name='Пользователь'
    )
    full_name = models.CharField('ФИО', max_length=255)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'Судья'
        verbose_name_plural = 'Судьи'
        ordering = ['full_name']

    def __str__(self):
        return self.full_name