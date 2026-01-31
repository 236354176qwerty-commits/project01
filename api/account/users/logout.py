from flask import jsonify, session

from database import DatabaseManager
from . import users_bp


@users_bp.route('/logout', methods=['POST'])
def api_logout():
    user_id = session.get('user_id')
    if user_id:
        try:
            db_manager = DatabaseManager()
            db_manager.update_user_session_token(user_id, None)
        except Exception:
            pass
    session.clear()
    return jsonify({'success': True, 'message': '退出成功'})
