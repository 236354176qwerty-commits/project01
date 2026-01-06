from flask import request, jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import players_bp


@players_bp.route('/players', methods=['GET'])
@log_action('获取参赛选手列表')
@handle_db_errors
def api_get_players():
    """获取参赛选手列表API"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    db_manager = DatabaseManager()

    # 获取筛选条件
    event_id = request.args.get('event_id')
    participant_id = request.args.get('participant_id')

    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        # 如果指定了赛事，则校验赛事存在
        if event_id:
            cursor.execute('SELECT * FROM events WHERE event_id = %s', (event_id,))
            event = cursor.fetchone()
            if not event:
                return jsonify({
                    'success': False,
                    'message': f'赛事ID {event_id} 不存在'
                }), 404

        # 构建查询SQL
        query = '''
            SELECT 
                p.participant_id,
                p.event_id,
                p.user_id,
                p.registration_number,
                p.event_member_no,
                p.category,
                p.weight_class,
                p.status,
                p.notes,
                p.registered_at,
                u.real_name,
                u.phone,
                u.email,
                e.name as event_name
            FROM participants p
            JOIN users u ON p.user_id = u.user_id
            JOIN events e ON p.event_id = e.event_id
        '''

        params = []
        conditions = []

        if event_id:
            conditions.append('p.event_id = %s')
            params.append(event_id)

        if participant_id:
            conditions.append('p.participant_id = %s')
            params.append(participant_id)

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += ' ORDER BY p.registered_at DESC'

        cursor.execute(query, tuple(params) if params else None)
        players = cursor.fetchall()

        players_list = []
        for player in players:
            players_list.append({
                'participant_id': player['participant_id'],
                'event_id': player['event_id'],
                'user_id': player['user_id'],
                'registration_number': player['registration_number'],
                'category': player['category'],
                'weight_class': player['weight_class'],
                'status': player['status'],
                'notes': player['notes'],
                'registered_at': player['registered_at'].isoformat() if player['registered_at'] else None,
                'real_name': player['real_name'],
                'phone': player['phone'],
                'email': player['email'],
                'event_name': player['event_name'],
            })

    return jsonify({
        'success': True,
        'data': players_list,
    })
