from flask import make_response, session

from utils.captcha import captcha_generator

from . import auth_bp, logger


@auth_bp.route('/captcha', methods=['GET'])
def generate_captcha():
    """生成验证码"""
    try:
        # 生成验证码
        text, image_data = captcha_generator.generate()
        
        # 将验证码文本存储到session中
        session['captcha'] = text.upper()
        logger.info(f"生成验证码: {text}, 存储到session: {session['captcha']}")
        
        # 创建响应
        response = make_response(image_data)
        response.headers['Content-Type'] = 'image/png'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        logger.error(f"生成验证码失败: {str(e)}")
        # 返回一个简单的错误图片或文本
        return "验证码生成失败", 500
