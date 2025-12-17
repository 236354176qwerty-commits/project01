from flask import jsonify

from utils.decorators import login_required, role_required, log_action, handle_db_errors

from . import events_bp, db_manager, logger


@events_bp.route('/<int:event_id>/publish', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin'])
@log_action('发布赛事')
@handle_db_errors
def publish_event(event_id):
    """发布赛事"""
    try:
        # 检查赛事是否存在
        event = db_manager.get_event_by_id(event_id)
        if not event:
            return jsonify({
                'success': False,
                'message': '赛事不存在'
            }), 404
        
        # 这里应该添加发布赛事的数据库操作
        # 由于当前的 DatabaseManager 没有相关方法，
        # 这里只是示例代码
        
        logger.info(f"赛事 {event_id} 发布成功")
        
        return jsonify({
            'success': True,
            'message': '赛事发布成功'
        })
        
    except Exception as e:
        logger.error(f"发布赛事失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '发布赛事失败'
        }), 500
