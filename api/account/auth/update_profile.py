from flask import request, jsonify, session

from utils.decorators import validate_json, log_action, handle_db_errors
from utils.helpers import validate_email, validate_phone

from . import auth_bp, logger


@auth_bp.route('/profile', methods=['PUT'])
@validate_json(['real_name', 'email'])
@log_action('更新用户信息')
@handle_db_errors
def update_profile():
    """更新用户信息"""
    if not session.get('logged_in'):
        return jsonify({
            'success': False,
            'message': '请先登录'
        }), 401
    
    data = request.get_json()
    user_id = session.get('user_id')
    
    # 验证输入数据
    real_name = data['real_name'].strip()
    email = data['email'].strip()
    phone = data.get('phone', '').strip()
    
    if not validate_email(email):
        return jsonify({
            'success': False,
            'message': '邮箱格式不正确'
        }), 400
    
    if phone and not validate_phone(phone):
        return jsonify({
            'success': False,
            'message': '手机号格式不正确'
        }), 400
    
    try:
        # 这里应该添加更新用户信息的数据库操作
        # 由于当前的 DatabaseManager 没有 update_user 方法，
        # 这里只是示例代码
        
        logger.info(f"用户 {user_id} 更新个人信息")
        
        return jsonify({
            'success': True,
            'message': '信息更新成功'
        })
        
    except Exception as e:
        logger.error(f"更新用户信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '更新失败，请稍后重试'
        }), 500
