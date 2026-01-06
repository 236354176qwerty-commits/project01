from flask import request, jsonify, session

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import players_bp


@players_bp.route('/players', methods=['POST'])
@log_action('添加参赛选手')
@handle_db_errors
def api_add_player():
    """添加参赛选手API - 自动创建用户并处理报名"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    from datetime import datetime
    from models import User, UserRole, UserStatus

    data = request.get_json()
    print(f"收到选手报名数据: {data}")
    real_name = data.get('real_name', '').strip()
    phone = data.get('phone', '').strip()
    id_card = data.get('registration_number', '').strip()
    event_id = data.get('event_id')
    competition_event = data.get('competition_event', '').strip()
    team_id = data.get('team_id')
    selected_events = data.get('selected_events')

    if not all([real_name, phone, id_card, event_id, competition_event]):
        return jsonify({
            'success': False,
            'message': '姓名、手机号、身份证号、赛事ID和项目为必填项'
        }), 400

    if len(id_card) != 18:
        return jsonify({
            'success': False,
            'message': '身份证号码必须为18位'
        }), 400

    def calculate_gender_from_id_card(id_card):
        try:
            gender_digit = int(id_card[16])
            return 'male' if gender_digit % 2 == 1 else 'female'
        except Exception:
            return None

    def calculate_age_from_id_card(id_card):
        try:
            birth_year = int(id_card[6:10])
            birth_month = int(id_card[10:12])
            birth_day = int(id_card[12:14])

            today = datetime.now()
            age = today.year - birth_year

            if (today.month, today.day) < (birth_month, birth_day):
                age -= 1

            return age if 0 <= age <= 150 else None
        except Exception:
            return None

    gender = calculate_gender_from_id_card(id_card)
    age = calculate_age_from_id_card(id_card)

    db_manager = DatabaseManager()

    user = db_manager.get_user_by_phone(phone)
    user_created = False
    auto_password = None

    if not user:
        print(f"用户不存在，创建新用户: {real_name}, {phone}")

        username = phone

        existing_user = db_manager.get_user_by_username(username)
        if existing_user:
            return jsonify({
                'success': False,
                'message': f'用户名{username}已存在'
            }), 400

        password = id_card[-6:]
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
        print(f"创建用户成功: ID={user.user_id}, username={user.username}")
    else:
        print(f"找到已有用户: ID={user.user_id}, username={user.username}")

    if team_id:
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)

                cursor.execute("SELECT * FROM teams WHERE team_id = %s", (team_id,))
                team = cursor.fetchone()

                if team and int(team.get('event_id')) == int(event_id):
                    import json
                    selected_events_json = None
                    if selected_events is not None:
                        try:
                            if isinstance(selected_events, str):
                                try:
                                    parsed = json.loads(selected_events)
                                    if isinstance(parsed, list):
                                        selected_events = parsed
                                except Exception:
                                    pass
                            if isinstance(selected_events, list):
                                selected_events_json = json.dumps(selected_events, ensure_ascii=False)
                        except Exception:
                            selected_events_json = None

                    cursor.execute(
                        """
                        SELECT player_id FROM team_players
                        WHERE event_id = %s AND team_id = %s AND id_card = %s
                        """,
                        (event_id, team_id, id_card),
                    )
                    existing_player = cursor.fetchone()

                    if existing_player:
                        cursor.execute(
                            """
                            UPDATE team_players
                            SET user_id = %s,
                                name = %s,
                                gender = %s,
                                age = %s,
                                phone = %s,
                                competition_event = %s,
                                selected_events = %s,
                                status = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE player_id = %s
                            """,
                            (
                                user.user_id,
                                real_name,
                                gender,
                                age,
                                phone,
                                competition_event,
                                selected_events_json,
                                'registered',
                                existing_player['player_id'],
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
                                user.user_id,
                                real_name,
                                gender,
                                age,
                                phone,
                                id_card,
                                competition_event,
                                selected_events_json,
                                None,
                                id_card,
                                None,
                                False,
                                False,
                                'registered',
                            ),
                        )
                    conn.commit()
        except Exception as e:
            print(f'同步到 team_players 失败: {e}')

    response_data = {
        'success': True,
        'message': '选手添加成功',
        'user': {
            'user_id': user.user_id,
            'username': user.username,
            'real_name': user.real_name or real_name,
            'phone': phone,
        },
        'application': {
            'applicantName': real_name,
            'applicantPhone': phone,
            'applicantIdCard': id_card,
            'phone': phone,
            'idCard': id_card,
            'gender': gender,
            'age': age,
            'competitionEvent': competition_event,
            'eventId': event_id,
            'userId': user.user_id,
            'status': 'approved',
            'appliedAt': datetime.now().isoformat(),
            'approvedAt': datetime.now().isoformat(),
        },
        'user_created': user_created,
        'auto_registration_info': {
            'username': phone,
            'password': auto_password,
        } if user_created else None,
    }

    response_data['data'] = {
        'user': response_data['user'],
        'application': response_data['application'],
        'user_created': response_data['user_created'],
        'auto_registration_info': response_data['auto_registration_info'],
    }

    print(f"返回数据: {response_data}")
    return jsonify(response_data)
