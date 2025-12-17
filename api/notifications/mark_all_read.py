from flask import jsonify, session

from database import DatabaseManager

from . import notifications_bp


@notifications_bp.route('/notifications/mark-all-read', methods=['POST'])
def api_mark_all_read():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        user_id = session.get('user_id')
        db_manager = DatabaseManager()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                '''
                UPDATE user_notifications 
                SET is_read = TRUE 
                WHERE user_id = %s AND is_read = FALSE
                ''',
                (user_id,),
            )

            conn.commit()

        return jsonify({'success': True, 'message': '所有通知已标记为已读'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'批量标记通知已读失败: {str(e)}'}), 500
