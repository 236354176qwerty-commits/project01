from flask import request, jsonify, session
from datetime import datetime

from database import DatabaseManager

from . import teams_bp


@teams_bp.route('/events/<int:event_id>/team-draft', methods=['GET', 'PUT', 'DELETE'])
def api_team_draft(event_id):
    """当前登录用户在指定赛事下的队伍草稿 CRUD"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')

    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            if request.method == 'GET':
                cursor.execute(
                    "SELECT * FROM team_drafts WHERE user_id = %s and event_id = %s",
                    (current_user_id, event_id),
                )
                draft = cursor.fetchone()
                cursor.close()

                if not draft:
                    return jsonify({'success': True, 'draft': None})

                draft_data = {
                    'draftId': draft['draft_id'],
                    'userId': draft['user_id'],
                    'eventId': draft['event_id'],
                    'teamName': draft.get('team_name'),
                    'teamType': draft.get('team_type'),
                    'teamAddress': draft.get('team_address'),
                    'teamDescription': draft.get('team_description'),
                    'leaderName': draft.get('leader_name'),
                    'leaderPosition': draft.get('leader_position'),
                    'leaderPhone': draft.get('leader_phone'),
                    'leaderEmail': draft.get('leader_email'),
                    'clientTeamKey': draft.get('client_team_key'),
                    'isSubmitted': bool(draft.get('is_submitted')),
                    'createdAt': draft['created_at'].isoformat() if draft.get('created_at') else None,
                    'updatedAt': draft['updated_at'].isoformat() if draft.get('updated_at') else None,
                }

                return jsonify({'success': True, 'draft': draft_data})

            if request.method == 'DELETE':
                cursor.execute(
                    "DELETE FROM team_drafts WHERE user_id = %s AND event_id = %s",
                    (current_user_id, event_id),
                )
                conn.commit()
                cursor.close()
                return jsonify({'success': True, 'message': '草稿已删除'})

            data = request.get_json() or {}

            def _norm(keys, default=None, strip=True):
                if isinstance(keys, (list, tuple)):
                    for k in keys:
                        if k in data:
                            v = data.get(k)
                            if strip and isinstance(v, str):
                                v = v.strip()
                            return v
                else:
                    if keys in data:
                        v = data.get(keys)
                        if strip and isinstance(v, str):
                            v = v.strip()
                        return v
                return default

            team_name = _norm(['team_name', 'teamName'])
            team_type = _norm(['team_type', 'teamType'], strip=False)
            team_address = _norm(['team_address', 'teamAddress'])
            team_description = _norm(['team_description', 'teamDescription'])
            leader_name = _norm(['leader_name', 'leaderName'])
            leader_position = _norm(['leader_position', 'leaderPosition'], default='领队')
            leader_phone = _norm(['leader_phone', 'leaderPhone'])
            leader_email = _norm(['leader_email', 'leaderEmail'])
            client_team_key = _norm(['client_team_key', 'clientTeamKey'], strip=False)

            now = datetime.now()

            cursor.execute(
                "SELECT draft_id FROM team_drafts WHERE user_id = %s AND event_id = %s",
                (current_user_id, event_id),
            )
            row = cursor.fetchone()

            if row:
                cursor.execute(
                    """
                    UPDATE team_drafts
                    SET team_name = %s,
                        team_type = %s,
                        team_address = %s,
                        team_description = %s,
                        leader_name = %s,
                        leader_position = %s,
                        leader_phone = %s,
                        leader_email = %s,
                        client_team_key = %s,
                        updated_at = %s
                    WHERE draft_id = %s
                    """,
                    (
                        team_name,
                        team_type,
                        team_address,
                        team_description,
                        leader_name,
                        leader_position,
                        leader_phone,
                        leader_email,
                        client_team_key,
                        now,
                        row['draft_id'],
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO team_drafts (
                        user_id, event_id, team_name, team_type, team_address, team_description,
                        leader_name, leader_position, leader_phone, leader_email,
                        client_team_key, is_submitted, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        current_user_id,
                        event_id,
                        team_name,
                        team_type,
                        team_address,
                        team_description,
                        leader_name,
                        leader_position,
                        leader_phone,
                        leader_email,
                        client_team_key,
                        False,
                        now,
                        now,
                    ),
                )

            conn.commit()
            cursor.close()
            return jsonify({'success': True, 'message': '草稿已保存'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'}), 500
