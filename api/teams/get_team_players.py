from flask import jsonify, session
import json

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import teams_bp


@teams_bp.route('/team/<int:team_id>/players', methods=['GET'])
@log_action('获取队伍选手列表')
@handle_db_errors
def api_get_team_players(team_id):
    """获取指定队伍的选手列表 - 领队、队员、随行人员和管理员可查看"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')
    user_role = session.get('user_role')

    db_manager = DatabaseManager()
    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM teams WHERE team_id = %s", (team_id,))
        team = cursor.fetchone()

        if not team:
            cursor.close()
            return jsonify({'success': False, 'message': '队伍不存在'}), 404

        event_id = team['event_id']

        is_admin = user_role in ['admin', 'super_admin']
        is_creator = team.get('created_by') == current_user_id

        if not (is_admin or is_creator):
            cursor.execute(
                "SELECT 1 FROM team_players WHERE team_id = %s AND event_id = %s AND user_id = %s LIMIT 1",
                (team_id, event_id, current_user_id),
            )
            membership = cursor.fetchone()

            if not membership:
                cursor.execute(
                    "SELECT 1 FROM team_staff WHERE team_id = %s AND event_id = %s AND user_id = %s LIMIT 1",
                    (team_id, event_id, current_user_id),
                )
                membership = cursor.fetchone()

            if not membership:
                cursor.close()
                return jsonify({'success': False, 'message': '您没有权限查看此队伍的选手信息'}), 403

        cursor.execute(
            """
            SELECT 
                tp.player_id,
                tp.event_id,
                tp.team_id,
                tp.user_id,
                tp.name,
                tp.gender,
                tp.age,
                tp.phone,
                tp.id_card,
                tp.competition_event,
                tp.selected_events,
                tp.level,
                tp.registration_number,
                tp.pair_partner_name,
                tp.pair_registered,
                tp.team_registered,
                tp.status,
                tp.created_at,
                tp.updated_at,
                u.real_name AS user_real_name,
                u.username AS username,
                u.phone AS user_phone,
                u.email AS user_email,
                t.team_name
            FROM team_players tp
            LEFT JOIN users u ON tp.user_id = u.user_id
            LEFT JOIN teams t ON tp.team_id = t.team_id
            WHERE tp.team_id = %s AND tp.event_id = %s
            ORDER BY tp.player_id ASC
            """,
            (team_id, event_id),
        )

        rows = cursor.fetchall()
        cursor.close()

    players = []
    for p in rows:
        raw_selected = p.get('selected_events')
        parsed_selected = None
        if raw_selected:
            try:
                # 数据库存的是 JSON 字符串，这里反序列化为列表，便于前端直接使用
                parsed = json.loads(raw_selected)
                if isinstance(parsed, list):
                    parsed_selected = parsed
            except Exception:
                parsed_selected = None

        players.append({
            'player_id': p['player_id'],
            'event_id': p['event_id'],
            'team_id': p['team_id'],
            'team_name': p.get('team_name'),
            'user_id': p['user_id'],
            'name': p['name'] or p.get('user_real_name'),
            'gender': p.get('gender'),
            'age': p.get('age'),
            'phone': p.get('phone') or p.get('user_phone'),
            'id_card': p.get('id_card'),
            'competition_event': p.get('competition_event'),
            'selected_events': parsed_selected,
            'level': p.get('level'),
            'registration_number': p.get('registration_number'),
            'pair_partner_name': p.get('pair_partner_name'),
            'pair_registered': bool(p.get('pair_registered')),
            'team_registered': bool(p.get('team_registered')),
            'status': p.get('status'),
            'created_at': p['created_at'].isoformat() if p.get('created_at') else None,
            'updated_at': p['updated_at'].isoformat() if p.get('updated_at') else None,
        })

    return jsonify({
        'success': True,
        'team_id': team_id,
        'event_id': event_id,
        'data': players,
        'players': players,
    })
