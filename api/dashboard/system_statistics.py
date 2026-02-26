from flask import jsonify

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors, cache_result

from . import dashboard_bp


@dashboard_bp.route('/system/statistics', methods=['GET'])
@log_action('获取系统统计信息')
@handle_db_errors
@cache_result(timeout=30)
def api_system_statistics():
    db_manager = DatabaseManager()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            '''
            SELECT
                (SELECT COUNT(*) FROM events) AS total_events,
                (SELECT COUNT(DISTINCT user_id) FROM event_participants WHERE role = 'athlete') AS ep_participants,
                (SELECT COUNT(DISTINCT user_id) FROM participants) AS p_participants,
                (SELECT COUNT(*) FROM events WHERE status = 'completed') AS completed_events,
                (SELECT COUNT(*) FROM events WHERE status != 'completed') AS incomplete_events
            '''
        )
        row = cursor.fetchone()

    ep_p = row['ep_participants'] or 0
    p_p = row['p_participants'] or 0

    statistics = {
        'total_events': row['total_events'] or 0,
        'total_participants': ep_p if ep_p > 0 else p_p,
        'incomplete_events': row['incomplete_events'] or 0,
        'completed_events': row['completed_events'] or 0,
    }

    return jsonify({
        'success': True,
        'data': statistics,
        'statistics': statistics,
    })
