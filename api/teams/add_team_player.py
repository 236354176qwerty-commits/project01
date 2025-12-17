from flask import request, jsonify, session
from datetime import datetime
import json

from database import DatabaseManager

from . import teams_bp


@teams_bp.route('/team/<int:team_id>/players', methods=['POST'])
def api_add_team_player(team_id):
    """为指定队伍添加选手 - 只有领队或管理员可以添加"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')
    user_role = session.get('user_role')

    try:
        data = request.get_json() or {}
        event_id = data.get('event_id')
        real_name = (data.get('real_name') or data.get('name') or '').strip()
        id_card = (data.get('registration_number') or data.get('id_card') or '').strip()
        phone = (data.get('phone') or '').strip()
        competition_event = (data.get('competition_event') or '').strip()
        selected_events = data.get('selected_events')

        raw_gender = (data.get('gender') or '').strip()
        raw_age = data.get('age')

        def normalize_gender(value):
            if not value:
                return None
            value = str(value).strip()
            mapping = {
                'male': '男',
                'm': '男',
                '男': '男',
                'female': '女',
                'f': '女',
                '女': '女'
            }
            return mapping.get(value.lower(), value)

        def extract_gender_from_id(card):
            if not card or len(card) != 18:
                return None
            try:
                return '男' if int(card[-2]) % 2 == 1 else '女'
            except Exception:
                return None

        def calculate_age_from_id(card):
            if not card or len(card) != 18:
                return None
            try:
                birth_year = int(card[6:10])
                birth_month = int(card[10:12])
                birth_day = int(card[12:14])
                today = datetime.now()
                age_value = today.year - birth_year
                if (today.month, today.day) < (birth_month, birth_day):
                    age_value -= 1
                if 0 <= age_value <= 150:
                    return age_value
            except Exception:
                return None
            return None

        def calculate_age_group(age_value):
            if age_value is None:
                return None
            if age_value < 12:
                return '儿童组'
            if 12 <= age_value <= 17:
                return '少年组'
            if 18 <= age_value <= 39:
                return '青年组'
            if 40 <= age_value <= 59:
                return '中年组'
            return '老年组'

        gender_value = normalize_gender(raw_gender) or extract_gender_from_id(id_card)

        age_value = None
        if raw_age not in (None, ''):
            try:
                age_value = int(raw_age)
            except (TypeError, ValueError):
                age_value = None
        if age_value is None:
            age_value = calculate_age_from_id(id_card)

        age_group_value = calculate_age_group(age_value) if age_value is not None else None

        if not event_id or not real_name or not id_card or not phone:
            return jsonify({
                'success': False,
                'message': 'event_id、姓名、身份证号和手机号为必填项'
            }), 400

        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM teams WHERE team_id = %s", (team_id,))
            team = cursor.fetchone()
            if not team:
                cursor.close()
                return jsonify({'success': False, 'message': '队伍不存在'}), 404

            if int(team['event_id']) != int(event_id):
                cursor.close()
                return jsonify({'success': False, 'message': '赛事ID与队伍不匹配'}), 400

            is_admin = user_role in ['admin', 'super_admin']
            is_creator = team.get('created_by') == current_user_id
            if not (is_admin or is_creator):
                cursor.close()
                return jsonify({'success': False, 'message': '您没有权限为该队伍添加选手'}), 403

            try:
                user = db_manager.get_user_by_phone(phone)
            except Exception:
                user = None

            user_created = False
            auto_password = None

            if not user:
                from models import User, UserRole, UserStatus

                username = phone
                existing = None
                try:
                    existing = db_manager.get_user_by_username(username)
                except Exception:
                    existing = None
                if existing:
                    cursor.close()
                    return jsonify({'success': False, 'message': f'用户名{username}已存在'}), 400

                password = id_card[-6:] if len(id_card) >= 6 else phone[-6:]
                auto_password = password
                user_created = True

                new_user = User(
                    username=username,
                    password=password,
                    real_name=real_name,
                    nickname=real_name,
                    phone=phone,
                    email=None,
                    role=UserRole.USER,
                    status=UserStatus.NORMAL,
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                user = db_manager.create_user(new_user)

            user_id = user.user_id

            cursor = conn.cursor()
            selected_events_json = None
            if selected_events is not None:
                try:
                    selected_events_json = json.dumps(selected_events, ensure_ascii=False)
                except Exception:
                    selected_events_json = None

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
                    gender_value,
                    age_value,
                    phone,
                    id_card,
                    competition_event,
                    selected_events_json,
                    data.get('level'),
                    id_card,
                    None,
                    False,
                    False,
                    data.get('status', 'registered'),
                ),
            )
            player_id = cursor.lastrowid
            # 确保 participants 有记录
            try:
                db_manager.ensure_participant_with_conn(
                    conn,
                    event_id=event_id,
                    user_id=user_id,
                    registration_number=id_card or phone,
                    category=competition_event or '个人项目',
                    participant_status='registered',
                    event_participant_status=data.get('status', 'registered'),
                    gender=gender_value,
                    age_group=age_group_value,
                    team_id=team_id,
                )
            except Exception:
                # 不影响主流程
                pass

            conn.commit()
            cursor.close()

        response = {
            'success': True,
            'message': '选手添加成功',
            'player': {
                'player_id': player_id,
                'event_id': int(event_id),
                'team_id': team_id,
                'user_id': user_id,
                'name': real_name,
                'phone': phone,
                'id_card': id_card,
                'gender': gender_value,
                'age': age_value,
                'competition_event': competition_event,
                'selected_events': selected_events,
                'status': data.get('status', 'registered'),
            },
            'user_created': user_created,
        }

        if user_created and auto_password:
            response['auto_registration_info'] = {
                'username': user.username,
                'password': auto_password,
            }

        return jsonify(response)

    except Exception as e:
        return jsonify({'success': False, 'message': f'添加选手失败: {str(e)}'}), 500
