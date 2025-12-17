from flask import jsonify, session

from models import EventStatus
from utils.decorators import login_required, role_required, log_action, handle_db_errors

from . import events_bp, db_manager, logger


@events_bp.route('/<int:event_id>', methods=['DELETE'])
@login_required
@role_required(['admin', 'super_admin'])
@log_action('删除赛事')
@handle_db_errors
def delete_event(event_id):
    """删除赛事"""
    try:
        user_id = session.get('user_id')
        
        # 检查赛事是否存在
        event = db_manager.get_event_by_id(event_id)
        if not event:
            return jsonify({
                'success': False,
                'message': '赛事不存在'
            }), 404
        
        # 检查是否有参赛者
        participants = db_manager.get_event_participants(event_id)
        if participants:
            return jsonify({
                'success': False,
                'message': f'无法删除赛事，已有 {len(participants)} 名参赛者报名。请先处理参赛者数据。'
            }), 400
        
        # 检查赛事状态
        if event.status in [EventStatus.ONGOING, EventStatus.COMPLETED]:
            return jsonify({
                'success': False,
                'message': '无法删除进行中或已完成的赛事'
            }), 400
        
        # 执行删除
        success = db_manager.delete_event(event_id)
        
        if success:
            logger.info(f"用户 {user_id} 删除了赛事 {event_id}: {event.name}")
            return jsonify({
                'success': True,
                'message': '赛事删除成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '删除赛事失败'
            }), 500
            
    except Exception as e:
        logger.error(f"删除赛事失败: {e}")
        return jsonify({
            'success': False,
            'message': '删除赛事失败'
        }), 500
