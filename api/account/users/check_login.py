from flask import jsonify, session

from . import users_bp


@users_bp.route('/check_login', methods=['GET'])
def api_check_login():
    """检查登录状态。

    SSO 校验已由 before_request 中间件周期性执行，此接口仅读取 session
    即可，无需再次查询数据库。如果 before_request 检测到 token 不匹配，
    session 早已被 clear，此处自然返回 logged_in=False。
    """
    logged_in = session.get('logged_in', False)

    return jsonify({
        'logged_in': logged_in,
        'user_id': session.get('user_id'),
        'user_name': session.get('user_name'),
        'username': session.get('username'),
        'user_role': session.get('user_role'),
    })
