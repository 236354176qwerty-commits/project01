from flask import request, jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import dashboard_bp


@dashboard_bp.route('/dashboard/statistics', methods=['GET'])
@log_action('获取仪表盘统计信息')
@handle_db_errors
def api_dashboard_statistics():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    user_id = session.get('user_id')
    db_manager = DatabaseManager()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            '''
            SELECT COUNT(DISTINCT ep.event_id) as my_events_count
            FROM event_participants ep
            WHERE ep.user_id = %s AND ep.role = 'athlete'
            ''',
            (user_id,),
        )
        my_events_result = cursor.fetchone()
        my_events_count = my_events_result['my_events_count'] if my_events_result else 0

        if my_events_count == 0:
            cursor.execute(
                '''
                SELECT COUNT(DISTINCT p.event_id) as my_events_count
                FROM participants p
                WHERE p.user_id = %s
                ''',
                (user_id,),
            )
            my_events_result = cursor.fetchone()
            my_events_count = my_events_result['my_events_count'] if my_events_result else 0

        cursor.execute(
            '''
            SELECT COUNT(*) as my_scores_count
            FROM scores s
            JOIN participants p ON s.participant_id = p.participant_id
            WHERE p.user_id = %s
            ''',
            (user_id,),
        )
        my_scores_result = cursor.fetchone()
        my_scores_count = my_scores_result['my_scores_count'] if my_scores_result else 0

        cursor.execute(
            '''
            SELECT COUNT(*) as unread_count
            FROM user_notifications
            WHERE user_id = %s AND is_read = FALSE
            ''',
            (user_id,),
        )
        unread_result = cursor.fetchone()
        notifications_count = unread_result['unread_count'] if unread_result else 0

    statistics = {
        'my_events': my_events_count,
        'my_scores': my_scores_count,
        'notifications': notifications_count,
    }

    return jsonify({
        'success': True,
        'data': statistics,
        'statistics': statistics,
    })
