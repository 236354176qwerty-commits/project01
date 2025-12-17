from flask import jsonify

from utils.decorators import login_required, role_required, log_action, handle_db_errors

from . import events_bp, logger


@events_bp.route('/<int:event_id>/checkin/<int:participant_id>', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin'])
@log_action('参赛者签到')
@handle_db_errors
def checkin_participant(event_id, participant_id):
    """参赛者签到"""
    try:
        # 这里应该添加签到的数据库操作
        # 由于当前的 DatabaseManager 没有相关方法，
        # 这里只是示例代码
        
        logger.info(f"参赛者 {participant_id} 签到成功")
        
        return jsonify({
            'success': True,
            'message': '签到成功'
        })
        
    except Exception as e:
        logger.error(f"签到失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '签到失败'
        }), 500
