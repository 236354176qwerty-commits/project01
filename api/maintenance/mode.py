from flask import jsonify, session

from . import maintenance_bp, get_maintenance_mode, set_maintenance_mode


@maintenance_bp.route('/admin/maintenance/mode', methods=['GET'])
def api_get_maintenance_mode_api():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以查看维护模式状态'}), 403

    try:
        is_maintenance = get_maintenance_mode()
        return jsonify({
            'success': True,
            'maintenance_mode': is_maintenance,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取维护模式状态失败: {str(e)}',
        }), 500


@maintenance_bp.route('/admin/maintenance/mode/toggle', methods=['POST'])
def api_toggle_maintenance_mode_api():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以切换维护模式'}), 403

    try:
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
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'切换维护模式失败: {str(e)}',
        }), 500
