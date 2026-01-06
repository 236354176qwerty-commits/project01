from flask import jsonify, session, current_app
import os
from datetime import datetime

from config import Config
from database import DatabaseManager
from utils.decorators import log_action, handle_db_errors
from . import maintenance_bp


@maintenance_bp.route('/admin/maintenance/stats', methods=['GET'])
@log_action('查看维护统计信息')
@handle_db_errors
def api_maintenance_stats():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以查看维护统计信息'}), 403

    db_manager = DatabaseManager()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT ROUND(SUM(data_length + index_length)/1024/1024,2) AS size_mb
            FROM information_schema.tables 
            WHERE table_schema=%s
            """,
            (Config.DB_NAME,),
        )
        db_size = cursor.fetchone()

        cursor.execute('SELECT role, COUNT(*) AS count FROM users GROUP BY role')
        users = cursor.fetchall()

        cursor.execute('SELECT status, COUNT(*) AS count FROM events GROUP BY status')
        events = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) AS total FROM event_participants WHERE role = 'athlete'")
        participants = cursor.fetchone()
        if not participants or participants['total'] == 0:
            cursor.execute('SELECT COUNT(*) AS total FROM participants')
            participants = cursor.fetchone()

        backup_dir = os.path.join(current_app.root_path, 'backups')
        last_backup = None
        if os.path.exists(backup_dir):
            backups = [f for f in os.listdir(backup_dir) if f.endswith('.sql')]
            if backups:
                latest = max(backups, key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)))
                mtime = os.path.getmtime(os.path.join(backup_dir, latest))
                last_backup = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

    stats = {
        'db_size': db_size['size_mb'] if db_size else 0,
        'users': users,
        'events': events,
        'participants': participants['total'] if participants else 0,
        'last_backup': last_backup,
    }

    return jsonify({
        'success': True,
        'stats': stats,
        'data': stats,
    })
