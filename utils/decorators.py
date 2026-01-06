#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武术赛事管理系统 - 装饰器（权限控制等）
"""

from functools import wraps
from flask import session, redirect, url_for, flash, jsonify, request, current_app
import logging

logger = logging.getLogger(__name__)

_simple_cache = {}

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.is_json:
                return jsonify({'error': '请先登录', 'code': 401}), 401
            flash('请先登录后再访问该页面', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_roles):
    """角色权限验证装饰器
    
    Args:
        required_roles: 字符串或列表，指定需要的角色
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                if request.is_json:
                    return jsonify({'error': '请先登录', 'code': 401}), 401
                flash('请先登录后再访问该页面', 'warning')
                return redirect(url_for('login'))
            
            user_role = session.get('user_role')
            
            # 确保 required_roles 是列表
            if isinstance(required_roles, str):
                roles = [required_roles]
            else:
                roles = required_roles
            
            # 直接检查用户角色是否在所需角色列表中
            if user_role not in roles:
                if request.is_json:
                    return jsonify({'error': '权限不足', 'code': 403}), 403
                flash('您没有权限访问该页面', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission):
    """权限验证装饰器
    
    Args:
        permission: 需要的权限名称
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                if request.is_json:
                    return jsonify({'error': '请先登录', 'code': 401}), 401
                return redirect(url_for('login'))
            
            user_role = session.get('user_role')
            role_permissions = current_app.config.get('ROLE_PERMISSIONS', {})
            user_permissions = role_permissions.get(user_role, [])
            
            if permission not in user_permissions:
                if request.is_json:
                    return jsonify({'error': '权限不足', 'code': 403}), 403
                flash('您没有权限执行该操作', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """管理员权限装饰器（管理员及以上）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return role_required(['admin', 'super_admin'])(f)(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """超级管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return role_required(['super_admin'])(f)(*args, **kwargs)
    return decorated_function

def judge_required(f):
    """裁判权限装饰器（裁判及以上）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return role_required(['judge', 'admin', 'super_admin'])(f)(*args, **kwargs)
    return decorated_function

def api_key_required(f):
    """API密钥验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': '缺少API密钥', 'code': 401}), 401
        
        # 这里可以添加API密钥验证逻辑
        valid_api_keys = current_app.config.get('VALID_API_KEYS', [])
        
        if api_key not in valid_api_keys:
            return jsonify({'error': 'API密钥无效', 'code': 401}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def rate_limit(max_requests=100, per_seconds=3600):
    """请求频率限制装饰器
    
    Args:
        max_requests: 最大请求次数
        per_seconds: 时间窗口（秒）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 这里可以实现基于Redis或内存的频率限制
            # 简单示例，实际应用中需要更完善的实现
            
            client_ip = request.remote_addr
            current_time = int(time.time())
            
            # 这里应该使用Redis或其他持久化存储
            # 暂时跳过频率限制检查
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_json(required_fields=None):
    """JSON数据验证装饰器
    
    Args:
        required_fields: 必需的字段列表
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': '请求必须是JSON格式', 'code': 400}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'JSON数据为空', 'code': 400}), 400
            
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in data or data[field] is None or data[field] == '':
                        missing_fields.append(field)
                
                if missing_fields:
                    # 提供更友好的字段名称映射
                    field_names = {
                        'username': '账号',
                        'password': '密码',
                        'confirmPassword': '确认密码',
                        'nickname': '用户昵称',
                        'phone': '手机号',
                        'captcha': '验证码'
                    }
                    
                    friendly_names = [field_names.get(field, field) for field in missing_fields]
                    return jsonify({
                        'success': False,
                        'message': f'请填写: {", ".join(friendly_names)}',
                        'code': 400
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_action(action_name):
    """操作日志装饰器
    
    Args:
        action_name: 操作名称
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            user_name = session.get('user_name', 'Unknown')
            
            # 记录操作开始
            start_time = time.perf_counter()
            logger.info(f"用户 {user_name}(ID:{user_id}) 开始执行操作: {action_name}")
            
            try:
                result = f(*args, **kwargs)
                
                duration_ms = (time.perf_counter() - start_time) * 1000
                # 记录操作成功
                logger.info(
                    f"用户 {user_name}(ID:{user_id}) 成功完成操作: {action_name}, 耗时: {duration_ms:.1f} ms"
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                # 记录操作失败
                logger.error(
                    f"用户 {user_name}(ID:{user_id}) 执行操作失败: {action_name}, 耗时: {duration_ms:.1f} ms, 错误: {str(e)}"
                )
                raise
                
        return decorated_function
    return decorator

def cache_result(timeout=300):
    """结果缓存装饰器
    
    Args:
        timeout: 缓存超时时间（秒）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 这里可以实现基于Redis或Flask-Caching的缓存
            # 简单示例，实际应用中需要更完善的实现
            
            # 生成缓存键
            try:
                key_base = f"{f.__name__}:{request.path}:{sorted(request.args.items())}"
                user_id = session.get('user_id')
                user_role = session.get('user_role')
                cache_key = f"{key_base}:{user_id}:{user_role}"
            except Exception:
                cache_key = f"{f.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 这里应该检查缓存并返回缓存结果
            # 如果没有缓存，执行函数并缓存结果
            now = time.time()
            entry = _simple_cache.get(cache_key)
            if entry:
                expires_at, value = entry
                if now < expires_at:
                    return value

            result = f(*args, **kwargs)
            _simple_cache[cache_key] = (now + timeout, result)
            return result
        return decorated_function
    return decorator

def handle_db_errors(f):
    """数据库错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"数据库操作错误: {str(e)}")
            
            if request.is_json:
                return jsonify({
                    'error': '数据库操作失败，请稍后重试',
                    'code': 500
                }), 500
            else:
                flash('操作失败，请稍后重试', 'error')
                return redirect(request.referrer or url_for('dashboard'))
                
    return decorated_function

def validate_event_access(f):
    """验证用户是否有访问特定赛事的权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        event_id = kwargs.get('event_id') or request.args.get('event_id') or request.json.get('event_id')
        
        if not event_id:
            if request.is_json:
                return jsonify({'error': '缺少赛事ID', 'code': 400}), 400
            flash('缺少赛事信息', 'error')
            return redirect(url_for('events'))
        
        user_role = session.get('user_role')
        user_id = session.get('user_id')
        
        # 超级管理员和管理员可以访问所有赛事
        if user_role in ['super_admin', 'admin']:
            return f(*args, **kwargs)
        
        # 这里可以添加更复杂的权限检查逻辑
        # 例如检查用户是否是该赛事的创建者或被授权的裁判
        
        return f(*args, **kwargs)
    return decorated_function

import time
