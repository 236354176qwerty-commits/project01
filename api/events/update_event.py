from flask import request, jsonify

from models import Event, EventStatus
from utils.decorators import login_required, role_required, validate_json, log_action, handle_db_errors
from utils.helpers import parse_datetime

from . import events_bp, db_manager, logger


@events_bp.route('/<int:event_id>', methods=['PUT'])
@login_required
@role_required(['admin', 'super_admin'])
@validate_json(['name', 'start_date', 'end_date'])
@log_action('更新赛事')
@handle_db_errors
def update_event(event_id):
    """更新赛事"""
    data = request.get_json()
    
    try:
        individual_fee = float(data.get('individual_fee') or 0)
        pair_practice_fee = float(data.get('pair_practice_fee') or 0)
        team_competition_fee = float(data.get('team_competition_fee') or 0)
    except (TypeError, ValueError):
        return jsonify({
            'success': False,
            'message': '赛事费用格式无效'
        }), 400

    # 检查赛事是否存在
    existing_event = db_manager.get_event_by_id(event_id)
    if not existing_event:
        return jsonify({
            'success': False,
            'message': '赛事不存在'
        }), 404
    
    # 解析日期
    try:
        start_date = parse_datetime(data['start_date'])
        end_date = parse_datetime(data['end_date'])
        registration_start_date = parse_datetime(data.get('registration_start_date')) if data.get('registration_start_date') else None
        registration_deadline = parse_datetime(data.get('registration_deadline')) if data.get('registration_deadline') else None
    except ValueError:
        return jsonify({
            'success': False,
            'message': '日期格式不正确，请使用ISO格式，如: 2024-06-01T10:00:00 或 2024-06-01 10:00:00'
        }), 400
    
    if start_date >= end_date:
        return jsonify({
            'success': False,
            'message': '开始时间必须早于结束时间'
        }), 400
    
    # 处理状态
    status_str = data.get('status', existing_event.status.value).lower()
    try:
        status = EventStatus(status_str)
    except ValueError:
        status = existing_event.status
    
    # 创建更新的赛事对象
    updated_event = Event(
        event_id=event_id,
        name=data['name'].strip(),
        description=data.get('description', '').strip(),
        start_date=start_date,
        end_date=end_date,
        location=data.get('location', '').strip(),
        max_participants=data.get('max_participants', 100),
        registration_start_time=registration_start_date,
        registration_deadline=registration_deadline,
        status=status,
        created_by=existing_event.created_by,
        contact_phone=data.get('contact_phone', '').strip(),
        organizer=data.get('organizer', '').strip(),
        co_organizer=data.get('co_organizer', '').strip(),
        individual_fee=individual_fee,
        pair_practice_fee=pair_practice_fee,
        team_competition_fee=team_competition_fee
    )
    
    # 更新到数据库
    result_event = db_manager.update_event(event_id, updated_event)
    
    if result_event:
        logger.info(f"赛事 {event_id} 更新成功")
        event_dict = result_event.to_dict()
        return jsonify({
            'success': True,
            'message': '赛事更新成功',
            'event': event_dict,
            'data': event_dict,
        })
    else:
        return jsonify({
            'success': False,
            'message': '更新失败'
        }), 500
