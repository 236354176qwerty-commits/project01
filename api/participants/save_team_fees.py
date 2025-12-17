from flask import request, jsonify, session
from datetime import datetime

from database import DatabaseManager

from . import participants_bp


@participants_bp.route('/participants/team-fees', methods=['POST'])
def api_save_team_fees():
    """保存或更新队伍费用统计到 team_applications 表"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    data = request.get_json() or {}

    event_id = data.get('event_id') or data.get('eventId')
    team_name = (data.get('team_name') or data.get('teamName') or '').strip()

    fees = data.get('fees') or {}
    try:
        individual_fee = float(fees.get('individualFee') or 0)
        pair_fee = float(fees.get('pairPracticeFee') or 0)
        team_fee = float(fees.get('teamCompetitionFee') or 0)
        other_fee = float(fees.get('otherFee') or 0)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': '费用格式无效'}), 400

    total_fee = float(fees.get('totalFee') or (individual_fee + pair_fee + team_fee + other_fee))

    if not event_id or not team_name:
        return jsonify({'success': False, 'message': 'event_id 和 team_name 为必填项'}), 400

    try:
        event_id_int = int(event_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'event_id 无效'}), 400

    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            # 尝试查找现有记录（同一赛事下按队名唯一）
            cursor.execute(
                """
                SELECT application_id
                FROM team_applications
                WHERE event_id = %s AND team_name = %s
                LIMIT 1
                """,
                (event_id_int, team_name),
            )
            row = cursor.fetchone()

            now = datetime.now()

            if row:
                # 更新已有记录
                cursor.execute(
                    """
                    UPDATE team_applications
                    SET 
                        individual_fee = %s,
                        pair_practice_fee = %s,
                        team_competition_fee = %s,
                        other_fee = %s,
                        total_fee = %s,
                        status = CASE WHEN status IN ('pending', 'approved') THEN status ELSE 'pending' END,
                        updated_at = %s
                    WHERE application_id = %s
                    """,
                    (
                        individual_fee,
                        pair_fee,
                        team_fee,
                        other_fee,
                        total_fee,
                        now,
                        row['application_id'],
                    ),
                )
            else:
                # 插入新记录（简化：只保存与费用相关的核心字段）
                cursor.execute(
                    """
                    INSERT INTO team_applications (
                        event_id,
                        team_id,
                        user_id,
                        applicant_name,
                        applicant_phone,
                        applicant_id_card,
                        type,
                        role,
                        team_name,
                        event_name,
                        status,
                        submitted_by,
                        submitted_at,
                        individual_fee,
                        pair_practice_fee,
                        team_competition_fee,
                        other_fee,
                        total_fee,
                        created_at,
                        updated_at
                    ) VALUES (%s, NULL, %s, NULL, NULL, NULL, 'player', NULL, %s, NULL, 'pending', %s, %s,
                              %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event_id_int,
                        session.get('user_id'),
                        team_name,
                        session.get('user_name') or session.get('username') or '',
                        now,
                        individual_fee,
                        pair_fee,
                        team_fee,
                        other_fee,
                        total_fee,
                        now,
                        now,
                    ),
                )

            conn.commit()
            cursor.close()

        return jsonify({'success': True, 'message': '队伍费用已同步到云端'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'保存队伍费用失败: {str(e)}'}), 500
