from flask import request, jsonify, session
import json

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import teams_bp


@teams_bp.route('/team/<int:team_id>/players/<int:player_id>', methods=['PUT'])
@log_action('更新队伍选手信息')
@handle_db_errors
def api_update_team_player(team_id, player_id):
    """更新队伍选手信息（项目报名、状态等）- 仅领队或管理员"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')
    user_role = session.get('user_role')

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

        candidate_id_card = None
        if 'id_card' in data and data.get('id_card'):
            candidate_id_card = str(data.get('id_card')).strip()
        else:
            candidate_id_card = (player.get('id_card') or '').strip() or None

        candidate_phone = None
        if 'phone' in data and data.get('phone'):
            candidate_phone = str(data.get('phone')).strip()
        else:
            candidate_phone = (player.get('phone') or '').strip() or None

        cursor.execute(
            """
            SELECT 1
            FROM team_staff ts
            WHERE ts.event_id = %s
              AND ts.status = 'active'
              AND ts.position = 'staff'
              AND ((%s IS NOT NULL AND ts.id_card = %s) OR (%s IS NOT NULL AND ts.phone = %s))
            LIMIT 1
            """,
            (player.get('event_id'), candidate_id_card, candidate_id_card, candidate_phone, candidate_phone),
        )
        staff_conflict = cursor.fetchone()
        if staff_conflict:
            cursor.close()
            return jsonify({
                'success': False,
                'message': '该人员已在本赛事登记为随行人员，不能登记为参赛人员'
            }), 400

        # 身份证号唯一性校验：同一 event_id + team_id 下不允许重复
        if 'id_card' in data and data.get('id_card'):
            new_id_card = str(data.get('id_card')).strip()
            old_id_card = (player.get('id_card') or '').strip()
            if new_id_card and new_id_card != old_id_card:
                cursor.execute(
                    """
                    SELECT player_id FROM team_players
                    WHERE team_id = %s AND event_id = %s AND id_card = %s AND player_id <> %s
                    LIMIT 1
                    """,
                    (team_id, player.get('event_id'), new_id_card, player_id),
                )
                dup = cursor.fetchone()
                if dup:
                    cursor.close()
                    return jsonify({'success': False, 'message': '该身份证号在本队中已存在'}), 400

        if 'competition_event' in data:
            fields.append("competition_event = %s")
            params.append(data.get('competition_event'))

        if 'name' in data:
            fields.append("name = %s")
            params.append(data.get('name'))

        if 'phone' in data:
            fields.append("phone = %s")
            params.append(data.get('phone'))

        if 'id_card' in data:
            fields.append("id_card = %s")
            params.append(data.get('id_card'))

        if 'registration_number' in data:
            fields.append("registration_number = %s")
            params.append(data.get('registration_number'))

        if 'gender' in data:
            fields.append("gender = %s")
            params.append(data.get('gender'))

        if 'age' in data:
            fields.append("age = %s")
            params.append(data.get('age'))

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

        updated_fields = [field.split('=')[0].strip() for field in fields]

        cursor.close()

    return jsonify({
        'success': True,
        'message': '选手信息更新成功',
        'data': {
            'team_id': team_id,
            'player_id': player_id,
            'updated_fields': updated_fields,
        },
    })
