from flask import Blueprint, request, jsonify, session

from database import DatabaseManager

from . import notifications_bp


@notifications_bp.route('/notifications/send', methods=['POST'])
def api_send_notification():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') != 'super_admin':
        return jsonify({'success': False, 'message': '权限不足，只有超级管理员可以发送通知'}), 403

    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        recipient_type = data.get('recipient_type', 'all')
        roles = data.get('roles', [])
        event_id = data.get('event_id')
        priority = data.get('priority', 'normal')

        if not title or not content:
            return jsonify({'success': False, 'message': '标题和内容不能为空'})

        db_manager = DatabaseManager()
        sender_id = session.get('user_id')

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                '''
                INSERT INTO notifications 
                (sender_id, title, content, recipient_type, roles, priority, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ''',
                (sender_id, title, content, recipient_type, ','.join(roles) if roles else None, priority),
            )

            notification_id = cursor.lastrowid

            if recipient_type == 'all':
                cursor.execute('SELECT user_id FROM users WHERE user_id != %s', (sender_id,))
                recipients = cursor.fetchall()
            elif recipient_type == 'role':
                placeholders = ','.join(['%s'] * len(roles))
                cursor.execute(
                    f'''
                    SELECT user_id FROM users 
                    WHERE role IN ({placeholders}) AND user_id != %s
                    ''',
                    tuple(roles) + (sender_id,),
                )
                recipients = cursor.fetchall()
            elif recipient_type == 'event':
                # 优先从 event_participants 中选择该赛事的参赛运动员（排除发送者）
                cursor.execute(
                    '''
                    SELECT DISTINCT user_id FROM event_participants
                    WHERE event_id = %s AND user_id != %s AND role = 'athlete'
                    ''',
                    (event_id, sender_id),
                )
                recipients = cursor.fetchall()

                # 如新表中尚无数据，则回退到旧的 participants 表
                if not recipients:
                    cursor.execute(
                        '''
                        SELECT DISTINCT user_id FROM participants 
                        WHERE event_id = %s AND user_id != %s
                        ''',
                        (event_id, sender_id),
                    )
                    recipients = cursor.fetchall()
            else:
                recipients = []

            for recipient in recipients:
                cursor.execute(
                    '''
                    INSERT INTO user_notifications 
                    (notification_id, user_id, is_read, created_at)
                    VALUES (%s, %s, FALSE, NOW())
                    ''',
                    (notification_id, recipient[0]),
                )

            conn.commit()

            return jsonify({
                'success': True,
                'message': f'通知已发送给 {len(recipients)} 个用户',
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'发送通知失败: {str(e)}'}), 500
