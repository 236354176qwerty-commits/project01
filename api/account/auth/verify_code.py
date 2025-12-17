from flask import request, jsonify

from utils.decorators import validate_json, log_action, handle_db_errors
from utils.helpers import validate_phone
from utils.sms_service import sms_provider

from . import auth_bp, logger


@auth_bp.route('/verify-code', methods=['POST'])
@validate_json(['phone', 'code'])
@log_action('验证验证码')
@handle_db_errors
def verify_code():
    """验证验证码是否正确（验证成功后立即删除验证码）"""
    data = request.get_json()
    phone = data['phone'].strip()
    code = data['code'].strip()
    
    # 验证手机号格式
    if not validate_phone(phone):
        return jsonify({
            'success': False,
            'message': '手机号格式不正确'
        }), 400
    
    # 验证验证码格式
    if not code or len(code) != 6 or not code.isdigit():
        return jsonify({
            'success': False,
            'message': '验证码格式不正确'
        }), 400
    
    try:
        # 验证验证码并立即删除（一次性使用，防止重复验证）
        success, message = sms_provider.verify_code(phone, code)
        
        if success:
            logger.info(f"验证码验证成功并已失效: {phone}")
            return jsonify({
                'success': True,
                'message': '验证码验证成功'
            })
        else:
            logger.warning(f"验证码验证失败: {phone}, 原因: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"验证验证码失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '验证失败，请稍后重试'
        }), 500
