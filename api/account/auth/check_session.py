from flask import jsonify, session

from . import auth_bp


@auth_bp.route('/check-session', methods=['GET'])
def check_session():
    """检查会话状态"""
    if session.get('logged_in'):
        return jsonify({
            'logged_in': True,
            'user': {
                'id': session.get('user_id'),
                'username': session.get('username'),
                'real_name': session.get('user_name'),
                'role': session.get('user_role')
            }
        })
    else:
        return jsonify({
            'logged_in': False
        })
