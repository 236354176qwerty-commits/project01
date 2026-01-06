from flask import jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import teams_bp


def _strip_pair_tokens_with_partner(competition_event: str, partner_name: str) -> tuple[str, bool]:
    if not competition_event or not partner_name:
        return competition_event or '', False
    tokens = [t.strip() for t in (competition_event or '').split('、') if t.strip()]
    marker_cn = f'（{partner_name}）'
    marker_en = f'({partner_name})'

    def is_pair_token(tok: str) -> bool:
        if not tok:
            return False
        return ('对练' in tok) or tok.startswith('徒手') or tok.startswith('器械') or tok.startswith('对练')

    kept = []
    changed = False
    for tok in tokens:
        if (marker_cn in tok or marker_en in tok) and is_pair_token(tok):
            changed = True
            continue
        kept.append(tok)
    return '、'.join(kept), changed


def _has_any_pair_tokens(competition_event: str) -> bool:
    if not competition_event:
        return False
    tokens = [t.strip() for t in competition_event.split('、') if t.strip()]
    for tok in tokens:
        if ('对练' in tok) or tok.startswith('徒手') or tok.startswith('器械') or tok.startswith('对练'):
            return True
    return False


@teams_bp.route('/team/<int:team_id>/players/<int:player_id>', methods=['DELETE'])
@log_action('删除队伍选手')
@handle_db_errors
def api_delete_team_player(team_id, player_id):
    """删除指定队伍的选手 - 只有领队或管理员可以删除"""
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
            return jsonify({'success': False, 'message': '您没有权限删除此队伍的选手'}), 403

        cursor.execute(
            "SELECT * FROM team_players WHERE team_id = %s AND player_id = %s",
            (team_id, player_id),
        )
        player = cursor.fetchone()

        if not player:
            cursor.close()
            return jsonify({'success': False, 'message': '选手不存在'}), 404

        deleted_name = (player.get('name') or '').strip()
        event_id = player.get('event_id')

        # 删除该队员之前，先清理同队伍中其他队员的对练项目中引用到该队员的条目
        if deleted_name and event_id:
            cursor.execute(
                """
                SELECT player_id, competition_event, pair_partner_name, pair_registered
                FROM team_players
                WHERE team_id = %s AND event_id = %s AND player_id <> %s
                  AND competition_event LIKE %s
                """,
                # 只要包含姓名就先取出来，避免括号类型不一致导致漏匹配
                (team_id, event_id, player_id, f"%{deleted_name}%"),
            )
            affected = cursor.fetchall() or []
            for other in affected:
                old_text = other.get('competition_event') or ''
                new_text, changed = _strip_pair_tokens_with_partner(old_text, deleted_name)
                if not changed:
                    continue

                has_pair = _has_any_pair_tokens(new_text)
                new_pair_registered = 1 if has_pair else 0
                new_pair_partner = other.get('pair_partner_name')
                if not has_pair:
                    new_pair_partner = None

                cursor.execute(
                    """
                    UPDATE team_players
                    SET competition_event = %s,
                        pair_registered = %s,
                        pair_partner_name = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE team_id = %s AND event_id = %s AND player_id = %s
                    """,
                    (new_text, new_pair_registered, new_pair_partner, team_id, event_id, other.get('player_id')),
                )

        cursor.execute(
            "DELETE FROM team_players WHERE team_id = %s AND player_id = %s",
            (team_id, player_id),
        )
        conn.commit()
        cursor.close()

    return jsonify({
        'success': True,
        'message': '选手删除成功',
    })
