from flask import request, jsonify, session

import re

from database import DatabaseManager

from . import participants_bp


@participants_bp.route('/participants/team-fees', methods=['GET'])
def api_get_team_fees():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    event_id = request.args.get('event_id')
    team_id = request.args.get('team_id')

    if event_id:
        try:
            event_id_int = int(event_id)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'event_id 无效'}), 400
    else:
        event_id_int = None

    team_id_int = None
    if team_id:
        try:
            team_id_int = int(team_id)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'team_id 无效'}), 400

    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            # 若传入 team_id，则按 entries + events 单价计算该队伍费用（权威来源）
            if event_id_int is not None and team_id_int is not None:
                cursor.execute(
                    """
                    SELECT
                        team_name
                    FROM teams
                    WHERE event_id = %s AND team_id = %s
                    LIMIT 1
                    """,
                    (event_id_int, team_id_int),
                )
                team_row = cursor.fetchone() or {}
                team_name = team_row.get('team_name') or ''

                cursor.execute(
                    """
                    SELECT
                        COALESCE(individual_fee, 0) AS individual_fee,
                        COALESCE(pair_practice_fee, 0) AS pair_practice_fee,
                        COALESCE(team_competition_fee, 0) AS team_competition_fee
                    FROM events
                    WHERE event_id = %s
                    LIMIT 1
                    """,
                    (event_id_int,),
                )
                fee_row = cursor.fetchone() or {}
                individual_unit = float(fee_row.get('individual_fee') or 0)
                pair_unit = float(fee_row.get('pair_practice_fee') or 0)
                team_unit = float(fee_row.get('team_competition_fee') or 0)

                cursor.execute(
                    """
                    SELECT
                        entry_type,
                        COUNT(*) AS cnt
                    FROM entries
                    WHERE event_id = %s
                      AND team_id = %s
                      AND status NOT IN ('withdrawn', 'disqualified')
                    GROUP BY entry_type
                    """,
                    (event_id_int, team_id_int),
                )
                counts = {row['entry_type']: int(row['cnt'] or 0) for row in (cursor.fetchall() or [])}

                individual_count = counts.get('individual', 0)
                pair_count = counts.get('pair', 0)
                team_count = counts.get('team', 0)

                used_source = 'entries_x_events'

                # 历史/离线录入数据可能没有 entries.team_id 或未生成 entries，导致统计为 0。
                # 这里回退到 team_players 解析项目字符串，保证队伍资料页费用不为 0。
                if individual_count == 0 and pair_count == 0 and team_count == 0:
                    used_source = 'team_players_fallback'
                    cursor.execute(
                        """
                        SELECT
                            competition_event,
                            selected_events,
                            COALESCE(pair_registered, 0) AS pair_registered,
                            COALESCE(team_registered, 0) AS team_registered,
                            COALESCE(registration_number, '') AS registration_number
                        FROM team_players
                        WHERE event_id = %s AND team_id = %s
                        """,
                        (event_id_int, team_id_int),
                    )
                    player_rows = cursor.fetchall() or []

                    pair_token_regex = re.compile(r'(?:[^、]*对练（[^）]+）|(?:徒手|器械)[^、]*（[^）]+）)')

                    def count_individual_from_text(text: str) -> int:
                        if not text:
                            return 0
                        segments = [s.strip() for s in text.split('、') if s.strip()]
                        # 排除对练/团体，剩余视为单人项目
                        segments = [s for s in segments if ('对练' not in s and '团体赛' not in s)]
                        return len(segments)

                    def count_pair_from_text(text: str) -> int:
                        if not text:
                            return 0
                        return len(pair_token_regex.findall(text))

                    individual_projects = 0
                    pair_projects = 0
                    has_team_competition = False
                    for r in player_rows:
                        competition_text = (r.get('competition_event') or '').strip()
                        selected_text = (r.get('selected_events') or '').strip()

                        # selected_events 多为文本/JSON，不强依赖格式，优先用 competition_event 做解析
                        individual_projects += count_individual_from_text(competition_text)
                        pair_projects += count_pair_from_text(competition_text)

                        if not has_team_competition:
                            if r.get('team_registered'):
                                has_team_competition = True
                            elif '团体赛' in competition_text:
                                has_team_competition = True

                        # 兜底：若 competition_event 为空但有 pair_registered 标记
                        if not competition_text and r.get('pair_registered'):
                            pair_projects += 1

                        # 极兜底：都没有但有 selected_events 文本，就按分隔符拆
                        if not competition_text and selected_text:
                            individual_projects += len([s for s in selected_text.split('、') if s.strip()])

                    pair_groups = pair_projects // 2
                    individual_count = individual_projects
                    pair_count = pair_groups
                    team_count = 1 if has_team_competition else 0

                    counts = {
                        'individual': individual_count,
                        'pair': pair_count,
                        'team': team_count,
                    }

                individual_fee = individual_count * individual_unit
                pair_fee = pair_count * pair_unit
                team_fee = team_count * team_unit
                other_fee = 0.0
                total_fee = individual_fee + pair_fee + team_fee + other_fee

                return jsonify({
                    'success': True,
                    'team_fee': {
                        'team_id': team_id_int,
                        'team_name': team_name,
                        'event_id': event_id_int,
                        'individual_fee': float(individual_fee),
                        'pair_fee': float(pair_fee),
                        'team_fee': float(team_fee),
                        'other_fee': float(other_fee),
                        'total_fee': float(total_fee),
                        'counts': {
                            'individual': individual_count,
                            'pair': pair_count,
                            'team': team_count,
                        },
                        'units': {
                            'individual_fee': float(individual_unit),
                            'pair_practice_fee': float(pair_unit),
                            'team_competition_fee': float(team_unit),
                        }
                    },
                    'debug_info': {
                        'data_source': used_source,
                        'event_id': event_id,
                        'team_id': team_id,
                    }
                })

            # 允许待审核(pending)和已审核(approved)的队伍费用都参与统计
            params = []

            # 列表模式：以 teams 为主表，确保导出/统计覆盖赛事内所有已提交队伍
            if event_id_int is not None:
                params.append(event_id_int)
                query = """
                    SELECT
                        t.team_name,
                        e.name AS event_name,
                        COALESCE(ta_id.applicant_name, ta_name.applicant_name, '') AS leader_name,
                        COALESCE(ta_id.individual_fee, ta_name.individual_fee, 0) AS individual_fee,
                        COALESCE(ta_id.pair_practice_fee, ta_name.pair_practice_fee, 0) AS pair_fee,
                        COALESCE(ta_id.team_competition_fee, ta_name.team_competition_fee, 0) AS team_fee,
                        COALESCE(ta_id.other_fee, ta_name.other_fee, 0) AS other_fee,
                        COALESCE(ta_id.total_fee, ta_name.total_fee, 0) AS total_fee
                    FROM teams t
                    JOIN events e ON e.event_id = t.event_id
                    LEFT JOIN (
                        SELECT
                            ta.*
                        FROM team_applications ta
                        JOIN (
                            SELECT
                                event_id,
                                team_id,
                                MAX(application_id) AS max_id
                            FROM team_applications
                            WHERE status IN ('pending', 'approved')
                              AND team_id IS NOT NULL
                            GROUP BY event_id, team_id
                        ) latest
                          ON latest.max_id = ta.application_id
                    ) ta_id
                      ON ta_id.event_id = t.event_id
                     AND ta_id.team_id = t.team_id
                    LEFT JOIN (
                        SELECT
                            ta.*
                        FROM team_applications ta
                        JOIN (
                            SELECT
                                event_id,
                                team_name,
                                MAX(application_id) AS max_id
                            FROM team_applications
                            WHERE status IN ('pending', 'approved')
                              AND (team_id IS NULL OR team_id = 0)
                            GROUP BY event_id, team_name
                        ) latest
                          ON latest.max_id = ta.application_id
                    ) ta_name
                      ON ta_name.event_id = t.event_id
                     AND ta_name.team_name = t.team_name
                    WHERE t.event_id = %s
                      AND t.status = 'active'
                      AND t.submitted_for_review = 1
                    ORDER BY t.team_name
                """
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
            else:
                # 未指定赛事时维持原逻辑：返回 team_applications 里的所有队伍费用
                query = """
                    SELECT
                        ta.team_name,
                        e.name AS event_name,
                        ta.applicant_name AS leader_name,
                        COALESCE(ta.individual_fee, 0) AS individual_fee,
                        COALESCE(ta.pair_practice_fee, 0) AS pair_fee,
                        COALESCE(ta.team_competition_fee, 0) AS team_fee,
                        COALESCE(ta.other_fee, 0) AS other_fee,
                        COALESCE(ta.total_fee, 0) AS total_fee
                    FROM team_applications ta
                    JOIN events e ON ta.event_id = e.event_id
                    WHERE ta.status IN ('pending', 'approved')
                    ORDER BY ta.team_name
                """
                cursor.execute(query)
                rows = cursor.fetchall()

        team_fees_list = []
        for row in rows:
            team_fees_list.append({
                'team_name': row.get('team_name') or '未知队伍',
                'event_name': row.get('event_name') or '未知赛事',
                'leader_name': row.get('leader_name') or '',
                'individual_fee': float(row.get('individual_fee') or 0),
                'pair_fee': float(row.get('pair_fee') or 0),
                'team_fee': float(row.get('team_fee') or 0),
                'other_fee': float(row.get('other_fee') or 0),
                'total_fee': float(row.get('total_fee') or 0),
                'participants': [],
            })

        debug_info = {
            'data_source': 'teams_left_join_team_applications' if event_id_int is not None else 'team_applications',
            'teams_count': len(team_fees_list),
            'event_id': event_id,
        }

        return jsonify({
            'success': True,
            'team_fees': team_fees_list,
            'debug_info': debug_info,
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'查询队伍费用失败: {str(e)}',
        }), 500
