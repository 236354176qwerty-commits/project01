from flask import request, jsonify

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors

from . import announcements_bp


@announcements_bp.route('/announcements', methods=['GET'])
@log_action('获取公告列表')
@handle_db_errors
def get_announcements():
    """获取公告列表（分页）"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT COUNT(*) as total 
            FROM announcements 
            WHERE is_active = TRUE
            """
        )
        total = cursor.fetchone()['total']

        offset = (page - 1) * per_page

        # 注意：不要在列表接口中选择 BLOB 字段 file_content，避免 jsonify 无法序列化
        cursor.execute(
            """
            SELECT 
                a.id,
                a.title,
                a.content,
                a.file_path,
                a.file_name,
                a.file_size,
                a.file_type,
                a.created_by,
                a.created_at,
                a.updated_at,
                a.is_active,
                a.view_count,
                u.real_name AS creator_name
            FROM announcements a
            LEFT JOIN users u ON a.created_by = u.user_id
            WHERE a.is_active = TRUE
            ORDER BY a.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (per_page, offset),
        )

        announcements = cursor.fetchall()

        total_pages = (total + per_page - 1) // per_page

        return jsonify(
            {
                'success': True,
                'data': announcements,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total': total,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1,
                },
            }
        )
