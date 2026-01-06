from flask import jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import teams_bp


@teams_bp.route('/team/<int:team_id>/staff', methods=['GET'])
@log_action('获取队伍随行人员列表')
@handle_db_errors
def api_get_team_staff(team_id):
    """获取指定队伍的随行人员列表 - 领队、队员、随行人员和管理员可查看"""
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
                return jsonify({'success': False, 'message': '您没有权限查看此队伍的随行人员信息'}), 403

        cursor.execute(
            """
            SELECT 
                ts.staff_id,
                ts.event_id,
                ts.team_id,
                ts.user_id,
                ts.name,
                ts.gender,
                ts.age,
                ts.position,
                ts.phone,
                ts.id_card,
                ts.status,
                ts.source,
                ts.created_at,
                ts.updated_at,
                u.real_name AS user_real_name,
                u.username AS username,
                u.phone AS user_phone,
                u.email AS user_email,
                t.team_name AS team_name
            FROM team_staff ts
            LEFT JOIN users u ON ts.user_id = u.user_id
            LEFT JOIN teams t ON ts.team_id = t.team_id
            WHERE ts.team_id = %s AND ts.event_id = %s AND ts.status = 'active'
            ORDER BY ts.staff_id ASC
            """,
            (team_id, event_id),
        )

        rows = cursor.fetchall()
        cursor.close()

    staff_list = []
    for s in rows:
        staff_list.append({
            'staff_id': s['staff_id'],
            'event_id': s['event_id'],
            'team_id': s['team_id'],
            'team_name': s.get('team_name'),
            'user_id': s['user_id'],
            'name': s['name'] or s.get('user_real_name'),
            'gender': s.get('gender'),
            'age': s.get('age'),
            'position': s.get('position'),
            'phone': s.get('phone') or s.get('user_phone'),
            'id_card': s.get('id_card'),
            'status': s.get('status'),
            'source': s.get('source'),
            'created_at': s['created_at'].isoformat() if s.get('created_at') else None,
            'updated_at': s['updated_at'].isoformat() if s.get('updated_at') else None,
        })

    return jsonify({
        'success': True,
        'team_id': team_id,
        'event_id': event_id,
        'data': staff_list,
        'staff': staff_list,
    })
