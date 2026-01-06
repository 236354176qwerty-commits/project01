from flask import jsonify, session

from utils.decorators import log_action, handle_db_errors

from . import notifications_bp


@notifications_bp.route('/notifications/<int:notification_id>/detail', methods=['GET'])
@log_action('获取通知详情')
@handle_db_errors
def api_get_notification_detail(notification_id):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    from utils.notification_service import notification_service

    user_id = session.get('user_id')

    notification = notification_service.get_notification_detail(notification_id, user_id)

    if not notification:
        return jsonify({'success': False, 'message': '通知不存在或无权访问'}), 404

    if notification.get('created_at'):
        notification['created_at'] = notification['created_at'].isoformat()
    if notification.get('received_at'):
        notification['received_at'] = notification['received_at'].isoformat()

    return jsonify({
        'success': True,
        'notification': notification,
        'data': notification,
    })
