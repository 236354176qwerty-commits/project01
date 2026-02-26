from flask import jsonify, session

from utils.decorators import log_action, handle_db_errors, cache_result

from . import notifications_bp


@notifications_bp.route('/notifications/unread-count', methods=['GET'])
@log_action('获取未读通知数量')
@handle_db_errors
@cache_result(timeout=10)
def api_get_unread_notification_count():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    from utils.notification_service import notification_service

    user_id = session.get('user_id')
    count = notification_service.get_unread_count(user_id)

    return jsonify({
        'success': True,
        'count': count,
        'data': {
            'count': count,
        },
    })
