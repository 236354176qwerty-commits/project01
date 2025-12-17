from flask import request, jsonify, session
import json

from database import DatabaseManager

from . import teams_bp


@teams_bp.route('/team_applications/my', methods=['GET'])
def api_get_my_team_applications():
    """获取当前用户的队伍申请列表，可按赛事过滤"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')
    event_id = request.args.get('event_id', type=int)

    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            sql = "SELECT * FROM team_applications WHERE user_id = %s"
            params = [current_user_id]

            if event_id:
                sql += " AND event_id = %s"
                params.append(event_id)

            sql += " AND status IN ('pending', 'approved', 'rejected') ORDER BY submitted_at DESC, application_id DESC"

            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            cursor.close()

        applications = []
        for app in rows:
            selected_events_raw = app.get('selected_events')
            selected_events_parsed = []
            if selected_events_raw:
                if isinstance(selected_events_raw, str):
                    try:
                        parsed = json.loads(selected_events_raw)
                        if isinstance(parsed, list):
                            selected_events_parsed = parsed
                        else:
                            selected_events_parsed = [str(parsed)]
                    except Exception:
                        text = selected_events_raw.strip()
                        if '、' in text:
                            selected_events_parsed = [s.strip() for s in text.split('、') if s.strip()]
                        elif ',' in text:
                            selected_events_parsed = [s.strip() for s in text.split(',') if s.strip()]
                        elif text:
                            selected_events_parsed = [text]
                elif isinstance(selected_events_raw, list):
                    selected_events_parsed = selected_events_raw

            applications.append({
                'id': app['application_id'],
                'teamId': app.get('team_id'),
                'eventId': app.get('event_id'),
                'userId': app.get('user_id'),
                'applicantName': app.get('applicant_name'),
                'applicantPhone': app.get('applicant_phone'),
                'applicantIdCard': app.get('applicant_id_card'),
                'teamName': app.get('team_name'),
                'eventName': app.get('event_name'),
                'status': app.get('status'),
                'type': app.get('type'),
                'role': app.get('role'),
                'position': app.get('position'),
                'selectedEvents': selected_events_parsed,
                'submittedAt': app['submitted_at'].isoformat() if app.get('submitted_at') else None,
                'appliedAt': app['submitted_at'].isoformat() if app.get('submitted_at') else None,
            })

        return jsonify({'success': True, 'applications': applications})

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取队伍申请失败: {str(e)}'}), 500
