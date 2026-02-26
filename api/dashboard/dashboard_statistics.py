from flask import request, jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors, cache_result

from . import dashboard_bp


@dashboard_bp.route('/dashboard/statistics', methods=['GET'])
@log_action('获取仪表盘统计信息')
@handle_db_errors
@cache_result(timeout=15)
def api_dashboard_statistics():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    user_id = session.get('user_id')
    db_manager = DatabaseManager()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        # 用单条 SQL 一次性获取所有统计数据，减少 DB 往返次数
        cursor.execute(
            '''
            SELECT
                (SELECT COUNT(DISTINCT ep.event_id)
                 FROM event_participants ep
                 WHERE ep.user_id = %s AND ep.role = 'athlete') AS ep_events,
                (SELECT COUNT(DISTINCT p.event_id)
                 FROM participants p
                 WHERE p.user_id = %s) AS p_events,
                (SELECT COUNT(*)
                 FROM scores s
                 JOIN participants p ON s.participant_id = p.participant_id
                 WHERE p.user_id = %s) AS my_scores_count,
                (SELECT COUNT(*)
                 FROM user_notifications
                 WHERE user_id = %s AND is_read = FALSE) AS unread_count
            ''',
            (user_id, user_id, user_id, user_id),
        )
        row = cursor.fetchone()

    ep_events = row['ep_events'] or 0
    p_events = row['p_events'] or 0
    my_events_count = ep_events if ep_events > 0 else p_events

    statistics = {
        'my_events': my_events_count,
        'my_scores': row['my_scores_count'] or 0,
        'notifications': row['unread_count'] or 0,
    }

    return jsonify({
        'success': True,
        'data': statistics,
        'statistics': statistics,
    })
