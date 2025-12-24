from flask import request, jsonify, session

from models import User, UserRole
from utils.decorators import validate_json, log_action, handle_db_errors
from utils.helpers import validate_phone
from utils.sms_service import sms_provider

from . import auth_bp, db_manager, logger


@auth_bp.route('/register', methods=['POST'])
@validate_json(['username', 'password', 'confirmPassword', 'nickname', 'phone', 'captcha', 'sms_code'])
@log_action('用户注册')
@handle_db_errors
def register():
    """用户注册"""
    data = request.get_json()
    
    # 验证输入数据
    username = data['username'].strip()
    password = data['password']
    confirm_password = data['confirmPassword']
    nickname = data['nickname'].strip()
    phone = data['phone'].strip()
    captcha = data['captcha'].strip()
    sms_code = data.get('sms_code', '').strip()  # 短信验证码
    
    # 验证验证码（大小写不敏感）
    session_captcha = session.get('captcha', '')
    logger.info(f"验证验证码 - 提交值: {captcha}, Session值: {session_captcha}")
    
    # 如果验证码为空或已过期
    if not session_captcha:
        logger.warning("验证码不存在或已过期")
        return jsonify({
            'success': False,
            'message': '验证码已过期，请刷新后重试'
        }), 400
        
    # 验证码不匹配
    if captcha.upper() != session_captcha.upper():
        logger.warning(f"验证码不匹配 - 提交值: {captcha}, 期望值: {session_captcha}")
        return jsonify({
            'success': False,
            'message': '验证码错误，请重新输入'
        }), 400
    
    # 验证短信验证码
    if not sms_code:
        logger.warning("未提供短信验证码")
        return jsonify({
            'success': False,
            'message': '请输入短信验证码'
        }), 400

    logger.info(f"验证短信验证码 - 手机号: {phone}")
    sms_ok, sms_msg = sms_provider.verify_code(phone, sms_code)
    if not sms_ok:
        logger.warning(f"短信验证码验证失败 - 手机号: {phone}, 原因: {sms_msg}")
        return jsonify({
            'success': False,
            'message': sms_msg
        }), 400
    
    
    # 基本验证
    if len(username) < 1 or len(username) > 12:
        return jsonify({
            'success': False,
            'message': '账号必须为1-12个字符'
        }), 400
    
    # 验证账号不能包含汉字
    if any('\u4e00' <= char <= '\u9fff' for char in username):
        return jsonify({
            'success': False,
            'message': '账号不能包含汉字'
        }), 400
    
    if len(password) < 6 or len(password) > 20:
        return jsonify({
            'success': False,
            'message': '密码必须为6-20个字符'
        }), 400
    
    # 验证密码必须包含数字和小写字母
    if not any(c.isdigit() for c in password) or not any(c.islower() for c in password):
        return jsonify({
            'success': False,
            'message': '密码必须同时包含数字和小写字母'
        }), 400
    
    # 验证密码不能包含汉字
    if any('\u4e00' <= char <= '\u9fff' for char in password):
        return jsonify({
            'success': False,
            'message': '密码不能包含汉字'
        }), 400
    
    # 验证确认密码
    if password != confirm_password:
        return jsonify({
            'success': False,
            'message': '两次输入的密码不一致'
        }), 400
    
    if len(nickname) < 2 or len(nickname) > 20:
        return jsonify({
            'success': False,
            'message': '用户昵称必须为2-20个字符'
        }), 400
    
    # 验证敏感词汇
    sensitive_words = ['政治', '暴力', '色情', '赌博', '毒品', '反动', '邪教']
    for word in sensitive_words:
        if word in nickname:
            return jsonify({
                'success': False,
                'message': '用户昵称包含敏感词汇，请重新输入'
            }), 400
    
    if not validate_phone(phone):
        return jsonify({
            'success': False,
            'message': '手机号格式不正确'
        }), 400
    
    try:
        # 检查用户名是否已存在
        existing_user = db_manager.get_user_by_username(username)
        if existing_user:
            return jsonify({
                'success': False,
                'message': '用户名已存在'
            }), 400

        # 检查手机号是否已存在
        existing_phone = db_manager.get_user_by_phone(phone)
        if existing_phone:
            return jsonify({
                'success': False,
                'message': '该手机号已被注册'
            }), 400
        
        # 创建新用户
        new_user = User(
            username=username,
            password=password,  # 存储明文密码（与登录验证保持一致）
            real_name=nickname,  # 使用昵称作为真实姓名字段
            nickname=nickname,
            email=None,  # 不再使用邮箱
            phone=phone,
            role=UserRole.USER
        )
        
        # 保存到数据库
        created_user = db_manager.create_user(new_user)
        
        # 注册成功，移除session中的验证码
        session.pop('captcha', None)
        logger.info(f"新用户注册成功: {username}")
        
        return jsonify({
            'success': True,
            'message': '注册成功，请登录',
            'user': {
                'id': created_user.user_id,
                'username': created_user.username,
                'nickname': created_user.nickname,
                'phone': created_user.phone
            }
        })
        
    except Exception as e:
        logger.error(f"注册失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '注册失败，请稍后重试'
        }), 500
