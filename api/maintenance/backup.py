from flask import jsonify, session, current_app
import os
import subprocess
import time
from datetime import datetime

from config import Config
from . import maintenance_bp, log_maintenance_operation, check_mysqldump_available


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
