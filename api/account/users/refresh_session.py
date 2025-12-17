from flask import jsonify, session

from user_manager import user_manager

from . import users_bp


@users_bp.route('/refresh_session', methods=['POST'])
def api_refresh_session():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        username = session.get('username')
        user = user_manager.get_user(username)

        if user:
            session['real_name'] = user.real_name
            session['user_name'] = user.nickname or user.username
            session['user_role'] = user.role.value
            session['user_role_display'] = user_manager.get_role_display_name(user.role)

            return jsonify({
                'success': True,
                'message': '会话刷新成功',
                'display_name': session['user_name'],
            })
        else:
            return jsonify({'success': False, 'message': '用户不存在或已被删除'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'刷新会话失败: {str(e)}'})
