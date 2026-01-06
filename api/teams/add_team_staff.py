from flask import request, jsonify, session
from datetime import datetime

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import teams_bp


@teams_bp.route('/team/<int:team_id>/staff', methods=['POST'])
@log_action('为队伍添加随队人员')
@handle_db_errors
def api_add_team_staff(team_id):
    """为指定队伍添加随行人员/教练/医务人员 - 只有领队或管理员可以添加"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')
    user_role = session.get('user_role')

    data = request.get_json() or {}
    event_id = data.get('event_id')
    name = (data.get('name') or '').strip()
    position = (data.get('position') or '').strip() or None
    phone = (data.get('phone') or '').strip() or None
    id_card = (data.get('id_card') or data.get('idCard') or '').strip() or None
    gender = (data.get('gender') or '').strip() or None
    age = data.get('age')

    if not event_id or not name:
        return jsonify({
            'success': False,
            'message': 'event_id 和 姓名 为必填项'
        }), 400

    if age not in (None, ''):
        try:
            age = int(age)
        except (TypeError, ValueError):
            age = None

    db_manager = DatabaseManager()
    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM teams WHERE team_id = %s", (team_id,))
        team = cursor.fetchone()
        if not team:
            cursor.close()
            return jsonify({'success': False, 'message': '队伍不存在'}), 404

        if int(team.get('event_id')) != int(event_id):
            cursor.close()
            return jsonify({'success': False, 'message': '赛事ID与队伍不匹配'}), 400

        is_admin = user_role in ['admin', 'super_admin']
        is_creator = team.get('created_by') == current_user_id
        if not (is_admin or is_creator):
            cursor.close()
            return jsonify({'success': False, 'message': '您没有权限为此队伍添加随行人员'}, 403)

        now = datetime.now()

        try:
            cursor.execute(
                """
                INSERT INTO team_staff (
                    event_id, team_id, user_id, name, gender, age,
                    position, phone, id_card, status, source, client_staff_key,
                    created_by, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', 'direct', %s, %s, %s, %s)
                """,
                (
                    event_id,
                    team_id,
                    current_user_id,
                    name,
                    gender,
                    age,
                    position,
                    phone,
                    id_card,
                    f"staff_{event_id}_{team_id}_{id_card or name}_{int(now.timestamp())}",
                    current_user_id,
                    now,
                    now,
                ),
            )
            staff_id = cursor.lastrowid
            conn.commit()
        except Exception as e:
            message = str(e)
            cursor.close()
            if '1062' in message and 'uniq_staff_identity' in message:
                return jsonify({
                    'success': False,
                    'message': '该身份证号已在当前赛事本队登记为随队人员，不能重复添加'
                }), 400
            raise
        else:
            cursor.close()

    staff_data = {
        'staff_id': staff_id,
        'event_id': int(event_id),
        'team_id': int(team_id),
        'name': name,
        'gender': gender,
        'age': age,
        'position': position,
        'phone': phone,
        'id_card': id_card,
        'status': 'active',
    }

    return jsonify({
        'success': True,
        'data': staff_data,
        'staff': staff_data,
    })
