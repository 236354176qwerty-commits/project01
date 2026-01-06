from flask import jsonify, session
import json

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import teams_bp


@teams_bp.route('/team/<int:team_id>/applications', methods=['GET'])
@log_action('获取队伍申请列表')
@handle_db_errors
def api_get_team_applications(team_id):
    """获取指定队伍的申请列表（队长/管理员使用）"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')
    user_role = session.get('user_role')

    db_manager = DatabaseManager()
    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM teams WHERE team_id = %s", (team_id,))
        team = cursor.fetchone()

        if not team:
            cursor.close()
            return jsonify({'success': False, 'message': '队伍不存在'}), 404

        is_admin = user_role in ['admin', 'super_admin']
        is_creator = team.get('created_by') == current_user_id
        if not (is_admin or is_creator):
            cursor.close()
            return jsonify({'success': False, 'message': '您没有权限查看该队伍的申请信息'}), 403

        cursor.execute(
            """
            SELECT ta.*, e.name AS event_name
            FROM team_applications ta
            LEFT JOIN events e ON ta.event_id = e.event_id
            WHERE ta.team_id = %s
              AND ta.status IN ('pending', 'approved', 'rejected')
            ORDER BY ta.submitted_at DESC, ta.application_id DESC
            """,
            (team_id,),
        )
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

    return jsonify({
        'success': True,
        'data': applications,
        'applications': applications,
    })
