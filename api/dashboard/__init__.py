from flask import Blueprint


dashboard_bp = Blueprint('dashboard', __name__)
# 兼容 system_bp 命名，用于系统聚合
system_bp = dashboard_bp

# 将具体路由实现拆分到独立模块中
from . import (
    dashboard_statistics,
    system_statistics,
    my_schedule,
)

__all__ = ['dashboard_bp', 'system_bp']
