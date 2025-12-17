from flask import jsonify, session

from . import users_bp


@users_bp.route('/check_login', methods=['GET'])
def api_check_login():
    return jsonify({
        'logged_in': session.get('logged_in', False),
        'user_id': session.get('user_id'),
        'user_name': session.get('user_name'),
        'username': session.get('username'),
        'user_role': session.get('user_role'),
    })
