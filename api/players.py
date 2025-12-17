from flask import Blueprint, request, jsonify, session

from database import DatabaseManager


players_bp = Blueprint('players', __name__)


@players_bp.route('/players', methods=['GET'])
def api_get_players():
    """获取参赛选手列表API"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        print("=== 获取参赛选手列表流程开始 ===")
        print(f"当前 session: {session}")
        print(f"查询参数: {request.args}")

        db_manager = DatabaseManager()

        # 获取筛选条件
        event_id = request.args.get('event_id')
        participant_id = request.args.get('participant_id')

        print(f"赛事ID: {event_id}, 选手ID: {participant_id}")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            # 如果指定了赛事，则校验赛事存在
            if event_id:
                cursor.execute('SELECT * FROM events WHERE event_id = %s', (event_id,))
                event = cursor.fetchone()
                if not event:
                    print(f"赛事ID {event_id} 不存在")
                    return jsonify({
                        'success': False,
                        'message': f'赛事ID {event_id} 不存在'
                    }), 404

            # 构建查询SQL
            query = '''
                SELECT 
                    p.participant_id,
                    p.event_id,
                    p.user_id,
                    p.registration_number,
                    p.event_member_no,
                    p.category,
                    p.weight_class,
                    p.status,
                    p.notes,
                    p.registered_at,
                    u.real_name,
                    u.phone,
                    u.email,
                    e.name as event_name
                FROM participants p
                JOIN users u ON p.user_id = u.user_id
                JOIN events e ON p.event_id = e.event_id
            '''

            params = []
            conditions = []

            if event_id:
                conditions.append('p.event_id = %s')
                params.append(event_id)

            if participant_id:
                conditions.append('p.participant_id = %s')
                params.append(participant_id)

            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)

            query += ' ORDER BY p.registered_at DESC'

            print(f"最终SQL: {query}")
            print(f"参数: {params}")

            cursor.execute(query, tuple(params) if params else None)
            players = cursor.fetchall()

            print(f"查询到 {len(players)} 条记录")

            # 序列化为 JSON 结构
            players_list = []
            for player in players:
                players_list.append({
                    'participant_id': player['participant_id'],
                    'event_id': player['event_id'],
                    'user_id': player['user_id'],
                    'registration_number': player['registration_number'],
                    'category': player['category'],
                    'weight_class': player['weight_class'],
                    'status': player['status'],
                    'notes': player['notes'],
                    'registered_at': player['registered_at'].isoformat() if player['registered_at'] else None,
                    'real_name': player['real_name'],
                    'phone': player['phone'],
                    'email': player['email'],
                    'event_name': player['event_name']
                })

            print("=== 获取参赛选手列表流程结束 ===")
            return jsonify({
                'success': True,
                'data': players_list
            })

    except Exception as e:
        print(f'获取参赛选手列表时发生错误: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取参赛选手信息失败: {str(e)}',
            'debug': str(e)
        }), 500


@players_bp.route('/players/<int:participant_id>', methods=['PUT'])
def api_update_player(participant_id):
    """更新参赛选手信息API"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        data = request.get_json()
        db_manager = DatabaseManager()

        # 构建更新SQL
        fields = {}

        if 'category' in data:
            fields['category'] = data['category']

        if 'weight_class' in data:
            fields['weight_class'] = data['weight_class']

        if 'status' in data:
            fields['status'] = data['status']

        if 'notes' in data:
            fields['notes'] = data['notes']

        if not fields:
            return jsonify({'success': False, 'message': '没有需要更新的字段'}), 400

        db_manager.update_participant_fields(participant_id, fields)

        return jsonify({
            'success': True,
            'message': '更新成功'
        })

    except Exception as e:
        print(f'更新参赛选手时发生错误: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500


@players_bp.route('/players/<int:participant_id>', methods=['DELETE'])
def api_delete_player(participant_id):
    """删除参赛选手API"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        db_manager = DatabaseManager()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # 先查出 event_id 和 user_id，用于同步删除 event_participants
            cursor.execute(
                'SELECT event_id, user_id FROM participants WHERE participant_id = %s',
                (participant_id,),
            )
            row = cursor.fetchone()

            if row is not None:
                event_id, user_id = row
                cursor.execute(
                    'DELETE FROM event_participants WHERE event_id = %s AND user_id = %s',
                    (event_id, user_id),
                )

            # 删除选手记录
            query = 'DELETE FROM participants WHERE participant_id = %s'
            cursor.execute(query, (participant_id,))
            conn.commit()

            return jsonify({
                'success': True,
                'message': '删除成功'
            })

    except Exception as e:
        print(f'删除参赛选手时发生错误: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500


@players_bp.route('/players', methods=['POST'])
def api_add_player():
    """添加参赛选手API - 自动创建用户并处理报名"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        from datetime import datetime
        from models import User, UserRole, UserStatus

        data = request.get_json()
        print(f"收到选手报名数据: {data}")

        # 提取基本信息
        real_name = data.get('real_name', '').strip()
        phone = data.get('phone', '').strip()
        id_card = data.get('registration_number', '').strip()
        event_id = data.get('event_id')
        competition_event = data.get('competition_event', '').strip()
        team_id = data.get('team_id')
        selected_events = data.get('selected_events')

        # 必填项校验
        if not all([real_name, phone, id_card, event_id, competition_event]):
            return jsonify({
                'success': False,
                'message': '姓名、手机号、身份证号、赛事ID和项目为必填项'
            }), 400

        # 身份证长度校验
        if len(id_card) != 18:
            return jsonify({
                'success': False,
                'message': '身份证号码必须为18位'
            }), 400

        # 根据身份证解析性别和年龄
        def calculate_gender_from_id_card(id_card):
            """根据身份证第17位奇偶性计算性别"""
            try:
                gender_digit = int(id_card[16])
                return 'male' if gender_digit % 2 == 1 else 'female'
            except Exception:
                return None

        def calculate_age_from_id_card(id_card):
            """根据身份证出生日期计算年龄"""
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

        # 1. 尝试根据手机号查找已有用户
        user = db_manager.get_user_by_phone(phone)
        user_created = False
        auto_password = None

        if not user:
            # 2. 用户不存在，则创建新用户
            print(f"用户不存在，创建新用户: {real_name}, {phone}")

            username = phone

            existing_user = db_manager.get_user_by_username(username)
            if existing_user:
                return jsonify({
                    'success': False,
                    'message': f'用户名{username}已存在'
                }), 400

            # 默认密码取身份证后6位
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
                updated_at=datetime.now()
            )

            user = db_manager.create_user(new_user)
            print(f"创建用户成功: ID={user.user_id}, username={user.username}")
        else:
            print(f"找到已有用户: ID={user.user_id}, username={user.username}")

        # 2. 如有队伍信息，则同步到 team_players
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
                            (event_id, team_id, id_card)
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
                                    existing_player['player_id']
                                )
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
                                    'registered'
                                )
                            )
                        conn.commit()
            except Exception as e:
                print(f'同步到 team_players 失败: {e}')

        # 3. 构造返回给前端的用户与报名信息
        response_data = {
            'success': True,
            'message': '选手添加成功',
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'real_name': user.real_name or real_name,
                'phone': phone
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
                'approvedAt': datetime.now().isoformat()
            },
            'user_created': user_created,
            'auto_registration_info': {
                'username': phone,
                'password': auto_password
            } if user_created else None
        }

        print(f"返回数据: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        print(f'添加参赛选手时发生错误: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'添加失败: {str(e)}'
        }), 500
