from flask import jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import notifications_bp


@notifications_bp.route('/notifications/sent', methods=['GET'])
@log_action('获取已发送通知列表')
@handle_db_errors
def api_get_sent_notifications():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') != 'super_admin':
        return jsonify({'success': False, 'message': '权限不足，只有超级管理员可以查看已发送通知'}), 403

    sender_id = session.get('user_id')
    db_manager = DatabaseManager()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            '''
            SELECT * FROM notifications 
            WHERE sender_id = %s 
            ORDER BY created_at DESC 
            LIMIT 50
            ''',
            (sender_id,),
        )

        notifications = cursor.fetchall()

    return jsonify({
        'success': True,
        'data': notifications,
        'notifications': notifications,
    })
