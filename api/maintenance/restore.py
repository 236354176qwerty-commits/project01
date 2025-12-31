from flask import request, jsonify, session, current_app
import os
import subprocess
import time

from config import Config
from . import maintenance_bp, log_maintenance_operation


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
