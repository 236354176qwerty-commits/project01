from flask import jsonify, session

from database import DatabaseManager

from . import teams_bp


@teams_bp.route('/team/<int:team_id>')
def api_get_team_details(team_id):
    """获取队伍详细信息API - 只有创建者或管理员可以查看"""
    try:
        if not session.get('logged_in'):
            return jsonify({
                'success': False,
                'message': '请先登录'
            })

        current_user_id = session.get('user_id')
        user_role = session.get('user_role')

        db_manager = DatabaseManager()
        with db_manager.get_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            query = """
            SELECT t.*, e.name as event_name
            FROM teams t
            LEFT JOIN events e ON t.event_id = e.event_id
            WHERE t.team_id = %s
            """

            cursor.execute(query, (team_id,))
            team = cursor.fetchone()

            if not team:
                cursor.close()
                return jsonify({
                    'success': False,
                    'message': '队伍不存在'
                })

            if user_role not in ['admin', 'super_admin'] and team['created_by'] != current_user_id:
                cursor.close()
                return jsonify({
                    'success': False,
                    'message': '您没有权限查看此队伍信息'
                })

            cursor.close()

        return jsonify({
            'success': True,
            'team': {
                'id': team['team_id'],
                'name': team['team_name'],
                'event_id': team['event_id'],
                'event_name': team['event_name'],
                'type': team['team_type'],
                'leader_id': team['leader_id'],
                'leader_name': team['leader_name'],
                'leader_position': team['leader_position'],
                'leader_phone': team['leader_phone'],
                'leader_email': team['leader_email'],
                'address': team['team_address'],
                'description': team['team_description'],
                'status': team['status'],
                'submitted_for_review': bool(team.get('submitted_for_review')),
                'submitted_at': team['submitted_at'].isoformat() if team.get('submitted_at') else None,
                'created_by': team['created_by'],
                'created_at': team['created_at'].isoformat() if team['created_at'] else None,
                'canEdit': team['created_by'] == current_user_id,
            },
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取队伍信息失败: {str(e)}'
        })
