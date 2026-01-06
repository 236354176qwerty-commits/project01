from flask import jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import notifications_bp


@notifications_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@log_action('标记通知已读')
@handle_db_errors
def api_mark_notification_read(notification_id):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    user_id = session.get('user_id')
    db_manager = DatabaseManager()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE user_notifications 
            SET is_read = TRUE 
            WHERE notification_id = %s AND user_id = %s
            ''',
            (notification_id, user_id),
        )

        conn.commit()

    return jsonify({
        'success': True,
        'message': '通知已标记为已读',
        'data': {
            'notification_id': notification_id,
        },
    })
