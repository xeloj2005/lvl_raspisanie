from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count, Sum, Case, When, IntegerField
from .models import TournamentGroup, Tournament, Match, Team
from collections import defaultdict
from django.contrib import messages
from functools import cmp_to_key

def format_ratio(value):
    if value is None:
        return '—'
    if value == float('inf'):
        return '∞'
    return f'{value:.3f}'

def index(request):

    if request.user.is_authenticated and hasattr(request.user, 'referee_profile'):
        referee = request.user.referee_profile

        search = request.GET.get('search', '').strip()
        tournament_filter = request.GET.get('tournament', '')
        stage_filter = request.GET.get('stage', '')
        finished_filter = request.GET.get('finished', '')

        matches = Match.objects.select_related(
            'tournament', 'team_a', 'team_b', 'venue'
        ).filter(is_finished=False).order_by('date_time', 'id')

        if search:
            matches = matches.filter(
                Q(team_a__name__icontains=search) |
                Q(team_b__name__icontains=search) |
                Q(venue__name__icontains=search) |
                Q(protocol_code__icontains=search)
            )

        if tournament_filter:
            matches = matches.filter(tournament_id=tournament_filter)

        if stage_filter:
            matches = matches.filter(stage=stage_filter)

        if finished_filter == 'finished':
            matches = matches.filter(is_finished=True)
        elif finished_filter == 'not_finished':
            matches = matches.filter(is_finished=False)

        tournaments = Tournament.objects.order_by('name')
        stages = Match.STAGE_CHOICES

        return render(request, 'tournament/index_matches.html', {
            'matches': matches,
            'tournaments': tournaments,
            'stages': stages,
            'search': search,
            'tournament_filter': tournament_filter,
            'stage_filter': stage_filter,
            'finished_filter': finished_filter,
            'referee': referee,
        })
    groups = TournamentGroup.objects.prefetch_related('tournaments').all()
    return render(request, 'tournament/index.html', {'groups': groups})


def tournament_detail(request, tournament_id):
    """Страница турнира с таблицами и расписанием"""
    tournament = get_object_or_404(
        Tournament.objects.prefetch_related('teams', 'matches__team_a', 'matches__team_b', 'matches__venue'),
        id=tournament_id
    )

    # Получаем таблицу
    standings = calculate_standings(tournament)

    # Получаем матричную таблицу
    matrix = calculate_matrix_table(tournament)

    # Получаем расписание по турам
    schedule = get_schedule_by_rounds(tournament)

    # Получаем матчи плэйофф сгруппированные по этапам
    playoff_matches = get_playoff_matches(tournament)

    # Получаем все группы для меню навигации
    all_groups = TournamentGroup.objects.prefetch_related('tournaments').all()

    context = {
        'tournament': tournament,
        'standings': standings,
        'matrix': matrix,
        'schedule': schedule,
        'playoff_matches': playoff_matches,
        'all_groups': all_groups,
    }

    return render(request, 'tournament/tournament_detail.html', context)


def calculate_standings(tournament):
    teams = tournament.teams.all()
    standings = []

    for team in teams:
        matches = Match.objects.filter(
            tournament=tournament,
            is_finished=True
        ).filter(
            Q(team_a=team) | Q(team_b=team)
        )

        played = matches.count()
        won = 0
        lost = 0
        sets_won = 0
        sets_lost = 0
        points_won = 0
        points_lost = 0
        tournament_points = 0

        for match in matches:
            if match.team_a == team:
                team_sets = match.sets_a or 0
                opp_sets = match.sets_b or 0
                sets_won += team_sets
                sets_lost += opp_sets

                if match.sets_a is not None and match.sets_b is not None:
                    if match.sets_a > match.sets_b:
                        won += 1
                    else:
                        lost += 1

                if match.set_scores:
                    for set_score in match.set_scores:
                        points_won += set_score.get('a', 0)
                        points_lost += set_score.get('b', 0)
            else:
                team_sets = match.sets_b or 0
                opp_sets = match.sets_a or 0
                sets_won += team_sets
                sets_lost += opp_sets

                if match.sets_a is not None and match.sets_b is not None:
                    if match.sets_b > match.sets_a:
                        won += 1
                    else:
                        lost += 1

                if match.set_scores:
                    for set_score in match.set_scores:
                        points_won += set_score.get('b', 0)
                        points_lost += set_score.get('a', 0)

            tournament_points += get_match_points_for_team(match, team)

        sets_ratio = float('inf') if sets_lost == 0 and sets_won > 0 else (sets_won / sets_lost if sets_lost else 0)
        balls_ratio = float('inf') if points_lost == 0 and points_won > 0 else (points_won / points_lost if points_lost else 0)

        standings.append({
            'team': team,
            'played': played,
            'won': won,
            'lost': lost,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'sets_diff': sets_won - sets_lost,
            'points_won': points_won,
            'points_lost': points_lost,
            'points_diff': points_won - points_lost,
            'tournament_points': tournament_points,
            'sets_ratio': sets_ratio,
            'balls_ratio': balls_ratio,
            'sets_ratio_display': format_ratio(sets_ratio),
            'balls_ratio_display': format_ratio(balls_ratio),
        })

    def compare_rows(a, b):
        if tournament.is_short_format:
            if a['won'] != b['won']:
                return -1 if a['won'] > b['won'] else 1
            if a['tournament_points'] != b['tournament_points']:
                return -1 if a['tournament_points'] > b['tournament_points'] else 1

            head_to_head = get_head_to_head_result(tournament, a['team'], b['team'])
            if head_to_head == 1:
                return -1
            if head_to_head == -1:
                return 1

            if a['sets_ratio'] != b['sets_ratio']:
                return -1 if a['sets_ratio'] > b['sets_ratio'] else 1
            if a['balls_ratio'] != b['balls_ratio']:
                return -1 if a['balls_ratio'] > b['balls_ratio'] else 1
            return -1 if a['team'].name < b['team'].name else 1 if a['team'].name > b['team'].name else 0

        if a['tournament_points'] != b['tournament_points']:
            return -1 if a['tournament_points'] > b['tournament_points'] else 1
        if a['sets_diff'] != b['sets_diff']:
            return -1 if a['sets_diff'] > b['sets_diff'] else 1
        if a['sets_won'] != b['sets_won']:
            return -1 if a['sets_won'] > b['sets_won'] else 1
        return -1 if a['team'].name < b['team'].name else 1 if a['team'].name > b['team'].name else 0

    standings.sort(key=cmp_to_key(compare_rows))
    return standings


def calculate_matrix_table(tournament):
    """Рассчитывает матричную таблицу"""
    teams = list(tournament.teams.all())
    matrix = []

    # Создаем структуру матрицы
    for team_a in teams:
        row = {'team': team_a, 'results': []}

        for team_b in teams:
            if team_a == team_b:
                row['results'].append({'is_self': True})
            else:
                # Находим матчи между этими командами
                matches = Match.objects.filter(
                    tournament=tournament,
                    is_finished=True
                ).filter(
                    (Q(team_a=team_a) & Q(team_b=team_b)) |
                    (Q(team_a=team_b) & Q(team_b=team_a))
                ).order_by('round_number')

                results = []
                for match in matches:
                    if match.team_a == team_a:
                        results.append(f"{match.sets_a}:{match.sets_b}")
                    else:
                        results.append(f"{match.sets_b}:{match.sets_a}")

                row['results'].append({
                    'is_self': False,
                    'scores': results if results else ['-']
                })

        matrix.append(row)

    return {'teams': teams, 'matrix': matrix}


def get_schedule_by_rounds(tournament):
    """Получает расписание, сгруппированное по турам"""
    matches = Match.objects.filter(tournament=tournament).order_by('date_time', 'round_number')

    schedule = defaultdict(list)
    max_round_from_matches = 0

    for match in matches:
        # Отслеживаем максимальный round_number из матчей
        if match.stage == 'REGULAR' and match.round_number:
            max_round_from_matches = max(max_round_from_matches, match.round_number)
        
        if match.stage == 'PRELIMINARY':
            key = 'Предварительный этап'
        elif match.stage == 'REGULAR':
            key = f"Тур {match.round_number}"
        elif match.stage == 'QUARTER':
            key = '1/4 финала'
        elif match.stage == 'SEMI':
            key = '1/2 финала'
        elif match.stage == 'THIRD':
            key = 'Матч за 3 место'
        elif match.stage == 'FINAL':
            key = 'Финал'
        else:
            key = 'Другое'

        schedule[key].append(match)

    # Преобразуем defaultdict в обычный список кортежей для шаблона
    schedule_list = []

    # Сначала предварительный этап
    if 'Предварительный этап' in schedule:
        schedule_list.append(('Предварительный этап', schedule['Предварительный этап']))

    # Потом туры - используем максимальный номер тура из матчей
    max_round = max_round_from_matches
    
    # Если туры не задали явно, вычисляем максимальное количество туров
    if max_round == 0:
        teams_count = tournament.teams.count()
        max_round = teams_count * tournament.number_of_rounds if teams_count > 0 else 0

    for i in range(1, max_round + 1):
        key = f"Тур {i}"
        if key in schedule:
            schedule_list.append((key, schedule[key]))

    # Плейофф
    playoff_stages = ['1/4 финала', '1/2 финала', 'Матч за 3 место', 'Финал']
    for stage in playoff_stages:
        if stage in schedule:
            schedule_list.append((stage, schedule[stage]))

    return schedule_list


def check_and_generate_playoff(tournament):
    """
    Проверяет, все ли регулярные матчи сыграны.
    Если да - генерирует плэйофф (если его еще нет)
    """
    if tournament.is_short_format:
        return False
    if not tournament.has_playoff:
        return False

    # Получаем количество ожидаемых регулярных матчей
    teams_count = tournament.teams.count()
    if teams_count < 2:
        return False

    # Каждая команда должна сыграть с каждой
    # Количество матчей = C(n, 2) = n*(n-1)/2, умножено на количество кругов
    expected_matches = (teams_count * (teams_count - 1) // 2) * tournament.number_of_rounds

    # Считаем завершенные регулярные матчи (REGULAR или PRELIMINARY)
    completed_regular_matches = Match.objects.filter(
        tournament=tournament,
        stage__in=['REGULAR', 'PRELIMINARY'],
        is_finished=True
    ).count()

    # Если все регулярные матчи сыграны и плэйофф еще не создан
    if completed_regular_matches >= expected_matches and expected_matches > 0:
        # Проверяем, есть ли уже матчи плэйофф
        playoff_matches_exist = Match.objects.filter(
            tournament=tournament,
            stage__in=['QUARTER', 'SEMI', 'THIRD', 'FINAL']
        ).exists()

        if not playoff_matches_exist:
            # Получаем турнирную таблицу для определения сильнейших команд
            standings = calculate_standings(tournament)

            # Если есть хотя бы 4 команды, можем создать плэйофф
            if len(standings) >= 4:
                # Берем топ-4 команды для плэйофф
                top_4 = standings[:4]

                # Первые две полу-финала
                semifinal_1_teams = [top_4[0]['team'], top_4[3]['team']]  # 1 vs 4
                semifinal_2_teams = [top_4[1]['team'], top_4[2]['team']]  # 2 vs 3

                # Создаем полу-финалы
                Match.objects.create(
                    tournament=tournament,
                    team_a=semifinal_1_teams[0],
                    team_b=semifinal_1_teams[1],
                    stage='SEMI',
                    round_number=None,
                )

                Match.objects.create(
                    tournament=tournament,
                    team_a=semifinal_2_teams[0],
                    team_b=semifinal_2_teams[1],
                    stage='SEMI',
                    round_number=None,
                )

                return True

    return False


def get_playoff_matches(tournament):
    """
    Получает матчи плэйофф сгруппированные по этапам
    Возвращает список кортежей (этап_название, матчи)
    """
    playoff_stages = [
        ('QUARTER', '1/4 финала'),
        ('SEMI', '1/2 финала (Полуфиналы)'),
        ('THIRD', 'Матч за 3-е место'),
        ('FINAL', 'Финал'),
    ]
    
    result = []
    
    for stage_code, stage_name in playoff_stages:
        matches = Match.objects.filter(
            tournament=tournament,
            stage=stage_code,
        ).select_related('team_a', 'team_b', 'venue').order_by('date_time')
        
        if matches.exists():
            result.append((stage_name, list(matches)))
    
    return result

def protocol_code_entry(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()

        if not code:
            messages.error(request, 'Введите код матча')
            return render(request, 'tournament/code_entry.html', {
                'code': code,
            })

        match = Match.objects.filter(
            protocol_code=code,
        ).first()

        if not match:
            messages.error(request, 'Матч с таким кодом не найден или код не активен')
            return render(request, 'tournament/code_entry.html', {
                'code': code,
            })

        return redirect('match_protocol:squad_step', match_id=match.id,side="A")

    return render(request, 'tournament/code_entry.html')


def get_match_points_for_team(match, team):
    return match.get_match_points(team)

def get_head_to_head_result(tournament, team1, team2):
    """
    Возвращает:
    1  -> team1 выше team2 по личным встречам
    -1 -> team2 выше team1
    0  -> равенство / недостаточно данных
    """
    matches = Match.objects.filter(
        tournament=tournament,
        is_finished=True
    ).filter(
        (Q(team_a=team1) & Q(team_b=team2)) |
        (Q(team_a=team2) & Q(team_b=team1))
    )

    if not matches.exists():
        return 0

    team1_wins = 0
    team2_wins = 0
    team1_points = 0
    team2_points = 0
    team1_sets_won = 0
    team1_sets_lost = 0
    team1_balls_won = 0
    team1_balls_lost = 0

    for match in matches:
        if match.team_a == team1:
            s1, s2 = match.sets_a or 0, match.sets_b or 0
            team1_points += match.get_match_points(team1)
            team2_points += match.get_match_points(team2)
            team1_sets_won += s1
            team1_sets_lost += s2
            if match.set_scores:
                for set_score in match.set_scores:
                    team1_balls_won += set_score.get('a', 0)
                    team1_balls_lost += set_score.get('b', 0)
        else:
            s1, s2 = match.sets_b or 0, match.sets_a or 0
            team1_points += match.get_match_points(team1)
            team2_points += match.get_match_points(team2)
            team1_sets_won += s1
            team1_sets_lost += s2
            if match.set_scores:
                for set_score in match.set_scores:
                    team1_balls_won += set_score.get('b', 0)
                    team1_balls_lost += set_score.get('a', 0)

        if s1 > s2:
            team1_wins += 1
        elif s2 > s1:
            team2_wins += 1

    if team1_wins != team2_wins:
        return 1 if team1_wins > team2_wins else -1

    if team1_points != team2_points:
        return 1 if team1_points > team2_points else -1

    sets_ratio = (
        float('inf') if team1_sets_lost == 0 and team1_sets_won > 0
        else (team1_sets_won / team1_sets_lost if team1_sets_lost else 0)
    )
    opp_sets_ratio = (
        float('inf') if team1_sets_won == 0 and team1_sets_lost > 0
        else (team1_sets_lost / team1_sets_won if team1_sets_won else 0)
    )
    if sets_ratio != opp_sets_ratio:
        return 1 if sets_ratio > opp_sets_ratio else -1

    balls_ratio = (
        float('inf') if team1_balls_lost == 0 and team1_balls_won > 0
        else (team1_balls_won / team1_balls_lost if team1_balls_lost else 0)
    )
    opp_balls_ratio = (
        float('inf') if team1_balls_won == 0 and team1_balls_lost > 0
        else (team1_balls_lost / team1_balls_won if team1_balls_won else 0)
    )
    if balls_ratio != opp_balls_ratio:
        return 1 if balls_ratio > opp_balls_ratio else -1

    return 0