from flask import request, jsonify

from utils.decorators import validate_json, log_action, handle_db_errors
from utils.helpers import validate_phone

from . import auth_bp, db_manager, logger


@auth_bp.route('/reset-password', methods=['POST'])
@validate_json(['phone', 'newUsername', 'newPassword'])
@log_action('重置密码和账号')
@handle_db_errors
def reset_password():
    """通过手机验证码重置密码和账号（验证码已在进入第二步时验证）"""
    data = request.get_json()
    phone = data['phone'].strip()
    new_username = data['newUsername'].strip()
    new_password = data['newPassword']
    
    # 验证手机号格式
    if not validate_phone(phone):
        return jsonify({
            'success': False,
            'message': '手机号格式不正确'
        }), 400
    
    # 验证新账号
    if len(new_username) < 1 or len(new_username) > 12:
        return jsonify({
            'success': False,
            'message': '账号必须为1-12个字符'
        }), 400
    
    # 验证账号不能包含汉字
    if any('\u4e00' <= char <= '\u9fff' for char in new_username):
        return jsonify({
            'success': False,
            'message': '账号不能包含汉字'
        }), 400
    
    # 验证新密码
    if len(new_password) < 6 or len(new_password) > 20:
        return jsonify({
            'success': False,
            'message': '密码必须为6-20个字符'
        }), 400
    
    # 验证密码必须包含数字和小写字母
    if not any(c.isdigit() for c in new_password) or not any(c.islower() for c in new_password):
        return jsonify({
            'success': False,
            'message': '密码必须同时包含数字和小写字母'
        }), 400
    
    # 验证密码不能包含汉字
    if any('\u4e00' <= char <= '\u9fff' for char in new_password):
        return jsonify({
            'success': False,
            'message': '密码不能包含汉字'
        }), 400
    
    try:
        # 注意：验证码已在进入第二步时验证并删除，这里不再验证
        # 直接查找用户并更新信息
        
        # 查找用户
        user = db_manager.get_user_by_phone(phone)
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        # 检查新账号是否与当前用户的账号不同
        if new_username != user.username:
            # 如果新账号与原账号不同，检查新账号是否已被其他用户使用
            existing_user = db_manager.get_user_by_username(new_username)
            if existing_user:
                return jsonify({
                    'success': False,
                    'message': '该账号已被使用，请更换其他账号'
                }), 400
        
        # 更新账号和密码（使用明文密码，与登录验证保持一致）
        old_username = user.username
        user.username = new_username
        user.password = new_password
        db_manager.update_user(user)
        
        logger.info(f"用户 {old_username} 通过手机验证码重置账号为 {new_username} 并重置密码成功")
        
        return jsonify({
            'success': True,
            'message': '账号和密码重置成功，请使用新账号和密码登录'
        })
        
    except Exception as e:
        logger.error(f"重置账号和密码失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '重置失败，请稍后重试'
        }), 500
