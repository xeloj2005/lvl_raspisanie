from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count, Sum, Case, When, IntegerField
from .models import TournamentGroup, Tournament, Match, Team
from collections import defaultdict


def index(request):
    """Главная страница со списком групп турниров"""
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
    """Рассчитывает турнирную таблицу"""
    teams = tournament.teams.all()
    standings = []

    for team in teams:
        # Находим все матчи команды
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

        for match in matches:
            if match.team_a == team:
                sets_won += match.sets_a or 0
                sets_lost += match.sets_b or 0
                
                # Подсчет побед и поражений
                if match.sets_a and match.sets_b:
                    if match.sets_a > match.sets_b:
                        won += 1
                    else:
                        lost += 1
                
                # Подсчет очков по партиям
                if match.set_scores:
                    for set_score in match.set_scores:
                        points_won += set_score.get('a', 0)
                        points_lost += set_score.get('b', 0)
            else:
                sets_won += match.sets_b or 0
                sets_lost += match.sets_a or 0
                
                # Подсчет побед и поражений
                if match.sets_a and match.sets_b:
                    if match.sets_b > match.sets_a:
                        won += 1
                    else:
                        lost += 1
                
                # Подсчет очков по партиям
                if match.set_scores:
                    for set_score in match.set_scores:
                        points_won += set_score.get('b', 0)
                        points_lost += set_score.get('a', 0)

        # Подсчет очков турнира:
        # 3 за победу 3:0 или 3:1
        # 2 за победу 3:2
        # 1 за поражение 2:3
        # 0 за остальные поражения
        tournament_points = 0
        for match in matches:
            if match.team_a == team:
                if match.sets_a == 3 and match.sets_b in [0, 1]:
                    tournament_points += 3
                elif match.sets_a == 3 and match.sets_b == 2:
                    tournament_points += 2
                elif match.sets_b == 3 and match.sets_a == 2:
                    tournament_points += 1
                # Иначе 0 очков за поражение 1:3 или 0:3
            else:
                if match.sets_b == 3 and match.sets_a in [0, 1]:
                    tournament_points += 3
                elif match.sets_b == 3 and match.sets_a == 2:
                    tournament_points += 2
                elif match.sets_a == 3 and match.sets_b == 2:
                    tournament_points += 1
                # Иначе 0 очков за поражение 1:3 или 0:3

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
        })

    # Сортировка по очкам турнира, затем по разнице сетов, затем по выигранным сетам
    standings.sort(key=lambda x: (-x['tournament_points'], -x['sets_diff'], -x['sets_won']))

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