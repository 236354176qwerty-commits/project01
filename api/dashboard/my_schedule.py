from flask import request, jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import dashboard_bp


@dashboard_bp.route('/dashboard/my-schedule', methods=['GET'])
@log_action('获取个人日程')
@handle_db_errors
def api_dashboard_my_schedule():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    user_id = session.get('user_id')
    db_manager = DatabaseManager()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            '''
            SELECT 
                e.event_id,
                e.name AS event_name,
                e.start_date AS event_time,
                e.location,
                COALESCE(ei.name, p.category) AS project,
                p.status AS participant_status,
                e.status AS event_status
            FROM participants p
            JOIN events e ON p.event_id = e.event_id
            LEFT JOIN entries en ON en.registration_number = p.registration_number
            LEFT JOIN event_items ei ON en.event_item_id = ei.event_item_id
            WHERE p.user_id = %s
            ORDER BY e.start_date DESC
            LIMIT 10
            ''',
            (user_id,),
        )

        schedules = cursor.fetchall()

    schedules_list = []
    for schedule in schedules:
        event_time = schedule.get('event_time')
        if hasattr(event_time, 'isoformat'):
            event_time_str = event_time.isoformat()
        elif isinstance(event_time, str):
            event_time_str = event_time
        else:
            event_time_str = None

        status = schedule.get('participant_status') or schedule.get('event_status') or 'unknown'

        schedules_list.append({
            'id': schedule.get('event_id'),
            'name': schedule.get('event_name'),
            'event_time': event_time_str,
            'location': schedule.get('location') or '未提供地点',
            'project': schedule.get('project') or '未指定项目',
            'status': status,
        })

    return jsonify({
        'success': True,
        'data': schedules_list,
        'schedules': schedules_list,
    })
