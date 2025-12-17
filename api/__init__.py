#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武术赛事管理系统 - API接口模块
"""

from .account.auth import auth_bp
from .events import events_bp
from .scoring import scoring_bp
from .categories import categories_bp

__version__ = '1.0.0'
__author__ = '武术赛事管理团队'

# 导出所有蓝图
__all__ = ['auth_bp', 'events_bp', 'scoring_bp', 'categories_bp']
