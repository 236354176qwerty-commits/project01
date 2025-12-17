from flask import jsonify, session

from utils.decorators import log_action

from . import auth_bp, logger


@auth_bp.route('/logout', methods=['POST'])
@log_action('用户登出')
def logout():
    """用户登出"""
    username = session.get('username', 'Unknown')
    
    # 清除会话
    session.clear()
    
    logger.info(f"用户 {username} 登出")
    
    return jsonify({
        'success': True,
        'message': '登出成功'
    })
