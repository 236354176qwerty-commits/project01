from flask import jsonify

from database import DatabaseManager

from . import dashboard_bp


@dashboard_bp.route('/system/statistics', methods=['GET'])
def api_system_statistics():
    try:
        db_manager = DatabaseManager()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute('SELECT COUNT(*) as total FROM events')
            total_events = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(DISTINCT user_id) as total FROM event_participants WHERE role = 'athlete'")
            row = cursor.fetchone()
            total_participants = row['total'] if row else 0

            if total_participants == 0:
                cursor.execute('SELECT COUNT(DISTINCT user_id) as total FROM participants')
                row = cursor.fetchone()
                total_participants = row['total'] if row else 0

            cursor.execute("SELECT COUNT(*) as total FROM events WHERE status = 'completed'")
            completed_events = cursor.fetchone()['total']
            cursor.execute("SELECT COUNT(*) as total FROM events WHERE status != 'completed'")
            incomplete_events = cursor.fetchone()['total']

            return jsonify({
                'success': True,
                'statistics': {
                    'total_events': total_events,
                    'total_participants': total_participants,
                    'incomplete_events': incomplete_events,
                    'completed_events': completed_events,
                },
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取系统统计信息失败: {str(e)}',
            'statistics': {
                'total_events': 0,
                'total_participants': 0,
                'incomplete_events': 0,
                'completed_events': 0,
            },
        }), 500
