from flask import request, jsonify, session

import secrets

from models import UserStatus
from utils.decorators import validate_json, log_action, handle_db_errors
from user_manager import user_manager

from . import auth_bp, db_manager, logger


@auth_bp.route('/login', methods=['POST'])
@validate_json(['username', 'password'])
@log_action('用户登录')
@handle_db_errors
def login():
    """用户登录"""
    data = request.get_json()
    username = data['username'].strip()
    password = data['password']

    user, auth_message = user_manager.authenticate_user(username, password)

    if not user:
        message = auth_message or '用户名或密码错误'

        if message == '用户不存在':
            logger.warning(f"用户 {username} 不存在")
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 401

        if any(keyword in message for keyword in ['冻结', '状态异常', '状态为']):
            logger.warning(f"用户 {username} 尝试登录失败（状态原因）: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 403

        if '禁用' in message:
            logger.warning(f"用户 {username} 已被禁用: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 401

        logger.warning(f"用户 {username} 登录失败: {message}")
        return jsonify({
            'success': False,
            'message': '用户名或密码错误'
        }), 401

    # 单点登录：登录即生成新的会话标识，写入数据库；旧会话将被挤下线
    session_token = secrets.token_hex(32)
    try:
        db_manager.update_user_session_token(user.user_id, session_token)
        db_manager.invalidate_session_token_cache(user.user_id)
    except Exception as e:
        logger.error(f"更新用户session_token失败: {e}")
        return jsonify({'success': False, 'message': '登录失败，请稍后重试'}), 500

    # 设置会话
    session['logged_in'] = True
    session['user_id'] = user.user_id
    session['user_name'] = user.nickname or user.username  # 优先使用昵称，没有昵称则使用用户名
    session['username'] = user.username
    session['user_role'] = user.role.value
    session['session_token'] = session_token
    session.permanent = True

    logger.info(f"用户 {username} 登录成功")

    user_data = {
        'id': user.user_id,
        'username': user.username,
        'real_name': user.real_name,
        'role': user.role.value,
        'email': user.email,
    }

    return jsonify({
        'success': True,
        'message': '登录成功',
        'data': user_data,
        'user': user_data,
    })
