from flask import jsonify, session

from database import DatabaseManager
from . import maintenance_bp


@maintenance_bp.route('/admin/maintenance/logs', methods=['GET'])
def api_maintenance_logs():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以查看维护日志'}), 403

    try:
        db_manager = DatabaseManager()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT 
                    ml.id,
                    ml.operation,
                    ml.details,
                    ml.status,
                    ml.error_message,
                    ml.ip_address,
                    ml.file_size,
                    ml.duration,
                    ml.created_at,
                    u.username,
                    u.real_name
                FROM maintenance_logs ml
                LEFT JOIN users u ON ml.user_id = u.user_id
                ORDER BY ml.created_at DESC
                LIMIT 100
                """
            )
            logs = cursor.fetchall()

            for log in logs:
                if log.get('created_at'):
                    log['created_at'] = log['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                if log.get('file_size') is not None:
                    log['file_size'] = f"{log['file_size']:.2f}"
                if log.get('duration') is not None:
                    log['duration'] = f"{log['duration']:.2f}"

        return jsonify({
            'success': True,
            'logs': logs,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取维护日志失败: {str(e)}',
        }), 500
