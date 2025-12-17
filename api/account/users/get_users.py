from flask import jsonify, session

from models import UserRole
from user_manager import user_manager

from . import users_bp


@users_bp.route('/users', methods=['GET'])
def api_get_users():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    user_role = session.get('user_role')
    if user_role not in ['super_admin', 'admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以查看用户列表'})

    try:
        users = user_manager.get_all_users()
        users_data = []
        current_user_role = session.get('user_role')
        current_username = session.get('username')

        for user in users:
            user_dict = user.to_dict() if hasattr(user, 'to_dict') else {
                'user_id': user.user_id,
                'username': user.username,
                'role': user.role.value,
            }

            if current_user_role == 'super_admin':
                user_dict['password'] = user.password
            elif current_user_role == 'admin':
                if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN] and user.username != current_username:
                    user_dict['password'] = '*'
                else:
                    user_dict['password'] = user.password
            else:
                user_dict['password'] = '*'

            user_dict['full_name'] = user.real_name
            user_dict['team_name'] = getattr(user, 'team_name', None) or user.real_name

            users_data.append(user_dict)

        return jsonify({'success': True, 'users': users_data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取用户列表失败: {str(e)}'})
