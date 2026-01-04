import re

from flask import request, jsonify, session

from user_manager import user_manager

from . import users_bp


@users_bp.route('/profile', methods=['GET', 'PUT'])
def api_profile():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    username = session.get('username')

    if request.method == 'GET':
        try:
            user = user_manager.get_user_by_username(username)
            if not user:
                return jsonify({'success': False, 'message': '用户不存在或已被删除'})

            return jsonify({
                'success': True,
                'user': {
                    'username': user.username,
                    'full_name': user.real_name,
                    'nickname': user.nickname or user.username,
                    'phone': user.phone,
                },
            })
        except Exception as e:
            return jsonify({'success': False, 'message': f'获取个人资料失败: {str(e)}'})

    # PUT
    try:
        data = request.get_json()
        full_name = data.get('full_name', '').strip()
        nickname = data.get('nickname', '').strip()
        phone = data.get('phone', '').strip()

        if not all([nickname, phone]):
            return jsonify({'success': False, 'message': '请填写完整的昵称和手机号'})

        if not full_name:
            user = user_manager.get_user_by_username(username)
            if user:
                full_name = (getattr(user, 'real_name', None) or '').strip()
            if not full_name:
                full_name = nickname or username

        phone_regex = r'^[0-9]{11}$'
        if not re.match(phone_regex, phone):
            return jsonify({'success': False, 'message': '手机号格式不正确，应为 11 位数字'})

        success, message = user_manager.update_user_profile(
            username, full_name, nickname, phone
        )

        if success:
            session['user_name'] = nickname or session.get('username')
            session['real_name'] = full_name

        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'更新个人资料失败: {str(e)}'})
