from flask import jsonify, session, current_app
import os
import shutil

from utils.decorators import log_action, handle_db_errors
from . import maintenance_bp, log_maintenance_operation


@maintenance_bp.route('/admin/maintenance/cleanup', methods=['POST'])
@log_action('系统文件清理')
@handle_db_errors
def api_maintenance_cleanup():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if session.get('user_role') not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': '权限不足，只有管理员可以执行系统文件清理操作'}), 403

    try:
        backup_dir = os.path.join(current_app.root_path, 'backups')
        cleaned_files = 0
        freed_bytes = 0

        # 仅在备份目录存在时进行清理
        if os.path.exists(backup_dir):
            backups = []
            for file in os.listdir(backup_dir):
                if file.endswith('.sql'):
                    file_path = os.path.join(backup_dir, file)
                    try:
                        stat = os.stat(file_path)
                        backups.append((file_path, stat.st_mtime, stat.st_size))
                    except OSError:
                        continue

            # 按修改时间从新到旧排序
            backups.sort(key=lambda x: x[1], reverse=True)

            # 保留最近 10 个备份，其余删除
            for file_path, _, size in backups[10:]:
                try:
                    os.remove(file_path)
                    cleaned_files += 1
                    freed_bytes += size
                except OSError:
                    continue

        freed_mb = freed_bytes / (1024 * 1024) if freed_bytes > 0 else 0.0

        # 记录维护日志
        log_maintenance_operation(
            session.get('user_id'),
            'file_cleanup',
            f'系统文件清理完成，删除 {cleaned_files} 个备份文件，释放 {freed_mb:.2f} MB 空间',
            status='success',
            file_size=freed_mb,
        )

        return jsonify({
            'success': True,
            'message': '系统文件清理完成',
            'cleaned_files': cleaned_files,
            'freed_space': f'{freed_mb:.2f} MB',
            'data': {
                'cleaned_files': cleaned_files,
                'freed_space_mb': freed_mb,
            },
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        log_maintenance_operation(
            session.get('user_id'),
            'file_cleanup',
            '系统文件清理失败',
            status='failed',
            error_msg=str(e),
        )

        return jsonify({
            'success': False,
            'message': f'系统文件清理失败: {str(e)}',
        }), 500
