from flask import request, jsonify, session
import json

from database import DatabaseManager

from . import teams_bp


@teams_bp.route('/team/<int:team_id>/players/<int:player_id>', methods=['PUT'])
def api_update_team_player(team_id, player_id):
    """更新队伍选手信息（项目报名、状态等）- 仅领队或管理员"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')
    user_role = session.get('user_role')

    try:
        data = request.get_json() or {}
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM teams WHERE team_id = %s", (team_id,))
            team = cursor.fetchone()
            if not team:
                cursor.close()
                return jsonify({'success': False, 'message': '队伍不存在'}), 404

            is_admin = user_role in ['admin', 'super_admin']
            is_creator = team.get('created_by') == current_user_id
            if not (is_admin or is_creator):
                cursor.close()
                return jsonify({'success': False, 'message': '您没有权限修改此队伍的选手信息'}), 403

            cursor.execute(
                "SELECT * FROM team_players WHERE team_id = %s AND player_id = %s",
                (team_id, player_id),
            )
            player = cursor.fetchone()
            if not player:
                cursor.close()
                return jsonify({'success': False, 'message': '选手不存在'}), 404

            fields = []
            params = []

            if 'competition_event' in data:
                fields.append("competition_event = %s")
                params.append(data.get('competition_event'))

            if 'selected_events' in data:
                selected_events = data.get('selected_events')
                try:
                    selected_events_json = json.dumps(selected_events, ensure_ascii=False)
                except Exception:
                    selected_events_json = None
                fields.append("selected_events = %s")
                params.append(selected_events_json)

            if 'pair_registered' in data:
                fields.append("pair_registered = %s")
                params.append(bool(data.get('pair_registered')))

            if 'team_registered' in data:
                fields.append("team_registered = %s")
                params.append(bool(data.get('team_registered')))

            if 'pair_partner_name' in data:
                fields.append("pair_partner_name = %s")
                params.append(data.get('pair_partner_name'))

            if 'status' in data:
                fields.append("status = %s")
                params.append(data.get('status'))

            if not fields:
                cursor.close()
                return jsonify({'success': False, 'message': '没有需要更新的字段'}), 400

            params.append(team_id)
            params.append(player_id)

            sql = f"""
                UPDATE team_players
                SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE team_id = %s AND player_id = %s
            """
            cursor.execute(sql, tuple(params))
            conn.commit()
            cursor.close()

        return jsonify({'success': True, 'message': '选手信息更新成功'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'更新选手信息失败: {str(e)}'}), 500
