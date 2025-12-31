from flask import jsonify, session, send_file, current_app
import os
from datetime import datetime

from . import maintenance_bp, log_maintenance_operation


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


@maintenance_bp.route('/admin/maintenance/backups/<filename>', methods=['DELETE'])
def api_delete_backup(filename):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以删除备份文件'}), 403

    try:
        if not filename.endswith('.sql'):
            return jsonify({'success': False, 'message': '无效的备份文件名'}), 400

        # 简单防止路径穿越
        if '/' in filename or '\\' in filename:
            return jsonify({'success': False, 'message': '非法的备份文件路径'}), 400

        backup_dir = os.path.join(current_app.root_path, 'backups')
        file_path = os.path.join(backup_dir, filename)

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '备份文件不存在'}), 404

        file_size = os.path.getsize(file_path) / (1024 * 1024)

        os.remove(file_path)

        log_maintenance_operation(
            session.get('user_id'),
            'backup_delete',
            f'删除备份文件: {filename}',
            status='success',
            file_size=file_size,
        )

        return jsonify({
            'success': True,
            'message': '备份文件删除成功',
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        log_maintenance_operation(
            session.get('user_id'),
            'backup_delete',
            f'删除备份文件失败: {filename}',
            status='failed',
            error_msg=str(e),
        )

        return jsonify({
            'success': False,
            'message': f'删除备份文件失败: {str(e)}',
        }), 500
