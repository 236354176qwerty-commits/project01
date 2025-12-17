from datetime import datetime

from flask import request, jsonify, session

from models import Participant, ParticipantStatus, EventStatus
from utils.decorators import login_required, validate_json, log_action, handle_db_errors
from utils.helpers import generate_registration_number
from utils.notification_service import notification_service

from . import events_bp, db_manager, logger


@events_bp.route('/<int:event_id>/register', methods=['POST'])
@login_required
@validate_json(['category'])
@log_action('报名参赛')
@handle_db_errors
def register_event(event_id):
    """报名参赛"""
    data = request.get_json()
    user_id = session.get('user_id')
    
    try:
        # 检查赛事是否存在
        event = db_manager.get_event_by_id(event_id)
        if not event:
            return jsonify({
                'success': False,
                'message': '赛事不存在'
            }), 404
        
        # 检查赛事状态
        if event.status != EventStatus.PUBLISHED:
            return jsonify({
                'success': False,
                'message': '该赛事暂不接受报名'
            }), 400
        
        # 检查报名截止时间
        if event.registration_deadline and datetime.now() > event.registration_deadline:
            return jsonify({
                'success': False,
                'message': '报名时间已截止'
            }), 400
        
        # 检查是否已经报名
        participants = db_manager.get_participants_by_event(event_id)
        for participant in participants:
            if participant.user_id == user_id:
                return jsonify({
                    'success': False,
                    'message': '您已经报名了该赛事'
                }), 400
        
        # 检查参赛人数限制
        if event.max_participants and len(participants) >= event.max_participants:
            return jsonify({
                'success': False,
                'message': '该赛事报名人数已满'
            }), 400
        
        # 生成参赛编号
        registration_number = generate_registration_number(event_id, len(participants) + 1)
        
        # 创建参赛者
        participant = Participant(
            event_id=event_id,
            user_id=user_id,
            registration_number=registration_number,
            category=data['category'].strip(),
            weight_class=data.get('weight_class', '').strip(),
            status=ParticipantStatus.REGISTERED,
            notes=data.get('notes', '').strip()
        )
        
        # 保存到数据库
        created_participant = db_manager.create_participant(participant)

        logger.info(f"用户 {user_id} 报名参赛: {event.name}")

        # 尝试写入新结构 entries / entry_members（不影响主流程）
        try:
            item_name = created_participant.category or data['category'].strip()
            db_manager.create_individual_entry_for_user(
                event_id=event_id,
                item_name=item_name,
                registration_number=created_participant.registration_number,
                user_id=user_id,
                team_id=None,
                created_by=user_id,
                status=ParticipantStatus.REGISTERED.value,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"同步写入 entries/entry_members 失败（不影响主流程）: {e}")

        # 发送报名成功通知（异步，不影响主流程）
        try:
            participant_info = {
                'participant_id': created_participant.participant_id,
                'category': created_participant.category,
                'registration_number': created_participant.registration_number
            }
            notification_service.send_registration_success_notification(
                user_id=user_id,
                event_id=event_id,
                participant_info=participant_info
            )
            logger.info(f"报名成功通知已发送给用户 {user_id}")
        except Exception as e:
            logger.error(f"发送报名成功通知失败，但不影响报名流程: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': '报名成功',
            'participant': created_participant.to_dict()
        })
        
    except Exception as e:
        logger.error(f"报名失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '报名失败，请稍后重试'
        }), 500
