from flask import request, jsonify, session
from datetime import datetime

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import teams_bp


@teams_bp.route('/teams/<int:team_id>', methods=['PUT', 'DELETE'])
@log_action('更新或删除队伍')
@handle_db_errors
def api_update_or_delete_team(team_id):
    """更新或删除队伍（仅创建者或管理员）"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')
    user_role = session.get('user_role')

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
            return jsonify({'success': False, 'message': '您没有权限操作此队伍'}), 403

        if request.method == 'DELETE':
            now = datetime.now()
            cursor.execute(
                "UPDATE teams SET status = 'deleted', updated_at = %s WHERE team_id = %s",
                (now, team_id),
            )

            try:
                cursor.execute(
                    """
                    UPDATE team_applications
                    SET status = 'cancelled', updated_at = %s
                    WHERE team_id = %s AND status IN ('pending', 'approved')
                    """,
                    (now, team_id),
                )
            except Exception:
                pass

            try:
                # 删除队伍成员并同步 participants 表
                cursor.execute(
                    "SELECT user_id FROM team_players WHERE team_id = %s",
                    (team_id,),
                )
                player_user_ids = [row['user_id'] for row in cursor.fetchall() if row.get('user_id')]

                cursor.execute(
                    "DELETE FROM team_players WHERE team_id = %s",
                    (team_id,),
                )

                for uid in player_user_ids:
                    params = (team.get('event_id'), uid)
                    # 删除 participants 记录
                    cursor.execute(
                        "DELETE FROM participants WHERE event_id = %s AND user_id = %s",
                        params,
                    )
                    # 同步删除 event_participants 记录
                    cursor.execute(
                        "DELETE FROM event_participants WHERE event_id = %s AND user_id = %s",
                        params,
                    )
            except Exception:
                pass

            conn.commit()
            cursor.close()
            return jsonify({'success': True, 'message': '队伍已删除'}), 200

        data = request.get_json() or {}

        def _get_value(*keys):
            for k in keys:
                if k in data:
                    v = data.get(k)
                    return v.strip() if isinstance(v, str) else v
            return None

        fields = []
        params = []

        mapping = [
            ('team_name', ('team_name', 'teamName')),
            ('team_type', ('team_type', 'teamType')),
            ('team_address', ('team_address', 'teamAddress')),
            ('team_description', ('team_description', 'teamDescription')),
            ('leader_name', ('leader_name', 'leaderName')),
            ('leader_position', ('leader_position', 'leaderPosition')),
            ('leader_phone', ('leader_phone', 'leaderPhone')),
            ('leader_email', ('leader_email', 'leaderEmail')),
            ('status', ('status',)),
        ]

        for column, keys in mapping:
            value = _get_value(*keys)
            if value is not None:
                fields.append(f"{column} = %s")
                params.append(value)

        if not fields:
            cursor.close()
            return jsonify({'success': False, 'message': '没有需要更新的字段'}), 400

        now = datetime.now()
        fields.append("updated_at = %s")
        params.append(now)
        params.append(team_id)

        sql = f"""
            UPDATE teams
            SET {', '.join(fields)}
            WHERE team_id = %s
        """
        cursor.execute(sql, tuple(params))
        conn.commit()
        cursor.close()

    return jsonify({'success': True, 'message': '队伍信息更新成功'})
