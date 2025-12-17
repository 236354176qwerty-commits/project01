from flask import request, jsonify, session

from models import UserRole
from user_manager import user_manager

from . import users_bp


@users_bp.route('/users/role', methods=['PUT'])
def api_update_user_role():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    user_role = session.get('user_role')
    if user_role not in ['super_admin', 'admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以修改用户角色'})

    try:
        data = request.get_json()
        target_username = data.get('username')
        new_role_str = data.get('new_role')

        if not all([target_username, new_role_str]):
            return jsonify({'success': False, 'message': '用户名和新角色不能为空'})

        try:
            new_role = UserRole(new_role_str)
        except ValueError:
            return jsonify({'success': False, 'message': '无效的角色类型'})

        operator_username = session.get('username')
        success, message = user_manager.update_user_role(
            target_username, new_role, operator_username
        )

        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'更新用户角色失败: {str(e)}'})
