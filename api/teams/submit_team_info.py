from flask import request, jsonify, session

from database import DatabaseManager

from . import teams_bp


def _send_system_notification(user_id, title, content, priority='normal'):
    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            system_sender_id = 1
            cursor.execute(
                '''
                INSERT INTO notifications 
                (sender_id, title, content, recipient_type, roles, priority, created_at)
                VALUES (%s, %s, %s, 'system', NULL, %s, NOW())
                ''',
                (system_sender_id, title, content, priority),
            )
            notification_id = cursor.lastrowid
            cursor.execute(
                '''
                INSERT INTO user_notifications 
                (notification_id, user_id, is_read, created_at)
                VALUES (%s, %s, FALSE, NOW())
                ''',
                (notification_id, user_id),
            )
            conn.commit()
            return True
    except Exception:
        return False


def _persist_team_submission(team_id, current_user_id, user_role):
    db_manager = DatabaseManager()
    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        # 先读取队伍基础信息和创建者
        cursor.execute(
            '''
            SELECT team_id, event_id, team_name, team_type, team_address,
                   team_description, leader_id, leader_name, leader_position,
                   leader_phone, leader_email, status, submitted_for_review,
                   submitted_at, client_team_key, created_by, created_at, updated_at
            FROM teams
            WHERE team_id = %s
            ''',
            (team_id,),
        )
        team_row = cursor.fetchone()
        if not team_row:
            cursor.close()
            return {'error': '队伍不存在', 'status': 404}

        # 权限校验：创建者或管理员才可以提交
        is_owner = team_row.get('created_by') == current_user_id if team_row.get('created_by') else False
        is_admin = user_role in ['admin', 'super_admin']
        if not is_owner and not is_admin:
            cursor.close()
            return {'error': '权限不足：只有领队可以提交审核', 'status': 403}

        event_id = team_row.get('event_id')

        # 在同一事务中：更新 teams 提交状态
        try:
            # 更新原始队伍表的提交标记
            cursor.execute(
                """
                UPDATE teams
                SET submitted_for_review = 1,
                    submitted_at = NOW(),
                    updated_at = NOW()
                WHERE team_id = %s
                """,
                (team_id,),
            )

            cursor.execute('SELECT submitted_at FROM teams WHERE team_id = %s', (team_id,))
            latest = cursor.fetchone() or {}
            conn.commit()
            submitted_at = latest.get('submitted_at')
            cursor.close()
            return {'submitted_at': submitted_at}
        except Exception:
            conn.rollback()
            cursor.close()
            raise


@teams_bp.route('/team/submit-info', methods=['POST'])
def api_submit_team_info():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        data = request.get_json() or {}
        team_id = data.get('team_id')
        team_name = data.get('team_name') or '队伍'
        event_name = data.get('event_name') or '赛事'
        member_ids = data.get('member_ids') or []
        is_first_submit = bool(data.get('is_first_submit', False))
        creator_username = data.get('creator_username')

        if not team_id:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400

        current_username = session.get('username')
        current_user_id = session.get('user_id')
        user_role = session.get('user_role')

        if not creator_username or creator_username != current_username:
            return jsonify(
                {
                    'success': False,
                    'message': '权限不足：只有领队可以提交审核',
                }
            ), 403

        submission_result = _persist_team_submission(team_id, current_user_id, user_role)
        if 'error' in submission_result:
            return jsonify({'success': False, 'message': submission_result['error']}), submission_result['status']

        submitted_at_iso = (
            submission_result['submitted_at'].isoformat()
            if submission_result.get('submitted_at')
            else None
        )

        if is_first_submit:
            if not member_ids:
                return jsonify(
                    {
                        'success': True,
                        'message': '队伍信息上报成功',
                        'submitted_at': submitted_at_iso,
                    }
                )
            title = '队伍报名成功'
            content = f'您所在的【{team_name}】已成功报名【{event_name}】。队长已完成队伍信息上报，请做好参赛准备。'
            success_count = 0
            for member_id in member_ids:
                if _send_system_notification(member_id, title, content, priority='important'):
                    success_count += 1
            return jsonify(
                {
                    'success': True,
                    'message': f'队伍信息上报成功，已通知 {success_count}/{len(member_ids)} 位队员',
                    'submitted_at': submitted_at_iso,
                }
            )

        return jsonify({'success': True, 'message': '队伍信息更新成功', 'submitted_at': submitted_at_iso})

    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'}), 500
