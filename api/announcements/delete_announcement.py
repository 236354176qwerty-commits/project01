import os

from flask import jsonify, session

from database import DatabaseManager

from . import announcements_bp


@announcements_bp.route('/announcements/<int:announcement_id>', methods=['DELETE'])
def delete_announcement(announcement_id):
    """删除公告（仅超级管理员）"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') != 'super_admin':
        return jsonify({'success': False, 'message': '只有超级管理员可以删除公告'}), 403

    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT file_path FROM announcements 
                WHERE id = %s AND is_active = TRUE
                """,
                (announcement_id,),
            )

            announcement = cursor.fetchone()

            if not announcement:
                return jsonify({'success': False, 'message': '公告不存在'}), 404

            cursor.execute(
                """
                UPDATE announcements 
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = %s
                """,
                (announcement_id,),
            )

            conn.commit()

            # 如需物理删除文件，可取消下面代码注释
            # if announcement['file_path'] and os.path.exists(announcement['file_path']):
            #     os.remove(announcement['file_path'])

            return jsonify({'success': True, 'message': '公告删除成功'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
