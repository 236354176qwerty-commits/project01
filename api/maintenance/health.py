from flask import jsonify, session, current_app
import os
import shutil
from datetime import datetime

from database import DatabaseManager
from . import maintenance_bp


@maintenance_bp.route('/admin/maintenance/health', methods=['GET'])
def api_system_health():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以查看系统健康状态'}), 403

    try:
        health_status = {}

        try:
            db_manager = DatabaseManager()
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                cursor.fetchone()
            health_status['database'] = {
                'status': 'healthy',
                'message': '数据库连接正常',
            }
        except Exception as e:
            health_status['database'] = {
                'status': 'error',
                'message': f'数据库连接异常: {str(e)}',
            }

        try:
            total, used, free = shutil.disk_usage(os.path.abspath(os.getcwd()))
            free_gb = free / (1024**3)
            percent_used = (used / total) * 100

            if free_gb < 1:
                status = 'critical'
                message = f'磁盘可用空间小于 1GB，当前约 {free_gb:.2f} GB'
            elif free_gb < 5:
                status = 'warning'
                message = f'磁盘可用空间不足 5GB，当前约 {free_gb:.2f} GB'
            else:
                status = 'healthy'
                message = f'磁盘可用空间充足，当前约 {free_gb:.2f} GB'

            health_status['disk'] = {
                'status': status,
                'message': message,
                'free_space': f'{free_gb:.2f} GB',
                'used_percent': f'{percent_used:.1f}%',
            }
        except Exception as e:
            health_status['disk'] = {
                'status': 'unknown',
                'message': f'磁盘空间检查失败: {str(e)}',
            }

        try:
            backup_dir = os.path.join(current_app.root_path, 'backups')
            backups = [
                f
                for f in os.listdir(backup_dir)
                if os.path.isfile(os.path.join(backup_dir, f)) and f.endswith('.sql')
            ] if os.path.exists(backup_dir) else []

            if backups:
                latest = max(backups, key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)))
                mtime = os.path.getmtime(os.path.join(backup_dir, latest))
                last_backup_time = datetime.fromtimestamp(mtime)
                hours_ago = (datetime.now() - last_backup_time).total_seconds() / 3600

                if hours_ago > 48:
                    status = 'warning'
                    message = '最近一次备份在 48 小时之前，请尽快执行新的备份'
                elif hours_ago > 24:
                    status = 'info'
                    message = '最近一次备份在 24 小时之前，建议关注备份计划'
                else:
                    status = 'healthy'
                    message = '最近备份时间在 24 小时内'

                health_status['backup'] = {
                    'status': status,
                    'message': message,
                    'last_backup': last_backup_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'backup_count': len(backups),
                }
            else:
                health_status['backup'] = {
                    'status': 'warning',
                    'message': '未找到任何备份文件，请尽快执行一次数据库备份',
                    'last_backup': None,
                    'backup_count': 0,
                }
        except Exception as e:
            health_status['backup'] = {
                'status': 'error',
                'message': f'备份状态检查失败: {str(e)}',
            }

        try:
            db_manager = DatabaseManager()
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SHOW TABLES')
                tables = cursor.fetchall()
                table_count = len(tables)

            health_status['tables'] = {
                'status': 'healthy' if table_count > 0 else 'warning',
                'message': f'当前数据库中共有 {table_count} 张表' if table_count > 0 else '数据库中未发现任何表',
                'table_count': table_count,
            }
        except Exception as e:
            health_status['tables'] = {
                'status': 'error',
                'message': f'数据表状态检查失败: {str(e)}',
            }

        statuses = [h.get('status') for h in health_status.values()]
        if any(s == 'critical' for s in statuses):
            overall_status = 'critical'
        elif any(s == 'error' for s in statuses):
            overall_status = 'error'
        elif any(s == 'warning' for s in statuses):
            overall_status = 'warning'
        else:
            overall_status = 'healthy'

        return jsonify({
            'success': True,
            'overall_status': overall_status,
            'health': health_status,
            'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'系统健康检查失败: {str(e)}',
        }), 500
