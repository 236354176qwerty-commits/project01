from flask import jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import teams_bp


@teams_bp.route('/events/<int:event_id>/my-team', methods=['GET'])
@log_action('获取我在赛事中的队伍')
@handle_db_errors
def api_get_my_team_for_event(event_id):
    """获取当前用户在指定赛事中所属的队伍（作为队员或随行人员）"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')

    db_manager = DatabaseManager()
    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT t.*, e.name AS event_name
            FROM teams t
            LEFT JOIN events e ON t.event_id = e.event_id
            WHERE t.event_id = %s
              AND t.status = 'active'
              AND (
                EXISTS (
                    SELECT 1 FROM team_players p
                    WHERE p.team_id = t.team_id
                      AND p.event_id = t.event_id
                      AND p.user_id = %s
                )
                OR EXISTS (
                    SELECT 1 FROM team_staff s
                    WHERE s.team_id = t.team_id
                      AND s.event_id = t.event_id
                      AND s.user_id = %s
                )
              )
            ORDER BY t.team_id ASC
            LIMIT 1
            """,
            (event_id, current_user_id, current_user_id),
        )

        team = cursor.fetchone()
        cursor.close()

    if not team:
        return jsonify({'success': True, 'data': None, 'team': None})

    team_data = {
        'id': team['team_id'],
        'name': team['team_name'],
        'event_id': team['event_id'],
        'event_name': team.get('event_name'),
        'type': team.get('team_type'),
        'leader_id': team.get('leader_id'),
        'leader_name': team.get('leader_name'),
        'leader_position': team.get('leader_position'),
        'leader_phone': team.get('leader_phone'),
        'leader_email': team.get('leader_email'),
        'address': team.get('team_address'),
        'description': team.get('team_description'),
        'status': team.get('status'),
        'submitted_for_review': bool(team.get('submitted_for_review')),
        'submitted_at': team['submitted_at'].isoformat() if team.get('submitted_at') else None,
        'created_by': team.get('created_by'),
        'created_at': team['created_at'].isoformat() if team.get('created_at') else None,
        'canEdit': team.get('created_by') == current_user_id,
    }

    return jsonify({
        'success': True,
        'data': team_data,
        'team': team_data,
    })
