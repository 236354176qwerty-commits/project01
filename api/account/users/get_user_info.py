from flask import jsonify, session

from . import users_bp


@users_bp.route('/user/info', methods=['GET'])
def get_user_info():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('user_name'),
        'username': session.get('username'),
        'user_role': session.get('user_role'),
    }

    return jsonify({
        'success': True,
        'data': user_data,
        'user_id': user_data['user_id'],
        'user_name': user_data['user_name'],
        'username': user_data['username'],
        'user_role': user_data['user_role'],
    })
