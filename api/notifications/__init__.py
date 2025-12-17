from flask import Blueprint

notifications_bp = Blueprint('notifications', __name__)

# 每个具体路由实现在本包下的独立模块中
from . import (
    send_notification,
    get_sent_notifications,
    get_my_notifications,
    mark_notification_read,
    mark_all_read,
    get_notification_detail,
    get_unread_notification_count,
)

__all__ = ['notifications_bp']
