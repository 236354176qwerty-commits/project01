from flask import jsonify, session
from datetime import datetime

from database import DatabaseManager

from . import teams_bp


@teams_bp.route('/team_applications/<int:application_id>/cancel', methods=['POST'])
def api_cancel_team_application(application_id):
    """取消当前用户的一条队伍申请"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')

    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM team_applications WHERE application_id = %s", (application_id,))
            app_row = cursor.fetchone()
            if not app_row:
                cursor.close()
                return jsonify({'success': False, 'message': '申请不存在'}), 404

            if app_row.get('user_id') != current_user_id:
                cursor.close()
                return jsonify({'success': False, 'message': '您没有权限取消此申请'}), 403

            if app_row.get('status') not in ['pending', 'approved']:
                cursor.close()
                return jsonify({'success': False, 'message': '只有待审核或已通过的申请可以取消'}), 400

            now = datetime.now()
            cursor.execute(
                "UPDATE team_applications SET status = 'cancelled', updated_at = %s WHERE application_id = %s",
                (now, application_id),
            )
            conn.commit()
            cursor.close()

        return jsonify({'success': True, 'message': '申请已取消'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'取消申请失败: {str(e)}'}), 500
