from flask import jsonify

from utils.decorators import login_required, log_action, handle_db_errors

from . import events_bp, db_manager, logger


@events_bp.route('/<int:event_id>', methods=['GET'])
@login_required
@log_action('获取赛事详情')
@handle_db_errors
def get_event(event_id):
    """获取赛事详情"""
    event = db_manager.get_event_by_id(event_id)

    if not event:
        return jsonify({
            'success': False,
            'message': '赛事不存在'
        }), 404

    event_dict = event.to_dict()

    # 获取参赛者信息
    participants = db_manager.get_participants_by_event(event_id)
    event_dict['participants'] = [p.to_dict() for p in participants]
    event_dict['participant_count'] = len(participants)

    return jsonify({
        'success': True,
        'data': event_dict,
        'event': event_dict
    })
