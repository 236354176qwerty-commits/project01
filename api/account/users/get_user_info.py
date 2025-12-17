from flask import jsonify, session

from . import users_bp


@users_bp.route('/user/info', methods=['GET'])
def get_user_info():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    return jsonify({
        'success': True,
        'user_id': session.get('user_id'),
        'user_name': session.get('user_name'),
        'username': session.get('username'),
        'user_role': session.get('user_role'),
    })
