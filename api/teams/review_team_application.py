from flask import request, jsonify, session
from datetime import datetime
import json

from database import DatabaseManager

from . import teams_bp


@teams_bp.route('/team_applications/<int:application_id>/review', methods=['POST'])
def api_review_team_application(application_id):
    """审核队伍申请（队长/管理员将状态更新为approved或rejected）"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    data = request.get_json() or {}
    new_status = (data.get('status') or '').strip()
    if new_status not in ['approved', 'rejected']:
        return jsonify({'success': False, 'message': '无效的状态'}), 400

    current_user_id = session.get('user_id')
    user_role = session.get('user_role')

    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT ta.*, t.created_by AS team_owner_id, e.name AS event_name
                FROM team_applications ta
                LEFT JOIN teams t ON ta.team_id = t.team_id
                LEFT JOIN events e ON ta.event_id = e.event_id
                WHERE ta.application_id = %s
                """,
                (application_id,),
            )
            app_row = cursor.fetchone()
            if not app_row:
                cursor.close()
                return jsonify({'success': False, 'message': '申请不存在'}), 404

            is_admin = user_role in ['admin', 'super_admin']
            is_owner = app_row.get('team_owner_id') == current_user_id
            if not (is_admin or is_owner):
                cursor.close()
                return jsonify({'success': False, 'message': '您没有权限审核此申请'}), 403

            old_status = app_row.get('status')
            now = datetime.now()
            if old_status != new_status:
                cursor.execute(
                    "UPDATE team_applications SET status = %s, updated_at = %s WHERE application_id = %s",
                    (new_status, now, application_id),
                )
                conn.commit()
                app_row['status'] = new_status
                app_row['updated_at'] = now

            # 审核通过时，写入 team_players 并确保 participants 有记录
            if app_row.get('status') == 'approved' and (app_row.get('type') or 'player') == 'player':
                event_id = app_row.get('event_id')
                team_id = app_row.get('team_id')
                user_id = app_row.get('user_id')
                real_name = app_row.get('applicant_name')
                phone = app_row.get('applicant_phone')
                id_card = app_row.get('applicant_id_card')
                competition_event = app_row.get('competition_event')

                # 兜底：若无 user_id，尝试用手机号或身份证匹配 users
                if not user_id:
                    try:
                        cursor.execute("SELECT user_id FROM users WHERE phone = %s", (phone,))
                        row = cursor.fetchone()
                        if row:
                            user_id = row.get('user_id')
                        elif id_card:
                            cursor.execute("SELECT user_id FROM users WHERE username = %s OR real_name = %s", (id_card, id_card))
                            row2 = cursor.fetchone()
                            if row2:
                                user_id = row2.get('user_id')
                    except Exception:
                        pass

                # upsert 到 team_players（按 event_id, team_id, id_card 唯一约束）
                import json as _json
                selected_events_raw = app_row.get('selected_events')
                selected_events_json = None
                if selected_events_raw is not None:
                    try:
                        if isinstance(selected_events_raw, str):
                            try:
                                parsed = _json.loads(selected_events_raw)
                                if isinstance(parsed, list):
                                    selected_events_json = _json.dumps(parsed, ensure_ascii=False)
                                else:
                                    selected_events_json = _json.dumps([str(parsed)], ensure_ascii=False)
                            except Exception:
                                text = selected_events_raw.strip()
                                if '、' in text:
                                    selected_events_json = _json.dumps([s.strip() for s in text.split('、') if s.strip()], ensure_ascii=False)
                                elif ',' in text:
                                    selected_events_json = _json.dumps([s.strip() for s in text.split(',') if s.strip()], ensure_ascii=False)
                                elif text:
                                    selected_events_json = _json.dumps([text], ensure_ascii=False)
                        elif isinstance(selected_events_raw, list):
                            selected_events_json = _json.dumps(selected_events_raw, ensure_ascii=False)
                    except Exception:
                        selected_events_json = None

                cursor.execute(
                    """
                    SELECT player_id FROM team_players
                    WHERE event_id = %s AND team_id = %s AND id_card = %s
                    """,
                    (event_id, team_id, id_card or phone),
                )
                exists = cursor.fetchone()
                if exists:
                    cursor.execute(
                        """
                        UPDATE team_players
                        SET user_id = %s,
                            name = %s,
                            phone = %s,
                            id_card = %s,
                            competition_event = %s,
                            selected_events = %s,
                            status = 'registered',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE player_id = %s
                        """,
                        (
                            user_id,
                            real_name,
                            phone,
                            id_card or phone,
                            competition_event,
                            selected_events_json,
                            exists['player_id'],
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO team_players (
                            event_id, team_id, user_id,
                            name, gender, age, phone, id_card,
                            competition_event, selected_events,
                            level, registration_number,
                            pair_partner_name, pair_registered, team_registered, status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            event_id,
                            team_id,
                            user_id,
                            real_name,
                            None,
                            None,
                            phone,
                            id_card or phone,
                            competition_event,
                            selected_events_json,
                            None,
                            id_card or phone,
                            None,
                            False,
                            False,
                            'registered',
                        ),
                    )

                # 确保 participants 有记录（参赛者列表页来源）
                if user_id and event_id:
                    try:
                        db_manager.ensure_participant_with_conn(
                            conn,
                            event_id=event_id,
                            user_id=user_id,
                            registration_number=id_card or phone,
                            category=competition_event or '个人项目',
                            participant_status='registered',
                            event_participant_status='registered',
                            team_id=team_id,
                            registered_at=now,
                        )
                    except Exception:
                        pass

                conn.commit()

            cursor.close()

        selected_events_raw = app_row.get('selected_events')
        selected_events_parsed = []
        if selected_events_raw:
            if isinstance(selected_events_raw, str):
                try:
                    parsed = json.loads(selected_events_raw)
                    if isinstance(parsed, list):
                        selected_events_parsed = parsed
                    else:
                        selected_events_parsed = [str(parsed)]
                except Exception:
                    text = selected_events_raw.strip()
                    if '、' in text:
                        selected_events_parsed = [s.strip() for s in text.split('、') if s.strip()]
                    elif ',' in text:
                        selected_events_parsed = [s.strip() for s in text.split(',') if s.strip()]
                    elif text:
                        selected_events_parsed = [text]
            elif isinstance(selected_events_raw, list):
                selected_events_parsed = selected_events_raw

        application = {
            'id': app_row['application_id'],
            'teamId': app_row.get('team_id'),
            'eventId': app_row.get('event_id'),
            'userId': app_row.get('user_id'),
            'applicantName': app_row.get('applicant_name'),
            'applicantPhone': app_row.get('applicant_phone'),
            'applicantIdCard': app_row.get('applicant_id_card'),
            'teamName': app_row.get('team_name'),
            'eventName': app_row.get('event_name'),
            'status': app_row.get('status'),
            'type': app_row.get('type'),
            'role': app_row.get('role'),
            'position': app_row.get('position'),
            'selectedEvents': selected_events_parsed,
            'submittedAt': app_row['submitted_at'].isoformat() if app_row.get('submitted_at') else None,
            'appliedAt': app_row['submitted_at'].isoformat() if app_row.get('submitted_at') else None,
            'updatedAt': app_row['updated_at'].isoformat() if app_row.get('updated_at') else None,
        }

        return jsonify({'success': True, 'application': application})

    except Exception as e:
        return jsonify({'success': False, 'message': f'更新申请状态失败: {str(e)}'}), 500
