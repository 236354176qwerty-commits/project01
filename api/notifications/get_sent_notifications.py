from flask import jsonify, session

from database import DatabaseManager

from . import notifications_bp


@notifications_bp.route('/notifications/sent', methods=['GET'])
def api_get_sent_notifications():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') != 'super_admin':
        return jsonify({'success': False, 'message': '权限不足，只有超级管理员可以查看已发送通知'}), 403

    try:
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
                'notifications': notifications,
            })

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取已发送通知失败: {str(e)}'}), 500
