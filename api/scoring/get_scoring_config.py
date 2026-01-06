from flask import jsonify, current_app

from utils.decorators import login_required, log_action

from . import scoring_bp, logger


@scoring_bp.route('/config', methods=['GET'])
@login_required
@log_action('获取评分配置')
def get_scoring_config():
    """获取评分配置"""
    try:
        scoring_config = current_app.config.get('SCORING_CONFIG', {})

        return jsonify({
            'success': True,
            'data': scoring_config,
            'config': scoring_config,
        })

    except Exception as e:
        logger.error(f"获取评分配置失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '获取评分配置失败'
        }), 500
