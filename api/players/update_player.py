from flask import request, jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import players_bp


@players_bp.route('/players/<int:participant_id>', methods=['PUT'])
@log_action('更新参赛选手')
@handle_db_errors
def api_update_player(participant_id):
    """更新参赛选手信息API"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    data = request.get_json()
    db_manager = DatabaseManager()

    fields = {}
    if 'category' in data:
        fields['category'] = data['category']
    if 'weight_class' in data:
        fields['weight_class'] = data['weight_class']
    if 'status' in data:
        fields['status'] = data['status']
    if 'notes' in data:
        fields['notes'] = data['notes']

    if not fields:
        return jsonify({'success': False, 'message': '没有需要更新的字段'}), 400

    db_manager.update_participant_fields(participant_id, fields)

    return jsonify({
        'success': True,
        'message': '更新成功',
        'data': {
            'participant_id': participant_id,
            'updated_fields': list(fields.keys()),
        },
    })
