import re

from flask import request, jsonify, session

from user_manager import user_manager

from . import users_bp


@users_bp.route('/change_password', methods=['POST'])
def api_change_password():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        data = request.get_json()
        current_password = data.get('currentPassword', '')
        new_password = data.get('newPassword', '')
        confirm_new_password = data.get('confirmNewPassword', '')

        if not all([current_password, new_password, confirm_new_password]):
            return jsonify({'success': False, 'message': '请填写当前密码、新密码和确认密码'})

        if len(new_password) < 6 or len(new_password) > 20:
            return jsonify({'success': False, 'message': '新密码长度应为 6-20 位'})

        if not re.search(r'\d', new_password):
            return jsonify({'success': False, 'message': '新密码必须包含至少一个数字'})

        if not re.search(r'[a-z]', new_password):
            return jsonify({'success': False, 'message': '新密码必须包含至少一个小写字母'})

        if re.search(r'[\u4e00-\u9fa5]', new_password):
            return jsonify({'success': False, 'message': '新密码不能包含中文字符'})

        if new_password != confirm_new_password:
            return jsonify({'success': False, 'message': '两次输入的新密码不一致'})

        username = session.get('username')
        success, message = user_manager.change_password(
            username, current_password, new_password
        )

        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'修改密码失败: {str(e)}'})
