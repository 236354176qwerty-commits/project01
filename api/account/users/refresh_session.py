from flask import jsonify, session
import time
import logging

from user_manager import user_manager
from utils.decorators import log_action, handle_db_errors

from . import users_bp


logger = logging.getLogger(__name__)


@users_bp.route('/refresh_session', methods=['POST'])
@log_action('刷新会话')
@handle_db_errors
def api_refresh_session():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    t_start = time.perf_counter()

    username = session.get('username')
    user = user_manager.get_user(username)
    t_after_get = time.perf_counter()

    if user:
        session['real_name'] = user.real_name
        session['user_name'] = user.nickname or user.username
        session['user_role'] = user.role.value
        session['user_role_display'] = user_manager.get_role_display_name(user.role)

        data = {
            'user_id': user.user_id,
            'username': user.username,
            'display_name': session['user_name'],
            'role': user.role.value,
        }

        resp = jsonify({
            'success': True,
            'message': '会话刷新成功',
            'display_name': session['user_name'],
            'data': data,
        })
    else:
        resp = jsonify({'success': False, 'message': '用户不存在或已被删除'})

    t_end = time.perf_counter()
    logger.info(
        "refresh_session timings: get_user=%.1fms, total=%.1fms",
        (t_after_get - t_start) * 1000,
        (t_end - t_start) * 1000,
    )

    return resp
