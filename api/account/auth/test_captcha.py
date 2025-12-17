from flask import request, jsonify, session

from . import auth_bp, logger


@auth_bp.route('/test-captcha', methods=['POST'])
def test_captcha():
    """测试验证码接口：专门用于测试验证码验证功能，不受其他字段约束"""
    data = request.get_json()
    captcha = data.get('captcha', '').strip()
    
    # 验证验证码（大小写不敏感）
    session_captcha = session.get('captcha', '')
    logger.info(f"验证验证码 - 提交值: {captcha}, Session值: {session_captcha}")
    
    if not session_captcha:
        return jsonify({
            'success': False,
            'message': '验证码已过期，请刷新后重试'
        }), 400
    
    if captcha.upper() != session_captcha.upper():
        return jsonify({
            'success': False,
            'message': '验证码错误'
        }), 400
    
    return jsonify({
        'success': True,
        'message': '验证码验证成功'
    })
