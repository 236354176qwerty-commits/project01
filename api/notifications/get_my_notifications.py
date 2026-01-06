from flask import request, jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import notifications_bp


@notifications_bp.route('/notifications/my', methods=['GET'])
@log_action('获取我的通知列表')
@handle_db_errors
def api_get_my_notifications():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    user_id = session.get('user_id')
    db_manager = DatabaseManager()

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 5, type=int)

    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 5

    offset = (page - 1) * page_size

    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            '''
            SELECT COUNT(*) as total
            FROM user_notifications un
            WHERE un.user_id = %s
            ''',
            (user_id,),
        )
        total_result = cursor.fetchone()
        total = total_result['total'] if total_result else 0

        cursor.execute(
            '''
            SELECT 
                n.id,
                n.title,
                n.content,
                n.priority,
                n.sender_type,
                n.sender_id,
                n.recipient_type,
                n.additional_info,
                n.created_at,
                un.is_read,
                un.created_at as received_at
            FROM user_notifications un
            JOIN notifications n ON un.notification_id = n.id
            WHERE un.user_id = %s
            ORDER BY n.created_at DESC
            LIMIT %s OFFSET %s
            ''',
            (user_id, page_size, offset),
        )

        notifications = cursor.fetchall()

    for notif in notifications:
        if notif.get('created_at'):
            notif['created_at'] = notif['created_at'].isoformat()
        if notif.get('received_at'):
            notif['received_at'] = notif['received_at'].isoformat()

    total_pages = (total + page_size - 1) // page_size if page_size else 0

    return jsonify({
        'success': True,
        'data': notifications,
        'notifications': notifications,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': total_pages,
        },
    })
