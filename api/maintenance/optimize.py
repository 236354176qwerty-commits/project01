from flask import jsonify, session
import time

from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors
from . import maintenance_bp, log_maintenance_operation


@maintenance_bp.route('/admin/maintenance/optimize', methods=['POST'])
@log_action('执行数据库优化')
@handle_db_errors
def api_maintenance_optimize():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以执行数据库优化操作'}), 403

    start_time = time.time()

    try:
        db_manager = DatabaseManager()
        optimized_count = 0

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SHOW TABLES')
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                try:
                    cursor.execute(f'OPTIMIZE TABLE {table}')
                    optimized_count += 1
                except Exception:
                    continue

        duration = time.time() - start_time

        log_maintenance_operation(
            session.get('user_id'),
            'database_optimize',
            f'数据库优化完成，成功优化 {optimized_count}/{len(tables)} 张表',
            status='success',
            duration=duration,
        )

        return jsonify({
            'success': True,
            'message': f'数据库优化完成，成功优化 {optimized_count}/{len(tables)} 张表，耗时 {duration:.1f} 秒',
            'data': {
                'optimized_tables': optimized_count,
                'total_tables': len(tables),
                'duration_seconds': duration,
            },
        })

    except Exception as e:
        duration = time.time() - start_time
        import traceback
        traceback.print_exc()

        log_maintenance_operation(
            session.get('user_id'),
            'database_optimize',
            '数据库优化失败',
            status='failed',
            error_msg=str(e),
            duration=duration,
        )

        return jsonify({
            'success': False,
            'message': f'数据库优化失败：{str(e)}',
        }), 500
