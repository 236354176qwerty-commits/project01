from flask import jsonify, session

from database import DatabaseManager

from . import teams_bp


@teams_bp.route('/teams/my', methods=['GET'])
def api_get_my_created_teams():
    """获取当前用户创建的所有队伍列表（跨所有赛事，用于“我创建的队伍”页面）"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')

    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT t.team_id, t.event_id, e.name AS event_name,
                       t.team_name, t.team_type, t.team_address, t.team_description,
                       t.leader_name, t.leader_position, t.leader_phone, t.leader_email,
                       t.status, t.submitted_for_review, t.submitted_at,
                       t.created_at, t.updated_at
                FROM teams t
                LEFT JOIN events e ON t.event_id = e.event_id
                WHERE t.created_by = %s AND t.status = 'active'
                ORDER BY t.created_at DESC, t.team_id DESC
                """,
                (current_user_id,),
            )
            rows = cursor.fetchall()
            cursor.close()

        teams = []
        for row in rows:
            teams.append({
                'id': row['team_id'],
                'eventId': row['event_id'],
                'eventName': row.get('event_name'),
                'teamName': row.get('team_name'),
                'teamType': row.get('team_type'),
                'teamAddress': row.get('team_address'),
                'teamDescription': row.get('team_description'),
                'leaderName': row.get('leader_name'),
                'leaderPosition': row.get('leader_position'),
                'leaderPhone': row.get('leader_phone'),
                'leaderEmail': row.get('leader_email'),
                'status': row.get('status'),
                'submittedForReview': bool(row.get('submitted_for_review')),
                'submittedAt': row['submitted_at'].isoformat() if row.get('submitted_at') else None,
                'createdAt': row['created_at'].isoformat() if row.get('created_at') else None,
                'updatedAt': row['updated_at'].isoformat() if row.get('updated_at') else None,
            })

        return jsonify({'success': True, 'teams': teams})

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取我创建的队伍失败: {str(e)}'}), 500
