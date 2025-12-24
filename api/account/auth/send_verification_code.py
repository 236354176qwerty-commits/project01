import os

from flask import request, jsonify

from utils.decorators import validate_json, log_action, handle_db_errors
from utils.helpers import validate_phone
from utils.sms_service import sms_provider

from . import auth_bp, db_manager, logger


@auth_bp.route('/send-verification-code', methods=['POST'])
@validate_json(['phone'])
@log_action('发送验证码')
@handle_db_errors
def send_verification_code():
    """发送手机验证码（支持注册和找回密码两种场景）"""
    data = request.get_json()
    phone = data['phone'].strip()
    purpose = data.get('purpose', 'reset_password')  # 'register' 或 'reset_password'
    
    # 验证手机号格式
    if not validate_phone(phone):
        return jsonify({
            'success': False,
            'message': '手机号格式不正确'
        }), 400
    
    try:
        # 检查手机号是否已注册
        user = db_manager.get_user_by_phone(phone)
        
        # 如果是找回密码，要求手机号已注册
        if purpose == 'reset_password' and not user:
            return jsonify({
                'success': False,
                'message': '该手机号未注册'
            }), 404
        
        # 如果是注册，要求手机号未注册
        if purpose == 'register' and user:
            return jsonify({
                'success': False,
                'message': '该手机号已被注册'
            }), 400
        
        # 发送验证码
        success, result = sms_provider.send_verification_code(phone)
        
        if success:
            logger.info(f"验证码发送成功: {phone}, 用途: {purpose}")

            provider_type = os.getenv('SMS_PROVIDER', 'demo').lower()
            debug_enabled = os.getenv('DEBUG', 'False').lower() == 'true'
            return_code = result if (provider_type == 'demo' and debug_enabled and isinstance(result, str)) else None
            return jsonify({
                'success': True,
                'message': '验证码已发送，请查收短信',
                'code': return_code
            })
        else:
            logger.error(f"验证码发送失败: {phone}, 原因: {result}")
            return jsonify({
                'success': False,
                'message': result
            }), 500
            
    except Exception as e:
        logger.error(f"发送验证码失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '发送失败，请稍后重试'
        }), 500
