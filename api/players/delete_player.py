from flask import jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import players_bp


@players_bp.route('/players/<int:participant_id>', methods=['DELETE'])
@log_action('删除参赛选手')
@handle_db_errors
def api_delete_player(participant_id):
    """删除参赛选手API"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    db_manager = DatabaseManager()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        # 先查出 event_id 和 user_id，用于同步删除 event_participants
        cursor.execute(
            'SELECT event_id, user_id FROM participants WHERE participant_id = %s',
            (participant_id,),
        )
        row = cursor.fetchone()

        if row is not None:
            event_id, user_id = row
            cursor.execute(
                'DELETE FROM event_participants WHERE event_id = %s AND user_id = %s',
                (event_id, user_id),
            )

        query = 'DELETE FROM participants WHERE participant_id = %s'
        cursor.execute(query, (participant_id,))
        conn.commit()

    return jsonify({
        'success': True,
        'message': '删除成功',
        'data': {
            'participant_id': participant_id,
        },
    })
