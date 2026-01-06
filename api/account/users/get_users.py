from flask import jsonify, session
import time
import logging

from models import UserRole
from user_manager import user_manager
from utils.decorators import log_action, handle_db_errors, cache_result

from . import users_bp


logger = logging.getLogger(__name__)


@users_bp.route('/users', methods=['GET'])
@log_action('获取用户列表')
@handle_db_errors
@cache_result(timeout=5)
def api_get_users():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    user_role = session.get('user_role')
    if user_role not in ['super_admin', 'admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以查看用户列表'})

    t_start = time.perf_counter()
    users = user_manager.get_all_users()
    t_after_db = time.perf_counter()

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

    t_after_python = time.perf_counter()
    logger.info(
        "get_users timings: db=%.1fms, python=%.1fms, total=%.1fms",
        (t_after_db - t_start) * 1000,
        (t_after_python - t_after_db) * 1000,
        (t_after_python - t_start) * 1000,
    )

    return jsonify({
        'success': True,
        'data': users_data,
        'users': users_data,
    })
