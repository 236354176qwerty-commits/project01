from flask import jsonify, session

from . import notifications_bp


@notifications_bp.route('/notifications/unread-count', methods=['GET'])
def api_get_unread_notification_count():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        from utils.notification_service import notification_service

        user_id = session.get('user_id')
        count = notification_service.get_unread_count(user_id)

        return jsonify({'success': True, 'count': count})

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取未读通知数量失败: {str(e)}'}), 500
