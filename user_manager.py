#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武术赛事管理系统 - 用户管理模块 (MySQL数据库版本)
"""

from datetime import datetime
from models import User, UserRole, UserStatus
from database import DatabaseManager
from utils.helpers import generate_password_hash, verify_password
import re

class UserManager:
    """用户管理器 - 使用MySQL数据库存储"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def _verify_user_password(self, user, password):
        matched = False
        if getattr(user, 'password_hash', None):
            try:
                if verify_password(password, user.password_hash):
                    matched = True
            except Exception:
                matched = False
        if (not matched) and user.password == password:
            matched = True
            try:
                self.db_manager.update_user_password(user.user_id, password)
            except Exception:
                pass
        return matched

    def init_database(self):
        """初始化数据库"""
        try:
            self.db_manager.init_database()
        except Exception as e:
            print(f"数据库初始化失败: {e}")
    
    
    def register_user(self, username, password, real_name, email, phone, team_name=None):
        """注册新用户"""
        try:
            # 检查用户名是否已存在
            existing_user = self.db_manager.get_user_by_username(username)
            if existing_user:
                return False, "用户名已存在"
            
            # 检查邮箱是否已存在（通过查询所有用户）
            all_users = self.db_manager.get_all_users()
            for user in all_users:
                if user.email == email:
                    return False, "邮箱已被注册"
                if user.phone == phone:
                    return False, "手机号已被注册"
            
            # 创建新用户
            new_user = User(
                username=username,
                real_name=real_name or team_name,  # 如果没有真实姓名，使用队名
                email=email,
                phone=phone,
                role=UserRole.USER,  # 默认为普通用户
                created_at=datetime.now(),
                updated_at=datetime.now(),
                is_active=True,
                password=password  # 设置明文密码
            )
            
            # 保存到数据库
            created_user = self.db_manager.create_user(new_user)
            return True, "注册成功"
            
        except Exception as e:
            return False, f"注册失败: {str(e)}"
    
    def authenticate_user(self, username_or_phone, password):
        """验证用户登录（支持用户名或手机号登录）"""
        try:
            print(f"\n[调试] 尝试登录: {username_or_phone}")
            result = self.db_manager.get_user_for_login(username_or_phone)
            
            # 检查用户是否存在
            if not result:
                print(f"[调试] 用户不存在: {username_or_phone}")
                return None, "用户不存在"
            
            # 处理单个用户或多个用户的情况
            users_to_check = [result] if not isinstance(result, list) else result
            
            print(f"[调试] 找到 {len(users_to_check)} 个匹配的用户")
            
            # 遍历所有匹配的用户，找到密码正确的那个
            matched_user = None
            for user in users_to_check:
                print(f"[调试] 检查用户: {user.username} (手机号: {user.phone})")
                print(f"[调试] 存储的密码: {user.password}")
                print(f"[调试] 输入的密码: {password}")
                
                if self._verify_user_password(user, password):
                    matched_user = user
                    print(f"[调试] 密码匹配成功 - 用户: {user.username}")
                    break
                else:
                    print(f"[调试] 密码不匹配 - 用户: {user.username}")
            
            # 如果没有找到密码匹配的用户
            if not matched_user:
                print(f"[调试] 所有用户密码都不匹配")
                return None, "账号/手机号或密码错误"
            
            # 打印调试信息
            print(f"[调试] 最终匹配用户: {matched_user.username}")
            print(f"[调试] 角色: {matched_user.role}")
            print(f"[调试] 状态: {matched_user.status}")
            print(f"[调试] 激活状态: {matched_user.is_active}")
            
            # 检查用户状态
            if matched_user.status != UserStatus.NORMAL:
                status_messages = {
                    UserStatus.FROZEN: f"您的账户已被冻结（{matched_user.get_status_display()}），无法登录。请联系管理员解冻。",
                    UserStatus.ABNORMAL: f"您的账户状态异常（{matched_user.get_status_display()}），无法登录。请联系管理员处理。"
                }
                message = status_messages.get(matched_user.status, f"您的账户状态为\"{matched_user.get_status_display()}\"，无法登录。请联系管理员。")
                print(f"[调试] 用户状态验证失败: {message}")
                return None, message
            
            if not matched_user.is_active:
                message = "账户已被禁用，请联系管理员"
                print(f"[调试] 用户 {matched_user.username} 已被禁用")
                return None, message
            
            print(f"[调试] 用户 {matched_user.username} 登录成功")
            return matched_user, "登录成功"
            
        except Exception as e:
            print(f"[调试] 登录异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, f"认证失败: {str(e)}" 
    
    def get_user(self, username):
        """获取用户信息"""
        try:
            return self.db_manager.get_user_by_username(username)
        except Exception as e:
            print(f"获取用户失败: {e}")
            return None
    
    def get_all_users(self):
        """获取所有用户"""
        try:
            return self.db_manager.get_all_users()
        except Exception as e:
            print(f"获取用户列表失败: {e}")
            return []
    
    def update_user_role(self, username, new_role, operator_username):
        """更新用户角色"""
        try:
            # 获取目标用户和操作者
            target_user = self.db_manager.get_user_by_username(username)
            operator = self.db_manager.get_user_by_username(operator_username)
            
            if not target_user:
                return False, "用户不存在"
            if not operator:
                return False, "操作者不存在"
            
            # 权限检查：超级管理员和管理员都可以修改角色，但有不同的限制
            if operator.role == UserRole.SUPER_ADMIN:
                # 超级管理员可以修改任何人的角色，但不能修改自己的角色
                if operator.username == target_user.username:
                    return False, "不能修改自己的角色"
            elif operator.role == UserRole.ADMIN:
                # 管理员可以修改自己的角色和普通用户/裁判的角色
                if operator.username != target_user.username and target_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                    return False, "权限不足，管理员不能修改其他管理员或超级管理员的角色"
            else:
                return False, "权限不足，只有管理员及以上权限可以修改用户角色"
            
            # 更新用户角色到数据库
            self.db_manager.update_user_role(username, new_role)
            return True, f"用户 {username} 的角色已更新为 {self.get_role_display_name(new_role)}"
            
        except Exception as e:
            return False, f"角色更新失败: {str(e)}"
            
    def update_user_role_and_status(self, username, new_role, is_active, operator_username, status_type=None):
        """同时更新用户角色和状态"""
        try:
            # 获取目标用户（不考虑活跃状态）和操作者
            target_user = self.db_manager.get_user_by_username(username, include_inactive=True)
            operator = self.db_manager.get_user_by_username(operator_username)
            
            if not target_user:
                return False, "用户不存在"
            if not operator:
                return False, "操作者不存在"
            
            # 权限检查：超级管理员和管理员都可以修改角色和状态，但有不同的限制
            if operator.role == UserRole.SUPER_ADMIN:
                # 超级管理员可以修改任何人的角色和状态，但不能修改自己的角色
                if operator.username == target_user.username:
                    return False, "不能修改自己的角色"
            elif operator.role == UserRole.ADMIN:
                # 管理员可以修改自己的角色和状态，以及普通用户/裁判的角色和状态
                if operator.username != target_user.username and target_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                    return False, "权限不足，管理员不能修改其他管理员或超级管理员的角色和状态"
                
                # 管理员不能将任何用户（包括自己）提升为超级管理员
                if new_role == UserRole.SUPER_ADMIN:
                    return False, "权限不足，管理员不能将用户提升为超级管理员"
                
                # 管理员不能将其他用户提升为管理员（但可以修改自己的角色为管理员）
                if new_role == UserRole.ADMIN and operator.username != target_user.username:
                    return False, "权限不足，管理员不能将其他用户提升为管理员"
            else:
                return False, "权限不足，只有管理员及以上权限可以修改用户角色和状态"
            
            # 更新用户角色和状态到数据库
            self.db_manager.update_user_role_and_status(username, new_role, is_active, status_type)
            
            # 根据status_type区分状态文本
            if is_active:
                status_text = "正常"
            elif status_type == 'frozen':
                status_text = "冻结"
            else:
                status_text = "异常"
            
            return True, f"用户 {username} 的角色已更新为 {self.get_role_display_name(new_role)}，状态已更新为 {status_text}"
            
        except Exception as e:
            return False, f"更新失败: {str(e)}"
    
    def get_role_display_name(self, role):
        """获取角色显示名称"""
        role_names = {
            UserRole.SUPER_ADMIN: "超级管理员",
            UserRole.ADMIN: "管理员", 
            UserRole.JUDGE: "裁判",
            UserRole.USER: "普通用户"
        }
        return role_names.get(role, "未知角色")
    
    def can_manage_user(self, operator_role, target_role):
        """检查是否可以管理指定用户"""
        # 只有超级管理员可以管理其他用户
        return operator_role == UserRole.SUPER_ADMIN and target_role != UserRole.SUPER_ADMIN
    
    def get_role_hierarchy_level(self, role):
        """获取角色层级级别"""
        hierarchy = {
            UserRole.USER: 1,
            UserRole.JUDGE: 2,
            UserRole.ADMIN: 3,
            UserRole.SUPER_ADMIN: 4
        }
        return hierarchy.get(role, 0)
    
    def change_password(self, username, old_password, new_password):
        """修改用户密码"""
        try:
            # 获取用户
            user = self.db_manager.get_user_by_username(username)
            if not user:
                return False, "用户不存在"
            
            # 验证原密码（优先使用哈希，兼容明文）
            valid = False
            if getattr(user, 'password_hash', None):
                try:
                    if verify_password(old_password, user.password_hash):
                        valid = True
                except Exception:
                    valid = False
            if (not valid) and user.password == old_password:
                valid = True
            if not valid:
                return False, "原密码不正确"
            
            # 验证新密码长度
            if len(new_password) < 6 or len(new_password) > 20:
                return False, "新密码必须为6-20个字符"
            
            # 验证新密码复杂度
            if not re.search(r'\d', new_password):
                return False, "新密码必须包含数字"
            
            if not re.search(r'[a-z]', new_password):
                return False, "新密码必须包含小写字母"
            
            if re.search(r'[\u4e00-\u9fa5]', new_password):
                return False, "密码不能包含汉字"
            
            # 检查新密码是否与原密码相同
            if new_password == user.password:
                return False, "新密码不能与原密码相同"
            
            # 更新密码（暂时使用明文存储以保持与当前系统的兼容性）
            success = self.db_manager.update_user_password(user.user_id, new_password)
            
            if success:
                return True, "密码修改成功"
            else:
                return False, "密码修改失败"
            
        except Exception as e:
            return False, f"密码修改失败: {str(e)}"
    
    
    def get_user_by_username(self, username):
        """根据用户名获取用户信息"""
        try:
            return self.db_manager.get_user_by_username(username)
        except Exception as e:
            return None
    
    def update_user_profile(self, username, full_name, nickname, phone):
        """更新用户个人资料"""
        try:
            # 获取用户
            user = self.db_manager.get_user_by_username(username)
            if not user:
                return False, "用户不存在"
            
            # 检查是否与原信息相同（允许昵称更新）
            if (user.real_name == full_name and 
                user.phone == phone and
                getattr(user, 'nickname', '') == nickname):
                return False, "信息未发生变化"
            
            # 更新用户信息
            success = self.db_manager.update_user_profile(
                user.user_id, full_name, nickname, phone
            )
            
            if success:
                return True, "个人信息更新成功"
            else:
                return False, "个人信息更新失败"
            
        except Exception as e:
            return False, f"个人信息更新失败: {str(e)}"
    
    def reset_user_password(self, username, new_password=None):
        """重置用户密码"""
        try:
            # 如果没有提供新密码，生成默认密码
            if not new_password:
                new_password = "aaa123456"
            
            # 获取用户
            user = self.db_manager.get_user_by_username(username)
            if not user:
                return False, "用户不存在"
            
            # 更新密码（使用user_id而不是username）
            success = self.db_manager.update_user_password(user.user_id, new_password)
            
            if success:
                return True, f"密码重置成功，新密码：{new_password}"
            else:
                return False, "密码重置失败"
            
        except Exception as e:
            return False, f"密码重置失败: {str(e)}"
    

# 导入re模块用于密码验证
import re

# 全局用户管理器实例
user_manager = UserManager()
