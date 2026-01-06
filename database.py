#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武术赛事管理系统 - 数据库连接和操作
"""

import mysql.connector
from mysql.connector import Error, pooling
from contextlib import contextmanager
import logging
import time

from config import Config
from models import DATABASE_SCHEMA
from utils.helpers import generate_password_hash
from db_modules.db_users import UserDbMixin
from db_modules.db_events import EventDbMixin
from db_modules.db_participants import ParticipantDbMixin
from db_modules.db_scores import ScoreDbMixin
from db_modules.db_event_items import EventItemDbMixin
from db_modules.db_entries import EntryDbMixin

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimedCursorWrapper:
    def __init__(self, cursor, slow_threshold_ms=50):
        self._cursor = cursor
        self._slow_threshold_ms = slow_threshold_ms

    def execute(self, operation, params=None, multi=False):
        start = time.perf_counter()
        try:
            return self._cursor.execute(operation, params, multi)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            if duration_ms >= self._slow_threshold_ms:
                logger.warning(
                    "Slow query took %.1f ms: %s; params=%s",
                    duration_ms,
                    operation,
                    params,
                )

    def executemany(self, operation, seq_params):
        start = time.perf_counter()
        try:
            return self._cursor.executemany(operation, seq_params)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            if duration_ms >= self._slow_threshold_ms:
                logger.warning(
                    "Slow query (executemany) took %.1f ms: %s; params_count=%d",
                    duration_ms,
                    operation,
                    len(seq_params) if seq_params is not None else 0,
                )

    def __getattr__(self, item):
        return getattr(self._cursor, item)


_connection_pool = None

def _get_connection_pool(config):
    """获取全局数据库连接池"""
    global _connection_pool
    if _connection_pool is None:
        try:
            pool_config = config.copy()
            # 移除连接池配置参数，避免传递给连接池构造函数
            pool_size = pool_config.pop('pool_size', 5)
            pool_name = pool_config.pop('pool_name', getattr(Config, 'DB_POOL_NAME', 'wushu_pool'))
            
            _connection_pool = pooling.MySQLConnectionPool(
                pool_name=pool_name,
                pool_size=pool_size,
                **pool_config
            )
            logger.info(f"数据库连接池创建成功，池大小: {pool_size}")
        except Error as e:
            logger.error(f"创建数据库连接池失败，将回退到直连模式: {e}")
            _connection_pool = None
    return _connection_pool

class DatabaseManager(
    UserDbMixin,
    EventDbMixin,
    ParticipantDbMixin,
    ScoreDbMixin,
    EventItemDbMixin,
    EntryDbMixin,
):
    """数据库管理器"""
    
    def __init__(self):
        self.config = {
            'host': Config.DB_HOST,
            'port': Config.DB_PORT,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
            'database': Config.DB_NAME,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': False,
            'raise_on_warnings': False,
            'pool_size': 5,  # 减少连接池大小以避免超过限制
            'pool_reset_session': True,
            'connection_timeout': 30
        }
        self.pool = _get_connection_pool(self.config)

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        connection = None
        try:
            if hasattr(self, 'pool') and self.pool:
                connection = self.pool.get_connection()
            else:
                connection = mysql.connector.connect(**self.config)
            slow_threshold_ms = getattr(Config, 'SLOW_QUERY_THRESHOLD_MS', 50)

            original_cursor = connection.cursor

            def timed_cursor(*args, **kwargs):
                base_cursor = original_cursor(*args, **kwargs)
                return TimedCursorWrapper(base_cursor, slow_threshold_ms=slow_threshold_ms)

            connection.cursor = timed_cursor

            yield connection
        except Error as e:
            logger.error(f"数据库连接错误: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()

    def init_database(self, force_recreate=False):
        """初始化数据库和表
        
        Args:
            force_recreate (bool): 是否强制重建表（删除现有表）
        """
        try:
            # 首先连接到MySQL服务器（不指定数据库）
            temp_config = self.config.copy()
            temp_config.pop('database', None)
            
            with mysql.connector.connect(**temp_config) as connection:
                cursor = connection.cursor()
                
                # 创建数据库（如果不存在）- 静默模式
                try:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                except Error as e:
                    # 忽略错误码1007（数据库已存在）
                    if '1007' not in str(e):
                        logger.warning(f"创建数据库时出现警告: {e}")
                    # 继续执行，因为数据库可能已经存在
                
            # 连接到指定数据库并创建表
            with self.get_connection() as connection:
                cursor = connection.cursor()
                
                if force_recreate:
                    # 强制重建：删除现有表
                    logger.info("强制重建模式：删除现有表...")
                    for table_name in reversed(list(DATABASE_SCHEMA.keys())):
                        try:
                            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                            logger.info(f"删除表 {table_name}")
                        except Error as e:
                            logger.warning(f"删除表 {table_name} 失败: {e}")
                else:
                    # 检查并添加缺失的列
                    self._migrate_database(cursor)
                
                # 创建所有表
                for table_name, schema in DATABASE_SCHEMA.items():
                    try:
                        if force_recreate:
                            # 强制重建模式：直接创建表
                            schema_without_if_not_exists = schema.replace("CREATE TABLE IF NOT EXISTS", "CREATE TABLE")
                            cursor.execute(schema_without_if_not_exists)
                            logger.info(f"创建表 {table_name}")
                        else:
                            # 正常模式：如果不存在则创建（静默）
                            cursor.execute(schema)
                    except Error as e:
                        # 如果表已存在，静默忽略
                        if not force_recreate and ("already exists" in str(e).lower() or ("table" in str(e).lower() and "exists" in str(e).lower())):
                            pass
                        else:
                            logger.error(f"创建表 {table_name} 失败: {e}")
                            raise
                
                connection.commit()
                
                # 创建默认超级管理员账户
                self._create_default_admin(cursor)
                connection.commit()
                
        except Error as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    def _migrate_database(self, cursor):
        """迁移数据库结构"""
        try:
            # 确保users表存在password列（过渡期保留明文密码）
            cursor.execute("SHOW COLUMNS FROM users LIKE 'password'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN password VARCHAR(100) DEFAULT NULL COMMENT '明文密码'")
                logger.info("添加了password列到users表")

            # 确保users表存在password_hash列（安全存储）
            cursor.execute("SHOW COLUMNS FROM users LIKE 'password_hash'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN password_hash VARBINARY(128) DEFAULT NULL COMMENT '密码哈希' AFTER password")
                logger.info("添加了password_hash列到users表")

            # 检查users表是否存在nickname和team_name列
            cursor.execute("SHOW COLUMNS FROM users LIKE 'nickname'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN nickname VARCHAR(100) AFTER real_name")
                logger.info("添加了nickname列到users表")
            
            cursor.execute("SHOW COLUMNS FROM users LIKE 'team_name'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN team_name VARCHAR(200) AFTER nickname")
                logger.info("添加了team_name列到users表")
            
            # 检查users表是否存在手机号索引
            cursor.execute("SHOW INDEX FROM users WHERE Key_name = 'idx_phone'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD INDEX idx_phone (phone)")
                logger.info("添加了idx_phone索引到users表")

            # 确保users表存在id_card、gender、birthdate、deleted_at列
            cursor.execute("SHOW COLUMNS FROM users LIKE 'id_card'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN id_card VARCHAR(30) DEFAULT NULL COMMENT '身份证号' AFTER phone")
                logger.info("添加了id_card列到users表")

            cursor.execute("SHOW COLUMNS FROM users LIKE 'gender'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN gender ENUM('male','female','other') DEFAULT NULL COMMENT '性别' AFTER id_card")
                logger.info("添加了gender列到users表")

            cursor.execute("SHOW COLUMNS FROM users LIKE 'birthdate'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN birthdate DATE DEFAULT NULL COMMENT '出生日期' AFTER gender")
                logger.info("添加了birthdate列到users表")

            cursor.execute("SHOW COLUMNS FROM users LIKE 'deleted_at'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP NULL DEFAULT NULL COMMENT '删除时间' AFTER status")
                logger.info("添加了deleted_at列到users表")
            
            # 确保events表存在registration_start_time列
            try:
                cursor.execute("SHOW COLUMNS FROM events LIKE 'registration_start_time'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE events ADD COLUMN registration_start_time DATETIME NULL AFTER max_participants")
                    logger.info("添加了registration_start_time列到events表")
                
                # 检查events表是否有正确的字段名（start_date, end_date）
                cursor.execute("SHOW COLUMNS FROM events LIKE 'start_date'")
                if not cursor.fetchone():
                    # 检查是否有旧的字段名
                    cursor.execute("SHOW COLUMNS FROM events LIKE 'event_start_date'")
                    if cursor.fetchone():
                        cursor.execute("ALTER TABLE events CHANGE event_start_date start_date DATETIME NOT NULL")
                        logger.info("重命名event_start_date为start_date")
                    else:
                        cursor.execute("ALTER TABLE events ADD COLUMN start_date DATETIME NOT NULL AFTER description")
                        logger.info("添加了start_date列到events表")
                
                cursor.execute("SHOW COLUMNS FROM events LIKE 'end_date'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE events ADD COLUMN end_date DATETIME NOT NULL AFTER start_date")
                    logger.info("添加了end_date列到events表")

                # 确保关键索引存在，以加速赛事列表查询和统计
                cursor.execute("SHOW INDEX FROM events WHERE Key_name = 'idx_status'")
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute("ALTER TABLE events ADD INDEX idx_status (status)")
                    logger.info("添加了idx_status索引到events表")

                cursor.execute("SHOW INDEX FROM events WHERE Key_name = 'idx_start_date'")
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute("ALTER TABLE events ADD INDEX idx_start_date (start_date)")
                    logger.info("添加了idx_start_date索引到events表")

                cursor.execute("SHOW INDEX FROM events WHERE Key_name = 'idx_registration_start'")
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute("ALTER TABLE events ADD INDEX idx_registration_start (registration_start_time)")
                    logger.info("添加了idx_registration_start索引到events表")

                # 新增按创建时间的索引，优化按 created_at 排序的赛事列表
                cursor.execute("SHOW INDEX FROM events WHERE Key_name = 'idx_created_at'")
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute("ALTER TABLE events ADD INDEX idx_created_at (created_at)")
                    logger.info("添加了idx_created_at索引到events表")

                # 组合索引：按状态 + 开始时间筛选/排序，常见模式为 WHERE status=... ORDER BY start_date ...
                cursor.execute("SHOW INDEX FROM events WHERE Key_name = 'idx_status_start_date'")
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute("ALTER TABLE events ADD INDEX idx_status_start_date (status, start_date)")
                    logger.info("添加了idx_status_start_date组合索引到events表")

                # 组合索引：按状态 + 创建时间筛选/排序，对管理后台按创建时间查看不同状态赛事有帮助
                cursor.execute("SHOW INDEX FROM events WHERE Key_name = 'idx_status_created_at'")
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute("ALTER TABLE events ADD INDEX idx_status_created_at (status, created_at)")
                    logger.info("添加了idx_status_created_at组合索引到events表")
                    
            except Error as events_error:
                if "doesn't exist" in str(events_error):
                    logger.info("events表不存在，将在后续创建")
                else:
                    logger.warning(f"events表迁移失败: {events_error}")
            try:
                cursor.execute("SHOW COLUMNS FROM participants LIKE 'event_member_no'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE participants ADD COLUMN event_member_no INT DEFAULT NULL AFTER registration_number")
                    logger.info("添加了event_member_no列到participants表")
                cursor.execute("SHOW INDEX FROM participants WHERE Key_name = 'uniq_event_member_no'")
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute("ALTER TABLE participants ADD UNIQUE KEY uniq_event_member_no (event_id, event_member_no)")
                    logger.info("添加了uniq_event_member_no唯一索引到participants表")
                # 确保存在按赛事+报名时间的组合索引，优化参赛者列表分页查询
                cursor.execute("SHOW INDEX FROM participants WHERE Key_name = 'idx_event_registered_at'")
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute("ALTER TABLE participants ADD INDEX idx_event_registered_at (event_id, registered_at)")
                    logger.info("添加了idx_event_registered_at索引到participants表")

                # 确保participants表存在gender和age_group列及联合索引
                cursor.execute("SHOW COLUMNS FROM participants LIKE 'gender'")
                has_gender = cursor.fetchone() is not None
                if not has_gender:
                    cursor.execute("ALTER TABLE participants ADD COLUMN gender VARCHAR(10) AFTER weight_class")
                    logger.info("添加了gender列到participants表")
                    has_gender = True

                cursor.execute("SHOW COLUMNS FROM participants LIKE 'age_group'")
                has_age_group = cursor.fetchone() is not None
                if not has_age_group:
                    cursor.execute("ALTER TABLE participants ADD COLUMN age_group VARCHAR(20) AFTER gender")
                    logger.info("添加了age_group列到participants表")
                    has_age_group = True

                cursor.execute("SHOW INDEX FROM participants WHERE Key_name = 'idx_event_gender_age_group'")
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute("ALTER TABLE participants ADD INDEX idx_event_gender_age_group (event_id, gender, age_group)")
                    logger.info("添加了idx_event_gender_age_group索引到participants表")
            except Error as participants_error:
                if "doesn't exist" in str(participants_error):
                    logger.info("participants表不存在，将在后续创建")
                else:
                    logger.warning(f"participants表迁移失败: {participants_error}")

            if hasattr(self, '_ensure_event_columns'):
                try:
                    self._ensure_event_columns(cursor)
                except Exception as events_extra_error:
                    logger.warning(f"events表扩展列迁移失败: {events_extra_error}")

            # 扩展scores表结构（如果存在）
            if self._table_exists(cursor, 'scores'):
                try:
                    cursor.execute("SHOW COLUMNS FROM scores LIKE 'event_id'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE scores ADD COLUMN event_id INT NULL COMMENT '赛事ID' AFTER updated_at")
                        logger.info("添加了event_id列到scores表")

                    cursor.execute("SHOW COLUMNS FROM scores LIKE 'event_item_id'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE scores ADD COLUMN event_item_id INT NULL COMMENT '项目ID' AFTER event_id")
                        logger.info("添加了event_item_id列到scores表")

                    cursor.execute("SHOW COLUMNS FROM scores LIKE 'entry_id'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE scores ADD COLUMN entry_id BIGINT NULL COMMENT '报名条目ID' AFTER event_item_id")
                        logger.info("添加了entry_id列到scores表")

                    cursor.execute("SHOW COLUMNS FROM scores LIKE 'rank_in_round'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE scores ADD COLUMN rank_in_round INT NULL COMMENT '本轮排名' AFTER entry_id")
                        logger.info("添加了rank_in_round列到scores表")

                    cursor.execute("SHOW COLUMNS FROM scores LIKE 'is_valid'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE scores ADD COLUMN is_valid BOOLEAN DEFAULT TRUE COMMENT '是否有效' AFTER rank_in_round")
                        logger.info("添加了is_valid列到scores表")

                    cursor.execute("SHOW COLUMNS FROM scores LIKE 'judge_signature'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE scores ADD COLUMN judge_signature VARCHAR(100) COMMENT '裁判签名' AFTER is_valid")
                        logger.info("添加了judge_signature列到scores表")

                    cursor.execute("SHOW COLUMNS FROM scores LIKE 'modified_at'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE scores ADD COLUMN modified_at DATETIME NULL COMMENT '最后修改时间' AFTER judge_signature")
                        logger.info("添加了modified_at列到scores表")

                    cursor.execute("SHOW COLUMNS FROM scores LIKE 'modified_by'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE scores ADD COLUMN modified_by INT NULL COMMENT '修改人' AFTER modified_at")
                        logger.info("添加了modified_by列到scores表")

                    cursor.execute("SHOW COLUMNS FROM scores LIKE 'modification_reason'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE scores ADD COLUMN modification_reason TEXT COMMENT '修改原因' AFTER modified_by")
                        logger.info("添加了modification_reason列到scores表")

                    cursor.execute("SHOW COLUMNS FROM scores LIKE 'version'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE scores ADD COLUMN version INT DEFAULT 1 COMMENT '版本号(乐观锁)' AFTER modification_reason")
                        logger.info("添加了version列到scores表")

                    cursor.execute("SHOW INDEX FROM scores WHERE Key_name = 'idx_event_item_round'")
                    rows = cursor.fetchall()
                    if not rows:
                        cursor.execute("ALTER TABLE scores ADD INDEX idx_event_item_round (event_id, event_item_id, round_number)")
                        logger.info("添加了idx_event_item_round索引到scores表")

                    cursor.execute("SHOW INDEX FROM scores WHERE Key_name = 'idx_entry_round'")
                    rows = cursor.fetchall()
                    if not rows:
                        cursor.execute("ALTER TABLE scores ADD INDEX idx_entry_round (entry_id, round_number)")
                        logger.info("添加了idx_entry_round索引到scores表")
                except Error as scores_error:
                    logger.warning(f"scores表迁移失败: {scores_error}")

        except Error as e:
            # 如果表不存在，忽略错误（稍后会创建表）
            if "doesn't exist" in str(e):
                logger.info("表不存在，将在后续创建")
            else:
                logger.error(f"数据库迁移失败: {e}")
                raise
    
    def apply_table_comments(self):
        """为所有核心表设置或更新表级注释"""
        statements = [
            ("users", "ALTER TABLE users COMMENT = '用户表（账号、基本资料、登录状态）'"),
            ("events", "ALTER TABLE events COMMENT = '赛事表（基础信息与报名配置）'"),
            ("announcements", "ALTER TABLE announcements COMMENT = '通知公告表（面向全体或按角色发送的公告）'"),
            ("notifications", "ALTER TABLE notifications COMMENT = '系统通知模板表（面向全体或按角色发送的通知）'"),
            ("user_notifications", "ALTER TABLE user_notifications COMMENT = '用户通知收件表（通知与用户的映射及阅读状态）'"),
            ("participants", "ALTER TABLE participants COMMENT = '参赛者旧表（按赛事+用户记录参赛，含胸牌号与项目，已由 event_participants / entries 逐步替代）'"),
            ("scores", "ALTER TABLE scores COMMENT = '成绩表（评分明细，关联参赛者、项目和报名条目）'"),
            ("event_items", "ALTER TABLE event_items COMMENT = '赛事项目表（新结构，按赛事+项目记录比赛设置）'"),
            ("event_participants", "ALTER TABLE event_participants COMMENT = '赛事参与者表（新结构，按赛事+用户+角色记录参与者信息）'"),
            ("entries", "ALTER TABLE entries COMMENT = '报名条目表（新结构，按赛事+项目+队伍记录报名信息）'"),
            ("entry_members", "ALTER TABLE entry_members COMMENT = '报名成员表（新结构，按报名条目+用户记录成员信息）'"),
            ("entry_schedules", "ALTER TABLE entry_schedules COMMENT = '比赛编排表（新结构，按项目+报名条目记录比赛编排信息）'"),
            ("schedule_adjustment_logs", "ALTER TABLE schedule_adjustment_logs COMMENT = '编排调整历史表（新结构，按项目+报名条目记录编排调整历史）'"),
            ("score_modification_logs", "ALTER TABLE score_modification_logs COMMENT = '成绩修改历史表（新结构，按成绩+报名条目记录成绩修改历史）'"),
            ("payment_records", "ALTER TABLE payment_records COMMENT = '支付记录表（新结构，按赛事+队伍+报名条目记录支付信息）'"),
            ("teams", "ALTER TABLE teams COMMENT = '队伍表（代表队/俱乐部信息及报名主体）'"),
            ("team_applications", "ALTER TABLE team_applications COMMENT = '队伍报名申请旧表（队员、工作人员及费用申请记录，逐步由 entries 体系替代）'"),
            ("team_staff", "ALTER TABLE team_staff COMMENT = '队伍工作人员旧表（教练和工作人员信息）'"),
            ("team_players", "ALTER TABLE team_players COMMENT = '队员旧表（队伍成员与所报项目的旧结构）'"),
            ("team_drafts", "ALTER TABLE team_drafts COMMENT = '队伍报名草稿旧表（未正式提交的队伍信息与人员草稿）'"),
            ("maintenance_logs", "ALTER TABLE maintenance_logs COMMENT = '运维操作日志表（记录系统维护操作日志）'"),
        ]

        with self.get_connection() as connection:
            cursor = connection.cursor()
            for table_name, sql in statements:
                try:
                    cursor.execute(sql)
                    logger.info("更新表注释成功: %s", table_name)
                except Error as e:
                    message = str(e)
                    if "doesn't exist" in message or "Unknown table" in message:
                        logger.info("跳过不存在的表: %s", table_name)
                        continue
                    logger.error("更新表注释失败 %s: %s", table_name, e)
                    raise
            connection.commit()

    def _table_exists(self, cursor, table_name):
        """检查表是否存在"""
        try:
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            result = cursor.fetchone()
            return result is not None
        except Error as e:
            logger.error(f"检查表 {table_name} 是否存在时出错: {e}")
            return False

    def _create_default_admin(self, cursor):
        """创建默认超级管理员账户"""
        try:
            # 检查是否已存在超级管理员
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'super_admin'")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # 创建默认超级管理员
                admin_password = 'admin123'
                admin_password_hash = generate_password_hash(admin_password)
                cursor.execute("""
                    INSERT INTO users (username, real_name, email, role, status, is_active, password, password_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, ('admin', '系统管理员', 'admin@wushu.com', 'super_admin', 'normal', True, admin_password, admin_password_hash))
                
                logger.info("默认超级管理员账户创建成功 (用户名: admin, 密码: admin123)")
                
        except Error as e:
            logger.error(f"创建默认管理员失败: {e}")


if __name__ == '__main__':
    # 测试数据库连接和初始化
    db_manager = DatabaseManager()
    try:
        db_manager.init_database()
        print("数据库初始化成功！")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
