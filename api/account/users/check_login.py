from flask import jsonify, session

from . import users_bp

from database import DatabaseManager


@users_bp.route('/check_login', methods=['GET'])
def api_check_login():
    user_id = session.get('user_id')
    session_token = session.get('session_token')
    db_token = None
    token_match = None
    if user_id:
        try:
            db_manager = DatabaseManager()
            db_token = db_manager.get_user_session_token(user_id)
            token_match = bool(db_token) and bool(session_token) and db_token == session_token
        except Exception:
            db_token = None
            token_match = None

    return jsonify({
        'logged_in': session.get('logged_in', False),
        'user_id': session.get('user_id'),
        'user_name': session.get('user_name'),
        'username': session.get('username'),
        'user_role': session.get('user_role'),
        'session_token_present': bool(session_token),
        'db_token_present': bool(db_token),
        'token_match': token_match,
    })
