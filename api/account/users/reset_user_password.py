from flask import request, jsonify, session

from models import UserRole
from user_manager import user_manager

from . import users_bp


@users_bp.route('/users/reset_password', methods=['PUT'])
def api_reset_user_password():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    user_role = session.get('user_role')
    if user_role not in ['super_admin', 'admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以重置用户密码'})

    try:
        data = request.get_json()
        target_username = data.get('username')

        if not target_username:
            return jsonify({'success': False, 'message': '用户名不能为空'})

        if user_role == 'admin':
            current_username = session.get('username')
            target_user = user_manager.get_user_by_username(target_username)
            if not target_user:
                return jsonify({'success': False, 'message': '用户不存在'})
            if target_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN] and target_username != current_username:
                return jsonify({'success': False, 'message': '权限不足，管理员不能重置其他管理员或超级管理员的密码'})

        success, message = user_manager.reset_user_password(target_username)

        new_password = None
        if success and "新密码" in message:
            try:
                new_password = message.split("新密码：", 1)[1]
            except Exception:
                new_password = None

        return jsonify({
            'success': success,
            'message': message,
            'new_password': new_password if success else None,
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'重置用户密码失败: {str(e)}'})
