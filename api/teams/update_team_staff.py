from flask import request, jsonify, session

from database import DatabaseManager

from . import teams_bp


@teams_bp.route('/team/<int:team_id>/staff/<int:staff_id>', methods=['PUT'])
def api_update_team_staff(team_id, staff_id):
    """更新队伍随队人员信息（姓名、职务、联系方式、证件号等）- 仅领队或管理员"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    current_user_id = session.get('user_id')
    user_role = session.get('user_role')

    try:
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
                return jsonify({'success': False, 'message': '您没有权限修改此队伍的随队人员信息'}), 403

            cursor.execute(
                "SELECT * FROM team_staff WHERE team_id = %s AND staff_id = %s",
                (team_id, staff_id),
            )
            staff = cursor.fetchone()
            if not staff:
                cursor.close()
                return jsonify({'success': False, 'message': '随队人员不存在'}), 404

            fields = []
            params = []

            if 'name' in data:
                fields.append("name = %s")
                params.append(data.get('name'))

            if 'position' in data:
                fields.append("position = %s")
                params.append(data.get('position'))

            if 'phone' in data:
                fields.append("phone = %s")
                params.append(data.get('phone'))

            if 'id_card' in data or 'idCard' in data:
                fields.append("id_card = %s")
                params.append(data.get('id_card') or data.get('idCard'))

            if 'gender' in data:
                fields.append("gender = %s")
                params.append(data.get('gender'))

            if 'age' in data:
                fields.append("age = %s")
                params.append(data.get('age'))

            if 'status' in data:
                fields.append("status = %s")
                params.append(data.get('status'))

            if not fields:
                cursor.close()
                return jsonify({'success': False, 'message': '没有需要更新的字段'}), 400

            params.append(team_id)
            params.append(staff_id)

            sql = f"""
                UPDATE team_staff
                SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE team_id = %s AND staff_id = %s
            """
            try:
                cursor.execute(sql, tuple(params))
                conn.commit()
            except Exception as e:
                message = str(e)
                # 唯一键冲突（同一赛事+队伍+身份证号），给出友好提示
                if '1062' in message and 'uniq_staff_identity' in message:
                    cursor.close()
                    return jsonify({
                        'success': False,
                        'message': '该身份证号已在当前赛事本队登记为随队人员，不能重复使用'
                    }), 400
                cursor.close()
                return jsonify({'success': False, 'message': f'更新随队人员信息失败: {message}'}), 500

            cursor.close()

        return jsonify({'success': True, 'message': '随队人员信息更新成功'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'更新随队人员信息失败: {str(e)}'}), 500
