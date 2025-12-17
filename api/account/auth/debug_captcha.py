from datetime import datetime

from flask import request, jsonify, session

from . import auth_bp, logger


@auth_bp.route('/debug-captcha', methods=['GET'])
def debug_captcha():
    """调试端点：显示当前session中的验证码值"""
    captcha_value = session.get('captcha', '未设置')
    session_id = request.cookies.get('session')
    
    logger.info(f"调试验证码 - Session ID: {session_id}, 验证码值: {captcha_value}")
    
    return jsonify({
        'session_id': session_id,
        'captcha_value': captcha_value,
        'session_contents': dict(session),  # 显示所有session内容
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
