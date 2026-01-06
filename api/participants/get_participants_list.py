from flask import request, jsonify, session
from datetime import datetime
import time
import logging

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors, cache_result

from . import participants_bp


logger = logging.getLogger(__name__)


@participants_bp.route('/participants/list', methods=['GET'])
@log_action('获取参赛者列表')
@handle_db_errors
@cache_result(timeout=5)
def api_get_participants_list():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    db_manager = DatabaseManager()

    t_start = time.perf_counter()

    event_id = request.args.get('event_id')
    category = request.args.get('category')
    category_type = request.args.get('category_type')
    age_group = request.args.get('age_group')
    gender = request.args.get('gender')
    search_term = request.args.get('search')

    try:
        page = int(request.args.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1

    try:
        per_page = int(request.args.get('per_page', 20))
    except (TypeError, ValueError):
        per_page = 20
    if per_page < 1:
        per_page = 20
    if per_page > 200:
        per_page = 200

    offset = (page - 1) * per_page

        # 只统计已提交队伍的参赛者：
        # 参赛者管理需要覆盖“队伍报名名单”里的所有选手。
        # 仅用 participants 作为主表会漏掉：team_players 中存在但未生成 participants 记录（尤其 user_id 为空的历史/离线录入数据）。
        # 因此改为以 team_players 为主表，再左连接 participants/users/entries/event_items 补充字段。
    base_from = (
            ' FROM team_players tp '
            'JOIN teams t ON t.team_id = tp.team_id '
            ' AND t.event_id = tp.event_id '
            ' AND t.status = \'active\' '
            ' AND t.submitted_for_review = 1 '
            'JOIN events e ON e.event_id = tp.event_id '
            'LEFT JOIN users u ON u.user_id = tp.user_id '
            'LEFT JOIN participants p ON p.event_id = tp.event_id AND p.user_id = tp.user_id '
            'LEFT JOIN entries en ON en.registration_number = COALESCE(p.registration_number, tp.registration_number) '
            'LEFT JOIN event_items ei ON en.event_item_id = ei.event_item_id '
        )

    where_clauses = []
    params = []

    if event_id:
        where_clauses.append('tp.event_id = %s')
        params.append(event_id)

    if category:
        where_clauses.append('(' +
                             'tp.competition_event LIKE %s OR '
                             'tp.selected_events LIKE %s OR '
                             'p.category LIKE %s OR '
                             'ei.name LIKE %s'
                             ')')
        pattern = f'%{category}%'
        params.extend([pattern, pattern, pattern, pattern])

        # 性别也不在SQL中做等值过滤，因为历史数据可能未写入gender
        # 在Python层基于持久化字段或身份证推导后再过滤

        # 注意：年龄组不在SQL中做等值过滤，因为历史数据可能未写入age_group，等值过滤会误排除
        # 在Python层基于持久化字段或身份证推导后再过滤并分页

    if search_term:
        where_clauses.append('('
                             'COALESCE(u.real_name, tp.name) LIKE %s OR '
                             'COALESCE(tp.id_card, p.registration_number, tp.registration_number) LIKE %s OR '
                             'COALESCE(tp.phone, u.phone) LIKE %s OR '
                             't.team_name LIKE %s'
                             ')')
        pattern = f'%{search_term}%'
        params.extend([pattern, pattern, pattern, pattern])

    where_sql = ''
    if where_clauses:
        where_sql = ' WHERE ' + ' AND '.join(where_clauses)

    select_fields = (
            'SELECT '
            'COALESCE(p.participant_id, tp.player_id) AS participant_id, '
            'tp.event_id AS event_id, '
            'tp.user_id AS user_id, '
            'COALESCE(p.registration_number, tp.registration_number) AS registration_number, '
            'p.event_member_no AS event_member_no, '
            'p.category AS category, '
            'COALESCE(p.status, tp.status) AS status, '
            'COALESCE(p.registered_at, tp.created_at) AS registered_at, '
            'COALESCE(p.gender, tp.gender) AS gender, '
            'COALESCE(p.age_group, NULL) AS age_group, '
            'COALESCE(u.real_name, tp.name) AS real_name, '
            'COALESCE(u.phone, tp.phone) AS phone, '
            'tp.phone AS player_phone, '
            'tp.id_card AS player_id_card, '
            'tp.competition_event AS player_competition_event, '
            'tp.selected_events AS player_selected_events, '
            'e.name AS event_name, '
            't.team_name AS team_name, '
            'ei.name AS event_item_name'
        )

    count_query = 'SELECT COUNT(*) AS total' + base_from + where_sql

    data_query_base = (
        select_fields
        + base_from
        + where_sql
        + ' ORDER BY p.registered_at DESC'
    )

    # 是否需要在Python层做过滤与分页（年龄组或性别任一存在）
    do_python_filter = bool(age_group or gender)

    t_after_params = time.perf_counter()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        if do_python_filter:
            # 先不分页取出数据，后续在Python中过滤年龄组并分页
            if params:
                cursor.execute(data_query_base, tuple(params))
            else:
                cursor.execute(data_query_base)
            rows = cursor.fetchall()
            # total 暂不确定，待Python层过滤后计算
            total = None
        else:
            if params:
                cursor.execute(count_query, tuple(params))
            else:
                cursor.execute(count_query)

            row = cursor.fetchone()
            total = row['total'] if row else 0

            data_query = data_query_base + ' LIMIT %s OFFSET %s'
            data_params = params + [per_page, offset]
            cursor.execute(data_query, tuple(data_params))
            rows = cursor.fetchall()

    t_after_db = time.perf_counter()

    participants_list = []
    # 在循环外获取当前时间，避免对每条记录重复调用 datetime.now()
    today = datetime.now()
    for p in rows:
        # 优先使用 team_players 中同步的身份证号，其次使用 participants.registration_number
        id_card = p.get('player_id_card') or p['registration_number'] or ''

        competition_event = (p.get('player_competition_event') or '').strip()
        selected_events = (p.get('player_selected_events') or '').strip()
        resolved_category = competition_event or selected_events or p.get('event_item_name') or p.get('category')

        # 性别和年龄组优先使用表中的持久化字段，缺失时才从身份证兜底
        gender_value = p.get('gender')
        age_group_value = p.get('age_group')
        age = None

        if len(id_card) == 18:
            try:
                birth_year = int(id_card[6:10])
                birth_month = int(id_card[10:12])
                birth_day = int(id_card[12:14])

                age = today.year - birth_year
                if (today.month, today.day) < (birth_month, birth_day):
                    age -= 1

                # 如果性别为空，从身份证兜底计算
                if not gender_value:
                    gender_digit = int(id_card[-2])
                    gender_value = '男' if gender_digit % 2 == 1 else '女'

                # 如果年龄组为空，从年龄兜底计算（与旧逻辑一致）
                if age is not None and not age_group_value:
                    if age < 12:
                        age_group_value = '儿童组'
                    elif 12 <= age <= 17:
                        age_group_value = '少年组'
                    elif 18 <= age <= 39:
                        age_group_value = '青年组'
                    elif 40 <= age <= 59:
                        age_group_value = '中年组'
                    elif age >= 60:
                        age_group_value = '老年组'
            except Exception:
                age = None

        participants_list.append({
            'participant_id': p['participant_id'],
            'event_id': p['event_id'],
            'user_id': p['user_id'],
            # 对外继续使用 registration_number 字段名，但内容优先取 team_players.id_card
            'registration_number': id_card,
            'event_member_no': p.get('event_member_no'),
            'real_name': p['real_name'],
            # 手机号优先使用 team_players.phone，其次回退到 users.phone
            'phone': p.get('player_phone') or p['phone'],
            'event_name': p['event_name'],
            'team_name': p.get('team_name') or '',
            'category': resolved_category,
            'status': p['status'],
            'registered_at': p['registered_at'].isoformat() if p['registered_at'] else None,
            'gender': gender_value,
            'age': age,
            'age_group': age_group_value,
        })

    # 如果需要在Python层进行年龄组/性别过滤与分页，这里处理
    if do_python_filter:
        # 年龄组匹配（容忍带A/B/C组标注）
        def match_age_group(g):
            if not age_group:
                return True
            if not g:
                return False
            return age_group in g

        # 性别匹配：使用持久化/推导后的gender字段
        def match_gender(g):
            if not gender:
                return True
            return g == gender

        participants_list = [p for p in participants_list if match_age_group(p['age_group']) and match_gender(p['gender'])]

        total = len(participants_list)
        start = offset
        end = offset + per_page
        participants_list = participants_list[start:end]

    total_pages = (total + per_page - 1) // per_page if per_page else 1

    t_after_python = time.perf_counter()
    logger.info(
        "get_participants_list timings: params=%.1fms, db=%.1fms, python=%.1fms, total=%.1fms",
        (t_after_params - t_start) * 1000,
        (t_after_db - t_after_params) * 1000,
        (t_after_python - t_after_db) * 1000,
        (t_after_python - t_start) * 1000,
    )

    return jsonify({
        'success': True,
        'data': participants_list,
        'participants': participants_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
        },
    })
