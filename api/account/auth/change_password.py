from flask import request, jsonify, session

from utils.decorators import validate_json, log_action, handle_db_errors
from user_manager import user_manager

from . import auth_bp, db_manager, logger


@auth_bp.route('/change-password', methods=['POST'])
@validate_json(['old_password', 'new_password'])
@log_action('修改密码')
@handle_db_errors
def change_password():
    """修改密码"""
    if not session.get('logged_in'):
        return jsonify({
            'success': False,
            'message': '请先登录'
        }), 401
    
    data = request.get_json()
    user_id = session.get('user_id')
    old_password = data['old_password']
    new_password = data['new_password']
    
    if len(new_password) < 6:
        return jsonify({
            'success': False,
            'message': '新密码至少需要6个字符'
        }), 400
    
    try:
        username = session.get('username')
        success, message = user_manager.change_password(username, old_password, new_password)
        if not success:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        logger.info(f"用户 {user_id} 修改密码成功")
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '修改密码失败，请稍后重试'
        }), 500
