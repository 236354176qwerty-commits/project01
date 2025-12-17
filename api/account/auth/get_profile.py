from flask import jsonify, session

from utils.decorators import log_action, handle_db_errors

from . import auth_bp, db_manager, logger


@auth_bp.route('/profile', methods=['GET'])
@log_action('获取用户信息')
@handle_db_errors
def get_profile():
    """获取当前用户信息"""
    if not session.get('logged_in'):
        return jsonify({
            'success': False,
            'message': '请先登录'
        }), 401
    
    try:
        user_id = session.get('user_id')
        user = db_manager.get_user_by_id(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '获取用户信息失败'
        }), 500
