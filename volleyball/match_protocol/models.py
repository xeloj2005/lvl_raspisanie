from django.db import models
from django.core.validators import MinValueValidator

class MatchProtocolSession(models.Model):
    STEP_SQUAD_A = "squad_a"
    STEP_SQUAD_B = "squad_b"
    STEP_LINEUP_A = "lineup_a"
    STEP_LINEUP_B = "lineup_b"
    STEP_PROTOCOL = "protocol"

    STEP_CHOICES = [
        (STEP_SQUAD_A, "Заявка команды A"),
        (STEP_SQUAD_B, "Заявка команды B"),
        (STEP_LINEUP_A, "Расстановка команды A"),
        (STEP_LINEUP_B, "Расстановка команды B"),
        (STEP_PROTOCOL, "Протокол матча"),
    ]

    match = models.OneToOneField(
        "tournament.Match",
        on_delete=models.CASCADE,
        related_name="protocol_session",
        verbose_name="Матч",
    )
    current_step = models.CharField(
        max_length=20,
        choices=STEP_CHOICES,
        default=STEP_SQUAD_A,
        verbose_name="Текущий шаг",
    )

    squad_a_completed = models.BooleanField(default=False, verbose_name="Заявка A заполнена")
    squad_b_completed = models.BooleanField(default=False, verbose_name="Заявка B заполнена")
    lineup_a_completed = models.BooleanField(default=False, verbose_name="Расстановка A заполнена")
    lineup_b_completed = models.BooleanField(default=False, verbose_name="Расстановка B заполнена")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Сессия протокола"
        verbose_name_plural = "Сессии протокола"

    def __str__(self):
        return f"Протокол матча #{self.match_id}"


class MatchSquad(models.Model):
    SIDE_A = "A"
    SIDE_B = "B"
    SIDE_CHOICES = [
        (SIDE_A, "Команда A"),
        (SIDE_B, "Команда B"),
    ]

    session = models.ForeignKey(
        MatchProtocolSession,
        on_delete=models.CASCADE,
        related_name="squads",
        verbose_name="Сессия",
    )
    side = models.CharField(max_length=1, choices=SIDE_CHOICES, verbose_name="Сторона")
    tournament_roster = models.ForeignKey(
        "tournament.TournamentTeamRoster",
        on_delete=models.PROTECT,
        related_name="match_protocol_squads",
        verbose_name="Турнирный состав",
    )

    is_submitted = models.BooleanField(default=False, verbose_name="Этап сохранён")
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Время сохранения")

    class Meta:
        verbose_name = "Заявка на матч"
        verbose_name_plural = "Заявки на матч"
        unique_together = ("session", "side")

    def __str__(self):
        return f"Заявка {self.side} для матча #{self.session.match_id}"


class MatchSquadPlayer(models.Model):
    squad = models.ForeignKey(
        MatchSquad,
        on_delete=models.CASCADE,
        related_name="players",
        verbose_name="Заявка",
    )
    roster_player = models.ForeignKey(
        "tournament.TournamentRosterPlayer",
        on_delete=models.PROTECT,
        related_name="match_protocol_entries",
        verbose_name="Игрок турнирного состава",
    )

    is_active = models.BooleanField(default=False, verbose_name="В заявке")
    match_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Номер на матч",
    )
    is_libero = models.BooleanField(default=False, verbose_name="Либеро")
    is_captain = models.BooleanField(default=False, verbose_name="Капитан")

    class Meta:
        verbose_name = "Игрок заявки матча"
        verbose_name_plural = "Игроки заявки матча"
        unique_together = ("squad", "roster_player")

    def __str__(self):
        return f"{self.roster_player.player.full_name} / матч #{self.squad.session.match_id}"

class MatchLineup(models.Model):
    SIDE_A = "A"
    SIDE_B = "B"
    SIDE_CHOICES = [
        (SIDE_A, "Команда A"),
        (SIDE_B, "Команда B"),
    ]

    session = models.ForeignKey(
        "match_protocol.MatchProtocolSession",
        on_delete=models.CASCADE,
        related_name="lineups",
        verbose_name="Сессия",
    )
    side = models.CharField(max_length=1, choices=SIDE_CHOICES, verbose_name="Сторона")
    set_number = models.PositiveSmallIntegerField(default=1, verbose_name="Партия")

    is_submitted = models.BooleanField(default=False, verbose_name="Этап сохранён")
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Время сохранения")

    class Meta:
        verbose_name = "Расстановка"
        verbose_name_plural = "Расстановки"
        unique_together = ("session", "side", "set_number")

    def __str__(self):
        return f"Расстановка {self.side}, партия {self.set_number}, матч #{self.session.match_id}"


class MatchLineupPosition(models.Model):
    lineup = models.ForeignKey(
        MatchLineup,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name="Расстановка",
    )
    position = models.PositiveSmallIntegerField(verbose_name="Позиция")
    squad_player = models.ForeignKey(
        "match_protocol.MatchSquadPlayer",
        on_delete=models.PROTECT,
        related_name="lineup_positions",
        verbose_name="Игрок заявки",
    )

    class Meta:
        verbose_name = "Позиция расстановки"
        verbose_name_plural = "Позиции расстановки"
        unique_together = [
            ("lineup", "position"),
            ("lineup", "squad_player"),
        ]
        ordering = ["position"]

    def __str__(self):
        return f"Позиция {self.position} / расстановка #{self.lineup_id}"

class MatchProtocolSet(models.Model):
    SIDE_A = "A"
    SIDE_B = "B"
    SIDE_CHOICES = [
        (SIDE_A, "Команда A"),
        (SIDE_B, "Команда B"),
    ]

    session = models.ForeignKey(
        "match_protocol.MatchProtocolSession",
        on_delete=models.CASCADE,
        related_name="sets",
        verbose_name="Сессия",
    )
    set_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Номер сета",
    )

    side_a_is_left = models.BooleanField(default=True, verbose_name="Команда A слева")
    first_server_side = models.CharField(
        max_length=1,
        choices=SIDE_CHOICES,
        verbose_name="Первая подача",
    )

    is_finished = models.BooleanField(default=False, verbose_name="Сет завершён")
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="Подтверждён")

    side_switch_triggered = models.BooleanField(
        default=False,
        verbose_name="Смена сторон в 5-м сете уже была",
    )

    class Meta:
        verbose_name = "Сет протокола"
        verbose_name_plural = "Сеты протокола"
        unique_together = ("session", "set_number")
        ordering = ["set_number"]

    def __str__(self):
        return f"Сет {self.set_number} матча #{self.session.match_id}"


class MatchProtocolSetLineup(models.Model):
    SIDE_A = "A"
    SIDE_B = "B"
    SIDE_CHOICES = [
        (SIDE_A, "Команда A"),
        (SIDE_B, "Команда B"),
    ]

    protocol_set = models.ForeignKey(
        MatchProtocolSet,
        on_delete=models.CASCADE,
        related_name="lineups",
        verbose_name="Сет",
    )
    side = models.CharField(max_length=1, choices=SIDE_CHOICES, verbose_name="Сторона")
    position = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Позиция",
    )
    squad_player = models.ForeignKey(
        "match_protocol.MatchSquadPlayer",
        on_delete=models.PROTECT,
        related_name="set_lineup_positions",
        verbose_name="Игрок заявки",
    )

    class Meta:
        verbose_name = "Стартовая позиция в сете"
        verbose_name_plural = "Стартовые позиции в сете"
        unique_together = [
            ("protocol_set", "side", "position"),
            ("protocol_set", "side", "squad_player"),
        ]
        ordering = ["side", "position"]

    def __str__(self):
        return f"Сет {self.protocol_set_id} / {self.side} / позиция {self.position}"


class MatchProtocolEvent(models.Model):
    EVENT_POINT = "point"
    EVENT_TIMEOUT = "timeout"
    EVENT_SUBSTITUTION = "substitution"
    EVENT_SIDE_SWITCH = "side_switch"
    EVENT_SET_FINISH = "set_finish"

    EVENT_CHOICES = [
        (EVENT_POINT, "Очко"),
        (EVENT_TIMEOUT, "Тайм-аут"),
        (EVENT_SUBSTITUTION, "Замена"),
        (EVENT_SIDE_SWITCH, "Смена сторон"),
        (EVENT_SET_FINISH, "Завершение сета"),
    ]

    SIDE_A = "A"
    SIDE_B = "B"
    SIDE_CHOICES = [
        (SIDE_A, "Команда A"),
        (SIDE_B, "Команда B"),
    ]

    protocol_set = models.ForeignKey(
        MatchProtocolSet,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="Сет",
    )
    sequence_number = models.PositiveIntegerField(verbose_name="Порядок")

    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES, verbose_name="Тип события")
    side = models.CharField(max_length=1, choices=SIDE_CHOICES, null=True, blank=True, verbose_name="Сторона")

    score_a_before = models.PositiveSmallIntegerField(default=0)
    score_b_before = models.PositiveSmallIntegerField(default=0)
    score_a_after = models.PositiveSmallIntegerField(default=0)
    score_b_after = models.PositiveSmallIntegerField(default=0)

    server_side_before = models.CharField(max_length=1, choices=SIDE_CHOICES, null=True, blank=True)
    server_number_before = models.PositiveSmallIntegerField(null=True, blank=True)

    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Событие протокола"
        verbose_name_plural = "События протокола"
        unique_together = ("protocol_set", "sequence_number")
        ordering = ["sequence_number", "id"]

    def __str__(self):
        return f"{self.protocol_set} / {self.event_type} / #{self.sequence_number}"