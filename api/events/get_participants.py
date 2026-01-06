from flask import jsonify

from utils.decorators import login_required, role_required, log_action, handle_db_errors

from . import events_bp, db_manager, logger


@events_bp.route('/<int:event_id>/participants', methods=['GET'])
@login_required
@role_required(['judge', 'admin', 'super_admin'])
@log_action('获取参赛者列表')
@handle_db_errors
def get_participants(event_id):
    """获取参赛者列表"""
    # 检查赛事是否存在
    event = db_manager.get_event_by_id(event_id)
    if not event:
        return jsonify({
            'success': False,
            'message': '赛事不存在'
        }), 404
    
    participants = db_manager.get_participants_by_event(event_id)
    
    participants_data = []
    for participant in participants:
        participant_dict = participant.to_dict()
        # 添加用户信息
        if hasattr(participant, 'real_name'):
            participant_dict['real_name'] = participant.real_name
        if hasattr(participant, 'username'):
            participant_dict['username'] = participant.username
        participants_data.append(participant_dict)
    
    return jsonify({
        'success': True,
        'participants': participants_data,
        'data': participants_data,
    })
