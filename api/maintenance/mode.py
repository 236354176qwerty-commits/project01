from flask import jsonify, session

from utils.decorators import log_action, handle_db_errors
from . import maintenance_bp, get_maintenance_mode, set_maintenance_mode


@maintenance_bp.route('/admin/maintenance/mode', methods=['GET'])
@log_action('获取维护模式状态')
@handle_db_errors
def api_get_maintenance_mode_api():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以查看维护模式状态'}), 403

    is_maintenance = get_maintenance_mode()
    return jsonify({
        'success': True,
        'maintenance_mode': is_maintenance,
        'data': {
            'maintenance_mode': is_maintenance,
        },
    })


@maintenance_bp.route('/admin/maintenance/mode/toggle', methods=['POST'])
@log_action('切换维护模式')
@handle_db_errors
def api_toggle_maintenance_mode_api():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以切换维护模式'}), 403

    current_mode = get_maintenance_mode()
    new_mode = not current_mode

    user_id = session.get('user_id')
    if not set_maintenance_mode(new_mode, user_id):
        return jsonify({
            'success': False,
            'message': '更新维护模式失败',
        }), 500

    return jsonify({
        'success': True,
        'maintenance_mode': new_mode,
        'data': {
            'maintenance_mode': new_mode,
        },
    })
