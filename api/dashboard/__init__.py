from flask import Blueprint, request, jsonify, session

from database import DatabaseManager


dashboard_bp = Blueprint('dashboard', __name__)
# 兼容 system_bp 命名，用于系统聚合
system_bp = dashboard_bp


@dashboard_bp.route('/dashboard/statistics', methods=['GET'])
def api_dashboard_statistics():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        user_id = session.get('user_id')
        db_manager = DatabaseManager()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            # 优先基于 event_participants 统计我参与的赛事数量（按 event 维度去重，role='athlete'）
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

            # 如果新表中尚无记录，则回退到旧的 participants 统计
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

        return jsonify({
            'success': True,
            'statistics': {
                'my_events': my_events_count,
                'my_scores': my_scores_count,
                'notifications': notifications_count,
            },
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取仪表盘统计信息失败: {str(e)}',
        }), 500


@dashboard_bp.route('/system/statistics', methods=['GET'])
def api_system_statistics():
    try:
        db_manager = DatabaseManager()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute('SELECT COUNT(*) as total FROM events')
            total_events = cursor.fetchone()['total']

            # 优先基于 event_participants 统计参与赛事的用户数量（按 user_id 去重，role='athlete'）
            cursor.execute("SELECT COUNT(DISTINCT user_id) as total FROM event_participants WHERE role = 'athlete'")
            row = cursor.fetchone()
            total_participants = row['total'] if row else 0

            # 如无新表数据则回退到 participants
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


@dashboard_bp.route('/dashboard/my-schedule', methods=['GET'])
def api_dashboard_my_schedule():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
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
            'schedules': schedules_list,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取个人日程失败: {str(e)}',
        }), 500
