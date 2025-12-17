from flask import jsonify, session

from database import DatabaseManager

from . import teams_bp


@teams_bp.route('/team/<int:team_id>/staff/<int:staff_id>', methods=['DELETE'])
def api_delete_team_staff(team_id, staff_id):
    """删除指定队伍的随行人员 - 只有领队或管理员可以删除"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')
    user_role = session.get('user_role')

    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM teams WHERE team_id = %s", (team_id,))
            team = cursor.fetchone()

            if not team:
                cursor.close()
                return jsonify({'success': False, 'message': '队伍不存在'}), 404

            is_admin = user_role in ['admin', 'super_admin']
            is_creator = team.get('created_by') == current_user_id

            if not (is_admin or is_creator):
                cursor.close()
                return jsonify({'success': False, 'message': '您没有权限删除此队伍的随行人员'}), 403

            cursor.execute(
                "SELECT * FROM team_staff WHERE team_id = %s AND staff_id = %s",
                (team_id, staff_id),
            )
            staff = cursor.fetchone()

            if not staff:
                cursor.close()
                return jsonify({'success': False, 'message': '随行人员不存在'}), 404

            cursor.execute(
                "DELETE FROM team_staff WHERE team_id = %s AND staff_id = %s",
                (team_id, staff_id),
            )
            conn.commit()
            cursor.close()

        return jsonify({
            'success': True,
            'message': '随行人员删除成功',
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'删除随行人员失败: {str(e)}'}), 500
