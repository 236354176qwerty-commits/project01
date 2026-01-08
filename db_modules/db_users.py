import logging

from mysql.connector import Error

from models import User
from utils.helpers import generate_password_hash


logger = logging.getLogger(__name__)


class UserDbMixin:
    """用户相关数据库操作 mixin。

    依赖宿主类提供:
    - self.get_connection(): 返回数据库连接的上下文管理器
    """

    # ==================== 用户相关操作 ====================
    
    def create_user(self, user):
        """创建用户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                password = user.password
                password_hash = getattr(user, 'password_hash', None)
                if password and not password_hash:
                    password_hash = generate_password_hash(password)
                cursor.execute("""
                    INSERT INTO users (username, real_name, nickname, team_name, email, phone, role, status, is_active, password, password_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (user.username, user.real_name, user.nickname, user.team_name,
                      user.email, user.phone, user.role.value, 'normal', True, password, password_hash))
                
                user.user_id = cursor.lastrowid
                conn.commit()
                return user
                
        except Error as e:
            logger.error(f"创建用户失败: {e}")
            raise

    def get_user_by_username(self, username, include_inactive=False):
        """根据用户名获取用户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                # 移除激活状态过滤，只根据用户名查询
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                row = cursor.fetchone()
                
                if row:
                    return User(
                        user_id=row['user_id'],
                        username=row['username'],
                        real_name=row['real_name'],
                        email=row['email'],
                        phone=row['phone'],
                        role=row['role'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        is_active=row['is_active'],
                        status=row.get('status', 'normal'),
                        nickname=row.get('nickname'),
                        team_name=row.get('team_name'),
                        password=row.get('password'),
                        password_hash=row.get('password_hash'),
                        session_token=row.get('session_token'),
                        id_card=row.get('id_card'),
                        gender=row.get('gender'),
                        birthdate=row.get('birthdate'),
                        deleted_at=row.get('deleted_at')
                    )
                return None
                
        except Error as e:
            logger.error(f"获取用户失败: {e}")
            raise

    def get_user_for_login(self, username_or_phone):
        """获取用户用于登录验证（支持用户名或手机号登录，包括非活跃用户）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                # 同时查询用户名或手机号匹配的所有用户
                cursor.execute(
                    "SELECT * FROM users WHERE username = %s OR phone = %s", 
                    (username_or_phone, username_or_phone)
                )
                rows = cursor.fetchall()
                
                if not rows:
                    return None
                
                # 将所有匹配的用户转换为User对象
                users = []
                for row in rows:
                    users.append(User(
                        user_id=row['user_id'],
                        username=row['username'],
                        real_name=row['real_name'],
                        email=row['email'],
                        phone=row['phone'],
                        role=row['role'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        is_active=row['is_active'],
                        status=row.get('status', 'normal'),
                        nickname=row.get('nickname'),
                        team_name=row.get('team_name'),
                        password=row.get('password'),
                        password_hash=row.get('password_hash'),
                        session_token=row.get('session_token'),
                        id_card=row.get('id_card'),
                        gender=row.get('gender'),
                        birthdate=row.get('birthdate'),
                        deleted_at=row.get('deleted_at')
                    ))
                
                # 如果只有一个匹配，直接返回
                if len(users) == 1:
                    return users[0]
                
                # 如果有多个匹配（用户名与其他用户的手机号重复），返回列表
                return users
                
        except Error as e:
            logger.error(f"获取用户失败: {e}")
            raise

    def get_user_by_id(self, user_id):
        """根据用户ID获取用户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                # 移除激活状态过滤，只根据用户ID查询
                cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                
                if row:
                    return User(
                        user_id=row['user_id'],
                        username=row['username'],
                        real_name=row['real_name'],
                        email=row['email'],
                        phone=row['phone'],
                        role=row['role'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        is_active=row['is_active'],
                        status=row.get('status', 'normal'),
                        nickname=row.get('nickname'),
                        team_name=row.get('team_name'),
                        password=row.get('password'),
                        password_hash=row.get('password_hash'),
                        session_token=row.get('session_token'),
                    )
                return None
                
        except Error as e:
            logger.error(f"获取用户失败: {e}")
            raise

    def get_user_by_phone(self, phone):
        """根据手机号获取用户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True, buffered=True)  # 添加 buffered=True
                cursor.execute("SELECT * FROM users WHERE phone = %s", (phone,))
                row = cursor.fetchone()
                cursor.close()  # 显式关闭游标
                
                if row:
                    return User(
                        user_id=row['user_id'],
                        username=row['username'],
                        real_name=row['real_name'],
                        email=row['email'],
                        phone=row['phone'],
                        role=row['role'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        is_active=row['is_active'],
                        status=row.get('status', 'normal'),
                        nickname=row.get('nickname'),
                        team_name=row.get('team_name'),
                        password=row.get('password'),
                        password_hash=row.get('password_hash'),
                        session_token=row.get('session_token'),
                    )
                return None
                
        except Error as e:
            logger.error(f"根据手机号获取用户失败: {e}")
            raise

    def get_all_users(self, role=None):
        """获取所有用户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                if role:
                    cursor.execute("SELECT * FROM users WHERE role = %s ORDER BY created_at DESC", (role,))
                else:
                    # 按照权限级别排序：超级管理员 > 管理员 > 裁判 > 普通用户
                    cursor.execute("""
                        SELECT * FROM users 
                        ORDER BY 
                            CASE role 
                                WHEN 'super_admin' THEN 1 
                                WHEN 'admin' THEN 2 
                                WHEN 'judge' THEN 3 
                                WHEN 'user' THEN 4 
                                ELSE 5 
                            END, 
                            created_at DESC
                    """)
                
                users = []
                for row in cursor.fetchall():
                    users.append(User(
                        user_id=row['user_id'],
                        username=row['username'],
                        real_name=row['real_name'],
                        email=row['email'],
                        phone=row['phone'],
                        role=row['role'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        is_active=row['is_active'],
                        status=row.get('status', 'normal'),
                        nickname=row.get('nickname'),
                        team_name=row.get('team_name'),
                        password=row.get('password'),
                        password_hash=row.get('password_hash'),
                        session_token=row.get('session_token'),
                        id_card=row.get('id_card'),
                        gender=row.get('gender'),
                        birthdate=row.get('birthdate'),
                        deleted_at=row.get('deleted_at')
                    ))
                
                return users
                
        except Error as e:
            logger.error(f"获取用户列表失败: {e}")
            raise

    def update_user_role(self, username, new_role):
        """更新用户角色"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET role = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE username = %s AND is_active = TRUE
                """, (new_role.value, username))
                
                if cursor.rowcount == 0:
                    raise Exception("用户不存在或更新失败")
                
                conn.commit()
                logger.info(f"用户 {username} 的角色已更新为 {new_role.value}")
                return True
                
        except Error as e:
            logger.error(f"更新用户角色失败: {e}")
            raise
    
    def update_user_role_and_status(self, username, new_role, is_active, status):
        """同时更新用户角色和状态"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET role = %s, is_active = %s, status = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE username = %s
                """, (new_role.value, is_active, status, username))
                
                if cursor.rowcount == 0:
                    raise Exception("用户不存在或更新失败")
                
                conn.commit()
                logger.info(f"用户 {username} 的角色已更新为 {new_role.value}，状态已更新为 {status}")
                return True
                
        except Error as e:
            logger.error(f"更新用户角色和状态失败: {e}")
            raise
    
    def update_user(self, user):
        """更新用户信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                password = user.password
                password_hash = getattr(user, 'password_hash', None)
                if password and not password_hash:
                    password_hash = generate_password_hash(password)
                cursor.execute("""
                    UPDATE users 
                    SET username = %s, real_name = %s, nickname = %s, team_name = %s, 
                        email = %s, phone = %s, password = %s, password_hash = %s, role = %s, status = %s, 
                        is_active = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = %s
                """, (user.username, user.real_name, user.nickname, user.team_name,
                      user.email, user.phone, password, password_hash, user.role.value, user.status.value,
                      user.is_active, user.user_id))
                
                if cursor.rowcount == 0:
                    raise Exception("用户不存在或更新失败")
                
                conn.commit()
                logger.info(f"用户ID {user.user_id} 的信息已更新")
                return True
                
        except Error as e:
            logger.error(f"更新用户信息失败: {e}")
            raise

    def update_user_password(self, user_id, new_password):
        """更新用户密码"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                password_hash = generate_password_hash(new_password)
                cursor.execute("""
                    UPDATE users 
                    SET password = %s, password_hash = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = %s
                """, (new_password, password_hash, user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Error as e:
            logger.error(f"更新用户密码失败: {e}")
            raise
    
    def update_user_profile(self, user_id, full_name, nickname, phone):
        """更新用户个人资料"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 首先检查是否存在nickname列，如果不存在则添加
                cursor.execute("SHOW COLUMNS FROM users LIKE 'nickname'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN nickname VARCHAR(100)")
                
                cursor.execute("""
                    UPDATE users 
                    SET real_name = %s, nickname = %s, phone = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = %s
                """, (full_name, nickname, phone, user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Error as e:
            logger.error(f"更新用户资料失败: {e}")
            raise
    
    def update_user_status(self, username, new_status):
        """更新用户状态"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "UPDATE users SET status = %s WHERE username = %s",
                    (new_status, username)
                )
                conn.commit()
                return cursor.rowcount > 0
                
        except Error as e:
            logger.error(f"更新用户状态失败: {e}")
            return False

    def update_user_session_token(self, user_id, session_token):
        """更新用户单点登录会话标识"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET session_token = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                    (session_token, user_id),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Error as e:
            logger.error(f"更新用户session_token失败: {e}")
            raise

    def get_user_session_token(self, user_id):
        """获取用户当前有效的单点登录会话标识"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT session_token FROM users WHERE user_id = %s LIMIT 1",
                    (user_id,),
                )
                row = cursor.fetchone() or {}
                return row.get('session_token')
        except Error as e:
            logger.error(f"获取用户session_token失败: {e}")
            raise
