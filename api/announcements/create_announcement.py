import os

from flask import request, jsonify, session
from werkzeug.utils import secure_filename

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import announcements_bp


@announcements_bp.route('/announcements', methods=['POST'])
@log_action('创建公告')
@handle_db_errors
def create_announcement():
    """创建公告（仅超级管理员）"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') != 'super_admin':
        return jsonify({'success': False, 'message': '只有超级管理员可以管理公告'}), 403

    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()

    if not title:
        return jsonify({'success': False, 'message': '标题为必填项'}), 400

    # 文件元信息
    file_path = None  # 兼容旧字段，未来可逐步废弃
    file_name = None
    file_size = 0
    file_type = None
    # 使用十六进制字符串 + UNHEX 写入，避免字符集导致的 Invalid utf8mb4 错误
    file_content_hex = None  # 数据库存储仍为 BLOB，只是传参时用 hex 字符串

    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            # 统一使用安全文件名和扩展名信息
            filename = secure_filename(file.filename)
            file_ext = os.path.splitext(filename)[1]

            # 读取整个文件内容到内存，转为十六进制字符串，通过 UNHEX 写入 BLOB 字段
            file_bytes = file.read()
            if file_bytes:
                file_content_hex = file_bytes.hex()
                file_name = filename
                file_size = len(file_bytes)
                file_type = file_ext

            # 如果你希望在过渡期同时保留磁盘文件，可以在此处继续调用 file.save()
            # 当前实现不再写入 uploads/announcements 目录

    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO announcements (
                title,
                content,
                file_path,
                file_name,
                file_size,
                file_type,
                file_content,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, UNHEX(%s), %s)
            """,
            (
                title,
                content,
                file_path,
                file_name,
                file_size,
                file_type,
                file_content_hex,
                session.get('user_id'),
            ),
        )

        announcement_id = cursor.lastrowid
        conn.commit()

    announcement_data = {
        'id': announcement_id,
        'title': title,
        'file_name': file_name,
        'file_size': file_size,
        'file_type': file_type,
        'has_file': bool(file_content_hex),
    }

    return jsonify({
        'success': True,
        'message': '公告创建成功',
        'data': announcement_data,
        'announcement': announcement_data,
    })
