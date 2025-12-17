from flask import request, jsonify

from user_manager import user_manager

from . import users_bp


@users_bp.route('/check_username', methods=['GET'])
def api_check_username():
    """检查用户名是否可用，兼容旧前端 /api/check_username 接口"""
    try:
        username = (request.args.get('username') or '').strip()
        if not username:
            return jsonify({
                'success': False,
                'message': '缺少参数 username',
                'available': False,
            }), 400

        user = user_manager.get_user_by_username(username)
        available = user is None

        return jsonify({
            'success': True,
            'available': available,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'检查用户名失败: {str(e)}',
            'available': False,
        }), 500
