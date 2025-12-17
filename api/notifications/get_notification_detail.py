from flask import jsonify, session

from . import notifications_bp


@notifications_bp.route('/notifications/<int:notification_id>/detail', methods=['GET'])
def api_get_notification_detail(notification_id):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
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
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'获取通知详情失败: {str(e)}'}), 500
