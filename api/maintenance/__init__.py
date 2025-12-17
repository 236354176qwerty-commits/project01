from flask import Blueprint, request, jsonify, session, send_file, current_app
import os
import subprocess
import time
import shutil
from datetime import datetime

from config import Config
from database import DatabaseManager


maintenance_bp = Blueprint('maintenance', __name__)


def log_maintenance_operation(user_id, operation, details, status='success', error_msg=None, file_size=None, duration=None):
    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO maintenance_logs 
                (user_id, operation, details, status, error_message, ip_address, file_size, duration, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (user_id, operation, details, status, error_msg, request.remote_addr, file_size, duration),
            )
            conn.commit()
    except Exception:
        pass


def get_maintenance_mode():
    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT config_value FROM system_config 
                WHERE config_key = 'maintenance_mode'
                """
            )
            result = cursor.fetchone()
            cursor.close()
            return result[0] == '1' if result else False
    except Exception:
        return False


def set_maintenance_mode(enabled, user_id):
    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE system_config 
                SET config_value = %s, updated_by = %s, updated_at = NOW()
                WHERE config_key = 'maintenance_mode'
                """,
                ('1' if enabled else '0', user_id),
            )
            conn.commit()
            cursor.close()
            return True
    except Exception:
        return False


def check_mysqldump_available():
    try:
        subprocess.run(['mysqldump', '--version'], capture_output=True, check=True, timeout=5)
        return True
    except Exception:
        return False


@maintenance_bp.route('/admin/maintenance/backup', methods=['POST'])
def api_maintenance_backup():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以执行数据库备份操作'}), 403

    start_time = time.time()

    try:
        if not check_mysqldump_available():
            log_maintenance_operation(
                session.get('user_id'),
                'database_backup',
                '数据库备份失败：mysqldump 不可用或未安装',
                status='failed',
                error_msg='mysqldump 不可用或未安装',
            )
            return jsonify({
                'success': False,
                'message': '数据库备份失败：mysqldump 不可用或未安装，请检查服务器环境配置',
            }), 500

        backup_dir = os.path.join(current_app.root_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'wushu_backup_{timestamp}.sql')

        cmd = [
            'mysqldump',
            f'-h{Config.DB_HOST}',
            f'-P{Config.DB_PORT}',
            f'-u{Config.DB_USER}',
            f'-p{Config.DB_PASSWORD}',
            '--single-transaction',
            '--quick',
            '--lock-tables=false',
            Config.DB_NAME,
        ]

        with open(backup_file, 'w', encoding='utf8') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, timeout=300)

        if result.returncode != 0:
            raise Exception(result.stderr or 'mysqldump 执行失败')

        file_size = os.path.getsize(backup_file) / (1024 * 1024)
        duration = time.time() - start_time

        log_maintenance_operation(
            session.get('user_id'),
            'database_backup',
            f'数据库备份成功：{os.path.basename(backup_file)}',
            status='success',
            file_size=file_size,
            duration=duration,
        )

        return jsonify({
            'success': True,
            'message': f'数据库备份成功，文件大小约 {file_size:.2f} MB，耗时 {duration:.1f} 秒',
        })

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        log_maintenance_operation(
            session.get('user_id'),
            'database_backup',
            '数据库备份超时',
            status='failed',
            error_msg='数据库备份超时',
            duration=duration,
        )
        return jsonify({
            'success': False,
            'message': '数据库备份超时，请稍后重试或检查服务器负载',
        }), 500


@maintenance_bp.route('/admin/maintenance/optimize', methods=['POST'])
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


@maintenance_bp.route('/admin/maintenance/stats', methods=['GET'])
def api_maintenance_stats():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以查看维护统计信息'}), 403

    try:
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

            # 优先基于 event_participants 统计参赛记录总数（仅统计 role='athlete'）
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

        return jsonify({
            'success': True,
            'stats': {
                'db_size': db_size['size_mb'] if db_size else 0,
                'users': users,
                'events': events,
                'participants': participants['total'] if participants else 0,
                'last_backup': last_backup,
            },
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取维护统计信息失败: {str(e)}',
        }), 500


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


@maintenance_bp.route('/admin/maintenance/backups', methods=['GET'])
def api_list_backups():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以查看备份列表'}), 403

    try:
        backup_dir = os.path.join(current_app.root_path, 'backups')
        backups = []

        if os.path.exists(backup_dir):
            for file in os.listdir(backup_dir):
                if file.endswith('.sql'):
                    file_path = os.path.join(backup_dir, file)
                    stat = os.stat(file_path)
                    backups.append({
                        'filename': file,
                        'size': f'{stat.st_size / (1024*1024):.2f} MB',
                        'size_bytes': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'timestamp': stat.st_mtime,
                    })

        backups.sort(key=lambda x: x['timestamp'], reverse=True)

        return jsonify({
            'success': True,
            'backups': backups,
            'total': len(backups),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取备份列表失败: {str(e)}',
        }), 500


@maintenance_bp.route('/admin/maintenance/backups/<filename>/download', methods=['GET'])
def api_download_backup(filename):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以下载备份'}), 403

    try:
        if not filename.endswith('.sql'):
            return jsonify({'success': False, 'message': '无效的备份文件名'}), 400

        backup_dir = os.path.join(current_app.root_path, 'backups')
        file_path = os.path.join(backup_dir, filename)

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '备份文件不存在'}), 404

        log_maintenance_operation(
            session.get('user_id'),
            'backup_download',
            f'下载备份文件: {filename}',
            status='success',
        )

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/sql',
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'下载备份文件失败: {str(e)}',
        }), 500


@maintenance_bp.route('/admin/maintenance/restore', methods=['POST'])
def api_restore_backup():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') != 'super_admin':
        return jsonify({'success': False, 'message': '只有超级管理员可以执行数据库还原操作'}), 403

    start_time = time.time()

    try:
        data = request.get_json() or {}
        filename = data.get('filename') or ''
        confirm_code = data.get('confirm_code', '')

        if not filename:
            return jsonify({'success': False, 'message': '请选择要还原的备份文件'}), 400

        if confirm_code != 'RESTORE':
            log_maintenance_operation(
                session.get('user_id'),
                'database_restore',
                f'数据库还原确认码错误，文件名: {filename}',
                status='failed',
                error_msg='确认码不正确，应输入 "RESTORE"',
            )
            return jsonify({'success': False, 'message': '确认码错误，请输入 "RESTORE" 以确认执行还原操作'}), 400

        if not filename.endswith('.sql'):
            return jsonify({'success': False, 'message': '无效的备份文件名'}), 400

        backup_dir = os.path.join(current_app.root_path, 'backups')
        backup_path = os.path.join(backup_dir, filename)

        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'message': '备份文件不存在'}), 404

        file_size = os.path.getsize(backup_path) / (1024 * 1024)

        cmd = [
            'mysql',
            f'-h{Config.DB_HOST}',
            f'-P{Config.DB_PORT}',
            f'-u{Config.DB_USER}',
            f'-p{Config.DB_PASSWORD}',
            Config.DB_NAME,
        ]

        with open(backup_path, 'r', encoding='utf8') as f:
            result = subprocess.run(
                cmd,
                stdin=f,
                stderr=subprocess.PIPE,
                text=True,
                timeout=600,
            )

        if result.returncode != 0:
            raise Exception(result.stderr or 'mysql 执行失败')

        duration = time.time() - start_time

        log_maintenance_operation(
            session.get('user_id'),
            'database_restore',
            f'数据库还原成功：{filename}',
            status='success',
            file_size=file_size,
            duration=duration,
        )

        return jsonify({
            'success': True,
            'message': f'数据库还原成功，耗时 {duration:.1f} 秒，备份文件大小约 {file_size:.2f} MB',
        })

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        log_maintenance_operation(
            session.get('user_id'),
            'database_restore',
            '数据库还原超时',
            status='failed',
            error_msg='数据库还原超时',
            duration=duration,
        )
        return jsonify({
            'success': False,
            'message': '数据库还原超时，请稍后重试或检查服务器负载',
        }), 500

    except Exception as e:
        duration = time.time() - start_time
        import traceback
        traceback.print_exc()

        log_maintenance_operation(
            session.get('user_id'),
            'database_restore',
            '数据库还原失败',
            status='failed',
            error_msg=str(e),
            duration=duration,
        )

        return jsonify({
            'success': False,
            'message': f'数据库还原失败：{str(e)}',
        }), 500


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


@maintenance_bp.route('/admin/maintenance/mode', methods=['GET'])
def api_get_maintenance_mode_api():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以查看维护模式状态'}), 403

    try:
        is_maintenance = get_maintenance_mode()
        return jsonify({
            'success': True,
            'maintenance_mode': is_maintenance,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取维护模式状态失败: {str(e)}',
        }), 500


@maintenance_bp.route('/admin/maintenance/mode/toggle', methods=['POST'])
def api_toggle_maintenance_mode_api():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以切换维护模式'}), 403

    try:
        current_mode = get_maintenance_mode()
        new_mode = not current_mode

        user_id = session.get('user_id')
        if not set_maintenance_mode(new_mode, user_id):
            return jsonify({
                'success': False,
                'message': '更新维护模式失败',
            }), 500

        return jsonify({
            'success': True,
            'maintenance_mode': new_mode,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'切换维护模式失败: {str(e)}',
        }), 500
