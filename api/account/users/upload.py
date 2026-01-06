from flask import request, jsonify, session, current_app
import os
from uuid import uuid4

from utils.decorators import log_action

from . import users_bp


ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@users_bp.route('/upload', methods=['POST'])
@log_action('上传文件')
def api_upload_file():
    """通用文件上传接口，仅支持图片文件。"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '请先登录'}), 401

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未找到上传文件'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    if not _allowed_file(file.filename):
        return jsonify({'success': False, 'message': '不支持的文件类型'}), 400

    original_name = file.filename
    _, ext = os.path.splitext(original_name)
    ext = ext.lower()

    upload_dir = os.path.join(current_app.root_path, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    unique_name = f"{uuid4().hex}{ext}"
    save_path = os.path.join(upload_dir, unique_name)

    try:
        file.save(save_path)
    except Exception as e:
        return jsonify({'success': False, 'message': f'保存文件失败: {e}'}), 500

    return jsonify({
        'success': True,
        'message': '文件上传成功',
        'data': {
            'filename': unique_name,
            'original_name': original_name,
            # 这里只返回相对路径，具体访问方式由前端或其他下载接口决定
            'path': f'uploads/{unique_name}',
        },
    })
