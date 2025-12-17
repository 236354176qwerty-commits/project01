import os
from io import BytesIO

from flask import jsonify, session, send_file

from database import DatabaseManager

from . import announcements_bp


@announcements_bp.route('/announcements/<int:announcement_id>/download')
def download_announcement_file(announcement_id):
    """下载公告附件"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT file_path, file_name, file_type, file_content, view_count
                FROM announcements 
                WHERE id = %s AND is_active = TRUE
                """,
                (announcement_id,),
            )

            announcement = cursor.fetchone()

            if not announcement:
                return jsonify({'success': False, 'message': '公告不存在'}), 404

            # 如果存在 BLOB 内容，则优先从数据库返回
            file_content = announcement.get('file_content')
            file_name = announcement.get('file_name') or 'attachment'
            file_type = announcement.get('file_type') or ''

            # 更新浏览次数
            cursor.execute(
                """
                UPDATE announcements 
                SET view_count = view_count + 1 
                WHERE id = %s
                """,
                (announcement_id,),
            )
            conn.commit()

            if file_content:
                # 根据扩展名简单推断 MIME 类型
                ext = (file_type or '').lower()
                mimetype = 'application/octet-stream'
                if ext in ['.pdf']:
                    mimetype = 'application/pdf'
                elif ext in ['.jpg', '.jpeg']:
                    mimetype = 'image/jpeg'
                elif ext in ['.png']:
                    mimetype = 'image/png'
                elif ext in ['.doc', '.docx']:
                    mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif ext in ['.xls', '.xlsx']:
                    mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

                return send_file(
                    BytesIO(file_content),
                    mimetype=mimetype,
                    as_attachment=True,
                    download_name=file_name,
                )

            # 否则回退到旧的文件路径逻辑（兼容历史数据）
            if not announcement['file_path'] or not os.path.exists(announcement['file_path']):
                return jsonify({'success': False, 'message': '文件不存在'}), 404

            return send_file(
                announcement['file_path'],
                as_attachment=True,
                download_name=announcement['file_name'],
            )

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
