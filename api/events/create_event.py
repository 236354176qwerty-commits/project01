from flask import request, jsonify, session

from models import Event, EventStatus
from utils.decorators import login_required, role_required, validate_json, log_action, handle_db_errors
from utils.helpers import parse_datetime

from . import events_bp, db_manager, logger


@events_bp.route('/', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin'])
@validate_json(['name', 'start_date', 'end_date'])
@log_action('创建赛事')
@handle_db_errors
def create_event():
    """创建赛事"""
    data = request.get_json()
    user_id = session.get('user_id')
    
    try:
        try:
            individual_fee = float(data.get('individual_fee') or 0)
            pair_practice_fee = float(data.get('pair_practice_fee') or 0)
            team_competition_fee = float(data.get('team_competition_fee') or 0)
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'message': '赛事费用格式无效'
            }), 400

        # 解析日期
        start_date = parse_datetime(data['start_date'])
        end_date = parse_datetime(data['end_date'])
        registration_start_date = None
        registration_deadline = None
        
        if data.get('registration_start_date'):
            registration_start_date = parse_datetime(data['registration_start_date'])
        
        if data.get('registration_deadline'):
            registration_deadline = parse_datetime(data['registration_deadline'])
        
        if not start_date or not end_date:
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
        status_str = data.get('status', 'draft').lower()
        try:
            status = EventStatus(status_str)
        except ValueError:
            status = EventStatus.DRAFT
        
        # 创建赛事对象
        event = Event(
            name=data['name'].strip(),
            description=data.get('description', '').strip(),
            start_date=start_date,
            end_date=end_date,
            location=data.get('location', '').strip(),
            max_participants=data.get('max_participants', 100),
            registration_start_time=registration_start_date,
            registration_deadline=registration_deadline,
            status=status,
            created_by=user_id,
            contact_phone=data.get('contact_phone', '').strip(),
            organizer=data.get('organizer', '').strip(),
            co_organizer=data.get('co_organizer', '').strip(),
            individual_fee=individual_fee,
            pair_practice_fee=pair_practice_fee,
            team_competition_fee=team_competition_fee
        )
        
        # 保存到数据库
        created_event = db_manager.create_event(event)
        
        logger.info(f"用户 {user_id} 创建赛事: {event.name}")
        
        return jsonify({
            'success': True,
            'message': '赛事创建成功',
            'event': created_event.to_dict()
        })
        
    except Exception as e:
        logger.error(f"创建赛事失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '创建赛事失败，请稍后重试'
        }), 500
