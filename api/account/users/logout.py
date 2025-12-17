from flask import jsonify, session

from . import users_bp


@users_bp.route('/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': '退出成功'})
