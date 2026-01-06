from flask import request, jsonify, session

from models import UserRole
from user_manager import user_manager
from utils.decorators import log_action, handle_db_errors

from . import users_bp


@users_bp.route('/users/role_and_status', methods=['PUT'])
@log_action('更新用户角色和状态')
@handle_db_errors
def api_update_user_role_and_status():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    user_role = session.get('user_role')
    if user_role not in ['super_admin', 'admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以修改用户角色和状态'})

    data = request.get_json()
    target_username = data.get('username')
    new_role_str = data.get('new_role')
    new_status = data.get('new_status')

    if not all([target_username, new_role_str, new_status]):
        return jsonify({'success': False, 'message': '用户名、新角色和新状态不能为空'})

    try:
        new_role = UserRole(new_role_str)
    except ValueError:
        return jsonify({'success': False, 'message': '无效的角色类型'})

    valid_statuses = ['normal', 'frozen', 'abnormal']
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'message': '无效的状态类型'})

    if new_status == 'normal':
        is_active = True
        status_type = None
    elif new_status == 'frozen':
        is_active = False
        status_type = 'frozen'
    else:
        is_active = False
        status_type = 'abnormal'

    operator_username = session.get('username')
    success, message = user_manager.update_user_role_and_status(
        target_username, new_role, is_active, operator_username, status_type
    )

    if success and new_status == 'frozen':
        result_message = f"用户 {target_username} 已被冻结，角色为 {user_manager.get_role_display_name(new_role)}"
    else:
        result_message = message

    return jsonify({
        'success': success,
        'message': result_message,
        'data': {
            'username': target_username,
            'new_role': new_role_str,
            'new_status': new_status,
        },
    })
