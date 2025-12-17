from flask import Blueprint

announcements_bp = Blueprint('announcements', __name__)

# 每个具体路由实现在本包下的独立模块中
from . import (
    get_announcements,
    create_announcement,
    delete_announcement,
    download_announcement_file,
)

__all__ = ['announcements_bp']
