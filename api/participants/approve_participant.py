from flask import jsonify, session

from database import DatabaseManager
from utils.notification_service import notification_service
from utils.decorators import log_action, handle_db_errors

from . import participants_bp


@participants_bp.route('/participants/<int:participant_id>/approve', methods=['POST'])
@log_action('审批参赛信息')
@handle_db_errors
def api_approve_participant(participant_id):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    user_role = session.get('user_role')
    if user_role not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以审批参赛信息'}), 403
    
    db_manager = DatabaseManager()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
            SELECT 
                p.*,
                e.name AS event_name,
                u.user_id AS user_id,
                u.real_name,
                t.team_name,
                t.leader_name,
                c.category_name
            FROM participants p
            JOIN events e ON p.event_id = e.event_id
            JOIN users u ON p.user_id = u.user_id
            LEFT JOIN teams t ON p.team_id = t.team_id
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE p.participant_id = %s
        ''', (participant_id,))

        participant = cursor.fetchone()

        if not participant:
            return jsonify({'success': False, 'message': '未找到对应的参赛记录'}), 404

        db_manager.set_participant_review_status_with_conn(
            conn,
            participant_id,
            'approved',
        )

        conn.commit()

    participant_info = {
        'participant_id': participant['participant_id'],
        'team_name': participant.get('team_name'),
        'leader_name': participant.get('leader_name'),
        'category': participant.get('category_name'),
        'registration_number': participant.get('registration_number'),
        'contact_phone': None,
        'contact_email': None,
    }

    success = notification_service.send_final_confirmation_notification(
        user_id=participant['user_id'],
        event_id=participant['event_id'],
        participant_info=participant_info,
    )

    if success:
        message = '审核通过并已发送确认通知'
    else:
        message = '审核通过，但发送确认通知失败，请稍后在通知中心查看'

    return jsonify({
        'success': True,
        'message': message,
        'data': participant_info,
    })
