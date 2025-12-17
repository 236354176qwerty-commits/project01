from flask import request, jsonify, session

from database import DatabaseManager

from . import players_bp


@players_bp.route('/players', methods=['GET'])
def api_get_players():
    """获取参赛选手列表API"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        print("=== 获取参赛选手列表流程开始 ===")
        print(f"当前 session: {session}")
        print(f"查询参数: {request.args}")

        db_manager = DatabaseManager()

        # 获取筛选条件
        event_id = request.args.get('event_id')
        participant_id = request.args.get('participant_id')

        print(f"赛事ID: {event_id}, 选手ID: {participant_id}")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            # 如果指定了赛事，则校验赛事存在
            if event_id:
                cursor.execute('SELECT * FROM events WHERE event_id = %s', (event_id,))
                event = cursor.fetchone()
                if not event:
                    print(f"赛事ID {event_id} 不存在")
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

            print(f"最终SQL: {query}")
            print(f"参数: {params}")

            cursor.execute(query, tuple(params) if params else None)
            players = cursor.fetchall()

            print(f"查询到 {len(players)} 条记录")

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

            print("=== 获取参赛选手列表流程结束 ===")
            return jsonify({
                'success': True,
                'data': players_list,
            })

    except Exception as e:
        print(f'获取参赛选手列表时发生错误: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取参赛选手信息失败: {str(e)}',
            'debug': str(e),
        }), 500
