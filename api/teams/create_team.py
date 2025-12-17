from flask import request, jsonify, session
from datetime import datetime

from database import DatabaseManager

from . import teams_bp


@teams_bp.route('/teams', methods=['POST'])
def api_create_team():
    """创建队伍（领队在赛事中创建自己的队伍）"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    data = request.get_json() or {}

    event_id = data.get('event_id') or data.get('eventId')
    team_name = (data.get('team_name') or data.get('teamName') or '').strip()
    team_type = data.get('team_type') or data.get('teamType') or None
    team_address = (data.get('team_address') or data.get('teamAddress') or '').strip() or None
    team_description = (data.get('team_description') or data.get('teamDescription') or '').strip() or None
    leader_name = (data.get('leader_name') or data.get('leaderName') or '').strip()
    leader_position = (data.get('leader_position') or data.get('leaderPosition') or '领队').strip()
    leader_phone = (data.get('leader_phone') or data.get('leaderPhone') or '').strip()
    leader_email = (data.get('leader_email') or data.get('leaderEmail') or '').strip() or None

    if not event_id or not team_name or not leader_name or not leader_phone:
        return jsonify({
            'success': False,
            'message': 'event_id、队伍名称、负责人姓名和联系电话为必填项'
        }), 400

    current_user_id = session.get('user_id')

    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT event_id, name FROM events WHERE event_id = %s", (event_id,))
            event = cursor.fetchone()
            if not event:
                cursor.close()
                return jsonify({'success': False, 'message': '赛事不存在'}), 404

            cursor.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM teams
                WHERE event_id = %s AND created_by = %s AND status != 'deleted'
                """,
                (event_id, current_user_id),
            )
            row = cursor.fetchone() or {}
            if row.get('cnt', 0) > 0:
                cursor.close()
                return jsonify({'success': False, 'message': '您已经在该赛事中创建过队伍了'}), 400

            now = datetime.now()

            cursor.execute(
                """
                INSERT INTO teams (
                    event_id, team_name, team_type, team_address, team_description,
                    leader_id, leader_name, leader_position, leader_phone, leader_email,
                    status, submitted_for_review, submitted_at,
                    client_team_key, created_by, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    team_name,
                    team_type,
                    team_address,
                    team_description,
                    current_user_id,
                    leader_name,
                    leader_position,
                    leader_phone,
                    leader_email,
                    'active',
                    0,
                    None,
                    None,
                    current_user_id,
                    now,
                    now,
                ),
            )
            team_id = cursor.lastrowid
            conn.commit()
            cursor.close()

        return jsonify({
            'success': True,
            'team': {
                'id': team_id,
                'event_id': int(event_id),
                'event_name': event.get('name'),
                'name': team_name,
                'team_name': team_name,
                'team_type': team_type,
                'address': team_address,
                'description': team_description,
                'leader_id': current_user_id,
                'leader_name': leader_name,
                'leader_position': leader_position,
                'leader_phone': leader_phone,
                'leader_email': leader_email,
                'status': 'active',
                'created_by': current_user_id,
                'created_at': now.isoformat(),
                'canEdit': True,
            },
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'创建队伍失败: {str(e)}'}), 500
