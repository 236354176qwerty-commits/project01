from flask import jsonify

from utils.decorators import login_required, role_required, log_action, handle_db_errors

from . import scoring_bp, logger


@scoring_bp.route('/judge/<int:judge_id>/scores', methods=['GET'])
@login_required
@role_required(['admin', 'super_admin'])
@log_action('获取裁判评分记录')
@handle_db_errors
def get_judge_scores(judge_id):
    """获取裁判的评分记录"""
    # 这里应该添加获取裁判评分记录的数据库操作
    # 由于当前的 DatabaseManager 没有相关方法，
    # 这里只是示例代码
    scores = []

    return jsonify({
        'success': True,
        'data': {
            'scores': scores,
            'message': '功能开发中',
        },
        'scores': scores,
        'message': '功能开发中',
    })
