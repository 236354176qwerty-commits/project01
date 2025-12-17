from flask import request, jsonify, session

from database import DatabaseManager

from . import teams_bp


@teams_bp.route('/teams/<int:event_id>')
def api_get_teams_by_event(event_id):
    """获取指定赛事的队伍列表API

    默认仅返回当前用户创建的队伍（领队视角）。
    当 query 参数 visibility=all 时，返回该赛事下所有 active 队伍（用于队员加入时展示列表）。
    """
    try:
        if not session.get('logged_in'):
            return jsonify({'success': False, 'message': '请先登录', 'teams': []})

        current_user_id = session.get('user_id')
        user_role = session.get('user_role')

        visibility = request.args.get('visibility', 'mine')

        db_manager = DatabaseManager()
        with db_manager.get_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            if visibility == 'all':
                query = """
                SELECT team_id, team_name, leader_name, team_type, status,
                       submitted_for_review, submitted_at, created_by
                FROM teams
                WHERE event_id = %s AND status = 'active'
                ORDER BY team_name
                """
                cursor.execute(query, (event_id,))
            else:
                query = """
                SELECT team_id, team_name, leader_name, team_type, status,
                       submitted_for_review, submitted_at, created_by
                FROM teams
                WHERE event_id = %s AND status = 'active' AND created_by = %s
                ORDER BY team_name
                """
                cursor.execute(query, (event_id, current_user_id))

            teams = cursor.fetchall()
            cursor.close()

        team_list = [
            {
                'id': t['team_id'],
                'name': t['team_name'],
                'leader': t['leader_name'],
                'type': t['team_type'] or '未分类',
                'status': t['status'],
                'submittedForReview': bool(t.get('submitted_for_review')),
                'submittedAt': t['submitted_at'].isoformat() if t.get('submitted_at') else None,
                'canEdit': t['created_by'] == current_user_id,
            }
            for t in teams
        ]

        return jsonify({
            'success': True,
            'teams': team_list,
            'count': len(team_list),
            'user_role': user_role,
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取队伍数据失败: {str(e)}',
            'teams': [],
        })
