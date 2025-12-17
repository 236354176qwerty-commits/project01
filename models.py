#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武术赛事管理系统 - 数据库模型定义
"""

from datetime import datetime
from enum import Enum

class UserRole(Enum):
    """用户角色枚举"""
    SUPER_ADMIN = 'super_admin'  # 超级管理员
    ADMIN = 'admin'              # 管理员
    JUDGE = 'judge'              # 裁判
    USER = 'user'                # 普通用户

class UserStatus(Enum):
    """用户状态枚举"""
    NORMAL = 'normal'            # 正常状态
    ABNORMAL = 'abnormal'        # 异常状态
    FROZEN = 'frozen'            # 冻结状态

class EventStatus(Enum):
    """赛事状态枚举"""
    DRAFT = 'draft'              # 草稿
    PUBLISHED = 'published'      # 已发布
    ONGOING = 'ongoing'          # 进行中
    COMPLETED = 'completed'      # 已完成
    CANCELLED = 'cancelled'      # 已取消

class ParticipantStatus(Enum):
    """参赛者状态枚举"""
    REGISTERED = 'registered'    # 已注册
    CHECKED_IN = 'checked_in'    # 已签到
    COMPETING = 'competing'      # 比赛中
    COMPLETED = 'completed'      # 已完成
    DISQUALIFIED = 'disqualified' # 取消资格

class User:
    """用户模型"""
    def __init__(self, user_id=None, username=None, 
                 real_name=None, email=None, phone=None, role=UserRole.USER,
                 created_at=None, updated_at=None, is_active=True, status=UserStatus.NORMAL,
                 password=None, password_hash=None, nickname=None, team_name=None,
                 id_card=None, gender=None, birthdate=None, deleted_at=None):
        self.user_id = user_id
        self.username = username
        self.real_name = real_name
        self.email = email
        self.phone = phone
        self.role = role if isinstance(role, UserRole) else UserRole(role)
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.is_active = is_active
        # 处理状态字段，确保正确转换为枚举
        if isinstance(status, UserStatus):
            self.status = status
        elif isinstance(status, str):
            try:
                self.status = UserStatus(status)
            except ValueError:
                # 如果状态值无效，默认为正常状态
                self.status = UserStatus.NORMAL
        else:
            self.status = UserStatus.NORMAL
        self.password = password  # 明文密码
        self.password_hash = password_hash
        self.nickname = nickname  # 用户昵称
        self.team_name = team_name  # 运动队名称
        self.id_card = id_card
        self.gender = gender
        self.birthdate = birthdate
        self.deleted_at = deleted_at

    def to_dict(self):
        """转换为字典"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'real_name': self.real_name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'status': self.status.value,
            'status_display': self.get_status_display(),
            'password': self.password,
            'nickname': self.nickname,
            'team_name': self.team_name,
            'id_card': self.id_card,
            'gender': self.gender,
            'birthdate': self.birthdate.isoformat() if self.birthdate else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    def get_status_display(self):
        """获取状态显示名称"""
        status_display = {
            UserStatus.NORMAL: '正常',
            UserStatus.ABNORMAL: '异常',
            UserStatus.FROZEN: '冻结'
        }
        return status_display.get(self.status, '未知')

    def can_login(self):
        """检查用户是否可以登录"""
        return self.is_active and self.status == UserStatus.NORMAL

    def has_permission(self, required_roles):
        """检查用户是否有指定权限"""
        if not isinstance(required_roles, list):
            required_roles = [required_roles]
        
        role_hierarchy = {
            UserRole.SUPER_ADMIN: 4,
            UserRole.ADMIN: 3,
            UserRole.JUDGE: 2,
            UserRole.USER: 1
        }
        
        user_level = role_hierarchy.get(self.role, 0)
        required_levels = [role_hierarchy.get(UserRole(role), 0) for role in required_roles]
        
        return user_level >= max(required_levels)

class Event:
    """赛事模型"""
    def __init__(self, event_id=None, name=None, description=None,
                 start_date=None, end_date=None, location=None,
                 max_participants=None, registration_start_time=None, registration_deadline=None,
                 status=EventStatus.DRAFT, created_by=None,
                 created_at=None, updated_at=None, contact_phone=None, organizer=None, co_organizer=None,
                 individual_fee=0.0, pair_practice_fee=0.0, team_competition_fee=0.0):
        self.event_id = event_id
        self.name = name
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.location = location
        self.max_participants = max_participants
        self.registration_start_time = registration_start_time
        self.registration_deadline = registration_deadline
        self.status = status if isinstance(status, EventStatus) else EventStatus(status)
        self.created_by = created_by
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.contact_phone = contact_phone
        self.organizer = organizer
        self.co_organizer = co_organizer
        self.individual_fee = individual_fee
        self.pair_practice_fee = pair_practice_fee
        self.team_competition_fee = team_competition_fee

    def to_dict(self):
        """转换为字典"""
        return {
            'event_id': self.event_id,
            'name': self.name,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'location': self.location,
            'max_participants': self.max_participants,
            'registration_start_time': self.registration_start_time.isoformat() if self.registration_start_time else None,
            'registration_deadline': self.registration_deadline.isoformat() if self.registration_deadline else None,
            'status': self.status.value,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'contact_phone': self.contact_phone,
            'organizer': self.organizer,
            'co_organizer': self.co_organizer,
            'individual_fee': float(self.individual_fee or 0),
            'pair_practice_fee': float(self.pair_practice_fee or 0),
            'team_competition_fee': float(self.team_competition_fee or 0)
        }

class Participant:
    """参赛者模型"""
    def __init__(self, participant_id=None, event_id=None, user_id=None,
                 registration_number=None, event_member_no=None, category=None, weight_class=None,
                 status=ParticipantStatus.REGISTERED, notes=None,
                 registered_at=None, checked_in_at=None):
        self.participant_id = participant_id
        self.event_id = event_id
        self.user_id = user_id
        self.registration_number = registration_number
        self.event_member_no = event_member_no
        self.category = category
        self.weight_class = weight_class
        self.status = status if isinstance(status, ParticipantStatus) else ParticipantStatus(status)
        self.notes = notes
        self.registered_at = registered_at or datetime.now()
        self.checked_in_at = checked_in_at

    def to_dict(self):
        """转换为字典"""
        return {
            'participant_id': self.participant_id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'registration_number': self.registration_number,
            'event_member_no': self.event_member_no,
            'category': self.category,
            'weight_class': self.weight_class,
            'status': self.status.value,
            'notes': self.notes,
            'registered_at': self.registered_at.isoformat() if self.registered_at else None,
            'checked_in_at': self.checked_in_at.isoformat() if self.checked_in_at else None
        }

class Score:
    """评分模型"""
    def __init__(self, score_id=None, participant_id=None, judge_id=None,
                 round_number=1, technique_score=0.0, performance_score=0.0,
                 deduction=0.0, total_score=0.0, notes=None,
                 scored_at=None, updated_at=None):
        self.score_id = score_id
        self.participant_id = participant_id
        self.judge_id = judge_id
        self.round_number = round_number
        self.technique_score = technique_score
        self.performance_score = performance_score
        self.deduction = deduction
        self.total_score = total_score or (technique_score + performance_score - deduction)
        self.notes = notes
        self.scored_at = scored_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def calculate_total(self):
        """计算总分"""
        self.total_score = self.technique_score + self.performance_score - self.deduction
        return self.total_score

    def to_dict(self):
        """转换为字典"""
        return {
            'score_id': self.score_id,
            'participant_id': self.participant_id,
            'judge_id': self.judge_id,
            'round_number': self.round_number,
            'technique_score': self.technique_score,
            'performance_score': self.performance_score,
            'deduction': self.deduction,
            'total_score': self.total_score,
            'notes': self.notes,
            'scored_at': self.scored_at.isoformat() if self.scored_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# 数据库表结构定义
DATABASE_SCHEMA = {
    'users': '''
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            real_name VARCHAR(100) NOT NULL,
            nickname VARCHAR(100),
            team_name VARCHAR(200),
            email VARCHAR(100) UNIQUE,
            phone VARCHAR(20),
            id_card VARCHAR(30) DEFAULT NULL COMMENT '身份证号',
            gender ENUM('male', 'female', 'other') DEFAULT NULL COMMENT '性别',
            birthdate DATE DEFAULT NULL COMMENT '出生日期',
            role ENUM('super_admin', 'admin', 'judge', 'user') DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            status ENUM('normal', 'abnormal', 'frozen') DEFAULT 'normal',
            password VARCHAR(100) DEFAULT NULL COMMENT '明文密码',
            password_hash VARBINARY(128) DEFAULT NULL COMMENT '密码哈希',
            deleted_at TIMESTAMP NULL DEFAULT NULL COMMENT '删除时间',
            INDEX idx_username (username),
            INDEX idx_role (role),
            INDEX idx_status (status),
            INDEX idx_phone (phone)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表（账号、基本资料、登录状态）';
    ''',
    
    'events': '''
        CREATE TABLE IF NOT EXISTS events (
            event_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            start_date DATETIME NOT NULL,
            end_date DATETIME NOT NULL,
            location VARCHAR(200),
            max_participants INT DEFAULT 100,
            registration_start_time DATETIME NULL,
            registration_deadline DATETIME NULL,
            status ENUM('draft', 'published', 'ongoing', 'completed', 'cancelled') DEFAULT 'draft',
            created_by INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            individual_fee DECIMAL(10,2) DEFAULT 0.00,
            pair_practice_fee DECIMAL(10,2) DEFAULT 0.00,
            team_competition_fee DECIMAL(10,2) DEFAULT 0.00,
            contact_phone VARCHAR(20),
            organizer VARCHAR(255),
            co_organizer VARCHAR(255),
            code VARCHAR(50),
            logo_url VARCHAR(500),
            is_public BOOLEAN DEFAULT TRUE,
            max_teams INT DEFAULT NULL,
            deleted_at TIMESTAMP NULL,
            FOREIGN KEY (created_by) REFERENCES users(user_id),
            INDEX idx_status (status),
            INDEX idx_start_date (start_date),
            INDEX idx_registration_start (registration_start_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='赛事表（基础信息与报名配置）';
    ''',
    
    'participants': '''
        CREATE TABLE IF NOT EXISTS participants (
            participant_id INT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL,
            user_id INT NOT NULL,
            registration_number VARCHAR(50) UNIQUE NOT NULL,
            event_member_no INT DEFAULT NULL,
            category VARCHAR(100),
            weight_class VARCHAR(50),
            gender VARCHAR(10),
            age_group VARCHAR(20),
            status ENUM('registered', 'checked_in', 'competing', 'completed', 'disqualified') DEFAULT 'registered',
            notes TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checked_in_at TIMESTAMP NULL,
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE KEY unique_event_user (event_id, user_id),
            UNIQUE KEY uniq_event_member_no (event_id, event_member_no),
            INDEX idx_event_status (event_id, status),
            INDEX idx_registration_number (registration_number),
            INDEX idx_event_registered_at (event_id, registered_at),
            INDEX idx_event_gender_age_group (event_id, gender, age_group)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='参赛者旧表（按赛事+用户记录参赛，含胸牌号与项目，已由 event_participants / entries 逐步替代）';
    ''',
    
    'scores': '''
        CREATE TABLE IF NOT EXISTS scores (
            score_id INT AUTO_INCREMENT PRIMARY KEY,
            participant_id INT NOT NULL,
            judge_id INT NOT NULL,
            round_number INT DEFAULT 1,
            technique_score DECIMAL(5,2) DEFAULT 0.00,
            performance_score DECIMAL(5,2) DEFAULT 0.00,
            deduction DECIMAL(5,2) DEFAULT 0.00,
            total_score DECIMAL(5,2) GENERATED ALWAYS AS (technique_score + performance_score - deduction) STORED,
            notes TEXT,
            scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            event_id INT NULL COMMENT '赛事ID',
            event_item_id INT NULL COMMENT '项目ID',
            entry_id BIGINT NULL COMMENT '报名条目ID',
            rank_in_round INT NULL COMMENT '本轮排名',
            is_valid BOOLEAN DEFAULT TRUE COMMENT '是否有效',
            judge_signature VARCHAR(100) COMMENT '裁判签名',
            modified_at DATETIME NULL COMMENT '最后修改时间',
            modified_by INT NULL COMMENT '修改人',
            modification_reason TEXT COMMENT '修改原因',
            version INT DEFAULT 1 COMMENT '版本号',
            FOREIGN KEY (participant_id) REFERENCES participants(participant_id) ON DELETE CASCADE,
            FOREIGN KEY (judge_id) REFERENCES users(user_id),
            UNIQUE KEY unique_participant_judge_round (participant_id, judge_id, round_number),
            INDEX idx_participant_round (participant_id, round_number),
            INDEX idx_judge (judge_id),
            INDEX idx_event_item_round (event_id, event_item_id, round_number),
            INDEX idx_entry_round (entry_id, round_number)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='成绩表（评分明细，关联参赛者、项目和报名条目）';
    ''',
    
    'notifications': '''
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sender_id INT NOT NULL,
            title VARCHAR(100) NOT NULL,
            content TEXT NOT NULL,
            recipient_type ENUM('all', 'role') DEFAULT 'all',
            roles VARCHAR(200) COMMENT '角色列表，逗号分隔',
            priority ENUM('normal', 'important', 'urgent') DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(user_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统通知模板表（面向全体或按角色发送的通知）';
    ''',
    
    'user_notifications': '''
        CREATE TABLE IF NOT EXISTS user_notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            notification_id INT NOT NULL,
            user_id INT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (notification_id) REFERENCES notifications(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            UNIQUE KEY unique_user_notification (notification_id, user_id),
            INDEX idx_user_read (user_id, is_read),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户通知收件表（通知与用户的映射及阅读状态）';
    ''',
    
    'announcements': '''
        CREATE TABLE IF NOT EXISTS announcements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL COMMENT '公告标题',
            content TEXT COMMENT '公告内容（可选，用于纯文本公告）',
            file_path VARCHAR(500) COMMENT '上传文件路径',
            file_name VARCHAR(255) COMMENT '原始文件名',
            file_size INT COMMENT '文件大小（字节）',
            file_type VARCHAR(50) COMMENT '文件类型',
            created_by INT NOT NULL COMMENT '创建者用户ID',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
            view_count INT DEFAULT 0 COMMENT '查看次数',
            FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE CASCADE,
            INDEX idx_created_at (created_at),
            INDEX idx_created_by (created_by),
            INDEX idx_is_active (is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知公告表（面向全体或按角色发送的公告）';
    ''',
    
    'teams': '''
        CREATE TABLE IF NOT EXISTS teams (
            team_id INT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL,
            team_name VARCHAR(200) NOT NULL,
            team_type VARCHAR(100),
            team_address VARCHAR(255),
            team_description TEXT,
            leader_id INT NULL,
            leader_name VARCHAR(100),
            leader_position VARCHAR(100),
            leader_phone VARCHAR(20),
            leader_email VARCHAR(100),
            status ENUM('draft', 'active', 'deleted') DEFAULT 'active',
            submitted_for_review TINYINT(1) DEFAULT 0 COMMENT '是否已提交审核',
            submitted_at DATETIME NULL COMMENT '最近提交时间',
            client_team_key VARCHAR(100) UNIQUE,
            created_by INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(user_id),
            FOREIGN KEY (leader_id) REFERENCES users(user_id),
            INDEX idx_event (event_id),
            INDEX idx_event_status (event_id, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='队伍表（代表队/俱乐部信息及报名主体）';
    ''',

    'submitted_team': '''
        CREATE TABLE IF NOT EXISTS submitted_team (
            team_id INT PRIMARY KEY,
            event_id INT NOT NULL,
            team_name VARCHAR(200) NOT NULL,
            team_type VARCHAR(100),
            team_address VARCHAR(255),
            team_description TEXT,
            leader_id INT NULL,
            leader_name VARCHAR(100),
            leader_position VARCHAR(100),
            leader_phone VARCHAR(20),
            leader_email VARCHAR(100),
            status ENUM('draft', 'active', 'deleted') DEFAULT 'active',
            submitted_for_review TINYINT(1) DEFAULT 0 COMMENT '是否已提交审核',
            submitted_at DATETIME NULL COMMENT '最近提交时间',
            client_team_key VARCHAR(100) UNIQUE,
            created_by INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(user_id),
            FOREIGN KEY (leader_id) REFERENCES users(user_id),
            UNIQUE KEY uk_event_team (event_id, team_id),
            INDEX idx_event (event_id),
            INDEX idx_event_status (event_id, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='已提交队伍快照表（提交时从 teams 复制一份只读快照）';
    ''',

    'team_applications': '''
        CREATE TABLE IF NOT EXISTS team_applications (
            application_id INT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL,
            team_id INT NULL,
            user_id INT NULL,
            applicant_name VARCHAR(100),
            applicant_phone VARCHAR(20),
            applicant_id_card VARCHAR(30),
            type ENUM('player', 'staff') NOT NULL DEFAULT 'player',
            role VARCHAR(50),
            position VARCHAR(100),
            team_name VARCHAR(200),
            event_name VARCHAR(200),
            competition_event VARCHAR(500),
            selected_events TEXT,
            status ENUM('pending', 'approved', 'rejected', 'cancelled') DEFAULT 'pending',
            submitted_by VARCHAR(100),
            submitted_at DATETIME,
            approved_by INT NULL,
            approved_at DATETIME,
            individual_fee DECIMAL(10,2) DEFAULT 0.00,
            pair_practice_fee DECIMAL(10,2) DEFAULT 0.00,
            team_competition_fee DECIMAL(10,2) DEFAULT 0.00,
            other_fee DECIMAL(10,2) DEFAULT 0.00,
            total_fee DECIMAL(10,2) DEFAULT 0.00,
            client_application_key VARCHAR(100) UNIQUE,
            extra_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (approved_by) REFERENCES users(user_id),
            INDEX idx_event_status (event_id, status),
            INDEX idx_user_event (user_id, event_id),
            INDEX idx_team_status (team_id, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='队伍报名申请旧表（队员、工作人员及费用申请记录，逐步由 entries 体系替代）';
    ''',

    'team_staff': '''
        CREATE TABLE IF NOT EXISTS team_staff (
            staff_id INT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL,
            team_id INT NOT NULL,
            user_id INT NULL,
            name VARCHAR(100) NOT NULL,
            gender VARCHAR(10),
            age INT,
            position VARCHAR(100),
            phone VARCHAR(20),
            id_card VARCHAR(30),
            status ENUM('active', 'inactive') DEFAULT 'active',
            source ENUM('direct', 'application') DEFAULT 'direct',
            client_staff_key VARCHAR(100) UNIQUE,
            extra_data TEXT,
            created_by INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (created_by) REFERENCES users(user_id),
            UNIQUE KEY uniq_staff_identity (event_id, team_id, id_card),
            INDEX idx_event_team (event_id, team_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='队伍工作人员旧表（教练和工作人员信息）';
    ''',

    'team_players': '''
        CREATE TABLE IF NOT EXISTS team_players (
            player_id INT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL,
            team_id INT NOT NULL,
            user_id INT NULL,
            participant_id INT NULL,
            name VARCHAR(100) NOT NULL,
            gender VARCHAR(10),
            age INT,
            phone VARCHAR(20),
            id_card VARCHAR(30),
            competition_event VARCHAR(500),
            selected_events TEXT,
            level VARCHAR(100),
            registration_number VARCHAR(50),
            pair_partner_name VARCHAR(100),
            pair_registered BOOLEAN DEFAULT FALSE,
            team_registered BOOLEAN DEFAULT FALSE,
            status ENUM('registered', 'approved', 'cancelled') DEFAULT 'registered',
            client_player_key VARCHAR(100) UNIQUE,
            extra_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (participant_id) REFERENCES participants(participant_id),
            UNIQUE KEY uniq_player_identity (event_id, team_id, id_card),
            INDEX idx_event_team (event_id, team_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='队员旧表（队伍成员与所报项目的旧结构）';
    ''',

    'team_drafts': '''
        CREATE TABLE IF NOT EXISTS team_drafts (
            draft_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            event_id INT NOT NULL,
            team_name VARCHAR(200),
            team_type VARCHAR(100),
            team_address VARCHAR(255),
            team_description TEXT,
            leader_name VARCHAR(100),
            leader_position VARCHAR(100),
            leader_phone VARCHAR(20),
            leader_email VARCHAR(100),
            client_team_key VARCHAR(100),
            is_submitted BOOLEAN DEFAULT FALSE,
            extra_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            UNIQUE KEY uniq_user_event (user_id, event_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='队伍报名草稿旧表（未正式提交的队伍信息与人员草稿）';
    ''',
    'event_items': '''
        CREATE TABLE IF NOT EXISTS event_items (
            event_item_id INT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL COMMENT '赛事ID',
            name VARCHAR(200) NOT NULL COMMENT '项目名称',
            code VARCHAR(50) COMMENT '项目编码',
            description TEXT COMMENT '项目说明',
            type ENUM('individual', 'pair', 'team') NOT NULL COMMENT '项目类型',
            gender_limit ENUM('male', 'female', 'mixed') COMMENT '性别限制',
            min_age INT COMMENT '最小年龄',
            max_age INT COMMENT '最大年龄',
            weight_class VARCHAR(50) COMMENT '体重级别',
            min_members INT COMMENT '最少人数',
            max_members INT COMMENT '最多人数',
            max_entries INT COMMENT '最大报名数',
            equipment_required VARCHAR(200) COMMENT '器械要求',
            rounds INT DEFAULT 1 COMMENT '比赛轮次',
            scoring_mode ENUM('sum', 'avg', 'drop_high_low') DEFAULT 'sum' COMMENT '计分模式',
            sort_order INT DEFAULT 0 COMMENT '排序权重',
            is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            INDEX idx_event (event_id),
            INDEX idx_event_type (event_id, type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='赛事项目表（新结构，按赛事+项目记录比赛设置）';
    ''',

    'event_participants': '''
        CREATE TABLE IF NOT EXISTS event_participants (
            event_participant_id INT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL COMMENT '赛事ID',
            user_id INT NOT NULL COMMENT '用户ID',
            team_id INT NULL COMMENT '队伍ID',
            role ENUM('athlete', 'coach', 'staff', 'judge', 'official') DEFAULT 'athlete' COMMENT '角色',
            event_member_no INT COMMENT '赛事编号',
            status ENUM('registered', 'checked_in', 'withdrawn', 'disqualified') DEFAULT 'registered' COMMENT '状态',
            notes TEXT COMMENT '备注',
            registered_at DATETIME COMMENT '注册时间',
            checked_in_at DATETIME COMMENT '签到时间',
            FOREIGN KEY (event_id) REFERENCES events(event_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            UNIQUE KEY uk_event_user_role (event_id, user_id, role),
            UNIQUE KEY uk_event_member_no (event_id, event_member_no),
            INDEX idx_event_role (event_id, role),
            INDEX idx_event_status (event_id, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='赛事参与者表（新结构，按赛事+用户+角色记录参与者信息）';
    ''',

    'entries': '''
        CREATE TABLE IF NOT EXISTS entries (
            entry_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL COMMENT '赛事ID',
            event_item_id INT NOT NULL COMMENT '项目ID',
            team_id INT NULL COMMENT '队伍ID',
            entry_type ENUM('individual', 'pair', 'team') NOT NULL COMMENT '类型',
            registration_number VARCHAR(50) UNIQUE NOT NULL COMMENT '报名编号',
            status ENUM('registered', 'checked_in', 'late_checked_in', 'competing', 'completed', 'withdrawn', 'disqualified') DEFAULT 'registered' COMMENT '状态',
            checked_in_at DATETIME COMMENT '报到时间',
            late_checkin_at DATETIME COMMENT '补签时间',
            late_checkin_by INT COMMENT '补签操作人',
            late_checkin_reason TEXT COMMENT '补签原因',
            late_checkin_penalty DECIMAL(10,2) DEFAULT 0 COMMENT '补签罚款',
            individual_fee DECIMAL(10,2) DEFAULT 0 COMMENT '个人项目费',
            pair_fee DECIMAL(10,2) DEFAULT 0 COMMENT '对练项目费',
            team_fee DECIMAL(10,2) DEFAULT 0 COMMENT '团体项目费',
            other_fee DECIMAL(10,2) DEFAULT 0 COMMENT '其他费用',
            total_fee DECIMAL(10,2) DEFAULT 0 COMMENT '总费用',
            payment_status ENUM('unpaid', 'partial', 'paid', 'refunded') DEFAULT 'unpaid' COMMENT '支付状态',
            paid_amount DECIMAL(10,2) DEFAULT 0 COMMENT '已付金额',
            payment_time DATETIME COMMENT '支付时间',
            withdrawn_reason TEXT COMMENT '退赛原因',
            created_by INT COMMENT '创建人',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            FOREIGN KEY (event_id) REFERENCES events(event_id),
            FOREIGN KEY (event_item_id) REFERENCES event_items(event_item_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            FOREIGN KEY (late_checkin_by) REFERENCES users(user_id),
            FOREIGN KEY (created_by) REFERENCES users(user_id),
            INDEX idx_event_item (event_id, event_item_id),
            INDEX idx_team (event_id, team_id),
            INDEX idx_status (event_id, status),
            INDEX idx_event_item_status (event_id, event_item_id, status),
            INDEX idx_team_status (team_id, status),
            INDEX idx_registration_number (registration_number),
            INDEX idx_checkin_status (event_id, status, checked_in_at),
            INDEX idx_late_checkin (event_id, late_checkin_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报名条目表（新结构，按赛事+项目+队伍记录报名信息）';
    ''',

    'entry_members': '''
        CREATE TABLE IF NOT EXISTS entry_members (
            entry_member_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            entry_id BIGINT NOT NULL COMMENT '报名条目ID',
            user_id INT NOT NULL COMMENT '用户ID',
            role ENUM('main', 'substitute') DEFAULT 'main' COMMENT '角色',
            order_in_entry INT COMMENT '顺序',
            FOREIGN KEY (entry_id) REFERENCES entries(entry_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE KEY uk_entry_user (entry_id, user_id),
            INDEX idx_entry (entry_id),
            INDEX idx_user (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报名成员表（新结构，按报名条目+用户记录成员信息）';
    ''',

    'entry_schedules': '''
        CREATE TABLE IF NOT EXISTS entry_schedules (
            schedule_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL COMMENT '赛事ID',
            event_item_id INT NOT NULL COMMENT '项目ID',
            entry_id BIGINT NOT NULL COMMENT '报名条目ID',
            group_label VARCHAR(50) COMMENT '组别标识',
            group_no INT NOT NULL COMMENT '组号',
            sequence_no INT NOT NULL COMMENT '出场序号',
            global_sequence_no INT COMMENT '全局序号',
            venue VARCHAR(100) COMMENT '场地',
            scheduled_time DATETIME COMMENT '预计时间',
            actual_start_time DATETIME COMMENT '实际开始',
            actual_end_time DATETIME COMMENT '实际结束',
            status ENUM('pending', 'ready', 'in_progress', 'completed', 'skipped') DEFAULT 'pending' COMMENT '编排状态',
            is_manually_adjusted BOOLEAN DEFAULT FALSE COMMENT '是否手动调整',
            adjusted_by INT COMMENT '调整人',
            adjusted_at DATETIME COMMENT '调整时间',
            adjustment_reason TEXT COMMENT '调整原因',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            FOREIGN KEY (event_id) REFERENCES events(event_id),
            FOREIGN KEY (event_item_id) REFERENCES event_items(event_item_id),
            FOREIGN KEY (entry_id) REFERENCES entries(entry_id),
            FOREIGN KEY (adjusted_by) REFERENCES users(user_id),
            UNIQUE KEY uk_item_entry (event_item_id, entry_id),
            INDEX idx_item_group_seq (event_item_id, group_no, sequence_no),
            INDEX idx_item_global_seq (event_item_id, global_sequence_no),
            INDEX idx_scheduled_time (scheduled_time),
            INDEX idx_status (event_item_id, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='比赛编排表（新结构，按项目+报名条目记录比赛编排信息）';
    ''',

    'schedule_adjustment_logs': '''
        CREATE TABLE IF NOT EXISTS schedule_adjustment_logs (
            schedule_log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            event_item_id INT NOT NULL COMMENT '项目ID',
            entry_id BIGINT NOT NULL COMMENT '报名条目ID',
            old_group_no INT COMMENT '原组号',
            new_group_no INT COMMENT '新组号',
            old_sequence_no INT COMMENT '原序号',
            new_sequence_no INT COMMENT '新序号',
            old_global_sequence_no INT COMMENT '原全局序号',
            new_global_sequence_no INT COMMENT '新全局序号',
            adjustment_type ENUM('manual', 'auto', 'swap') COMMENT '调整类型',
            reason TEXT COMMENT '调整原因',
            adjusted_by INT NOT NULL COMMENT '操作人',
            adjusted_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '调整时间',
            FOREIGN KEY (event_item_id) REFERENCES event_items(event_item_id),
            FOREIGN KEY (entry_id) REFERENCES entries(entry_id),
            FOREIGN KEY (adjusted_by) REFERENCES users(user_id),
            INDEX idx_item_time (event_item_id, adjusted_at),
            INDEX idx_entry (entry_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='编排调整历史表（新结构，按项目+报名条目记录编排调整历史）';
    ''',

    'score_modification_logs': '''
        CREATE TABLE IF NOT EXISTS score_modification_logs (
            score_log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            score_id INT NOT NULL COMMENT '成绩ID',
            event_id INT NOT NULL COMMENT '赛事ID',
            entry_id BIGINT NULL COMMENT '报名条目ID',
            judge_id INT NOT NULL COMMENT '裁判ID',
            round_no INT NOT NULL COMMENT '轮次',
            old_technique_score DECIMAL(5,2) COMMENT '原技术分',
            new_technique_score DECIMAL(5,2) COMMENT '新技术分',
            old_performance_score DECIMAL(5,2) COMMENT '原表现分',
            new_performance_score DECIMAL(5,2) COMMENT '新表现分',
            old_deduction DECIMAL(5,2) COMMENT '原扣分',
            new_deduction DECIMAL(5,2) COMMENT '新扣分',
            old_total_score DECIMAL(5,2) COMMENT '原总分',
            new_total_score DECIMAL(5,2) COMMENT '新总分',
            modification_type ENUM('correction', 'tie_break', 'adjustment') NOT NULL COMMENT '修改类型',
            reason TEXT NOT NULL COMMENT '修改原因',
            modified_by INT NOT NULL COMMENT '修改人',
            modified_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '修改时间',
            FOREIGN KEY (score_id) REFERENCES scores(score_id),
            FOREIGN KEY (event_id) REFERENCES events(event_id),
            FOREIGN KEY (entry_id) REFERENCES entries(entry_id),
            FOREIGN KEY (judge_id) REFERENCES users(user_id),
            FOREIGN KEY (modified_by) REFERENCES users(user_id),
            INDEX idx_score (score_id),
            INDEX idx_entry_time (entry_id, modified_at),
            INDEX idx_event (event_id),
            INDEX idx_judge (judge_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='成绩修改历史表（新结构，按成绩+报名条目记录成绩修改历史）';
    ''',

    'payment_records': '''
        CREATE TABLE IF NOT EXISTS payment_records (
            payment_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL COMMENT '赛事ID',
            team_id INT NOT NULL COMMENT '队伍ID',
            entry_id BIGINT NULL COMMENT '报名条目ID',
            amount DECIMAL(10,2) NOT NULL COMMENT '金额',
            payment_type ENUM('registration', 'additional', 'refund') DEFAULT 'registration' COMMENT '支付类型',
            payment_method ENUM('cash', 'transfer', 'wechat', 'alipay', 'other') COMMENT '支付方式',
            transaction_no VARCHAR(100) COMMENT '交易流水号',
            paid_at DATETIME COMMENT '支付时间',
            created_by INT COMMENT '创建人',
            notes TEXT COMMENT '备注',
            FOREIGN KEY (event_id) REFERENCES events(event_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            FOREIGN KEY (entry_id) REFERENCES entries(entry_id),
            FOREIGN KEY (created_by) REFERENCES users(user_id),
            INDEX idx_team_payment (team_id, paid_at),
            INDEX idx_event (event_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付记录表（新结构，按赛事+队伍+报名条目记录支付信息）';
    ''',

    'maintenance_logs': '''
        CREATE TABLE IF NOT EXISTS maintenance_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            operation VARCHAR(50) NOT NULL COMMENT '操作类型：backup, optimize, cleanup等',
            details TEXT COMMENT '操作详情',
            status ENUM('success', 'failed') DEFAULT 'success',
            error_message TEXT COMMENT '错误信息',
            ip_address VARCHAR(50) COMMENT 'IP地址',
            file_size DECIMAL(10,2) COMMENT '相关文件大小(MB)',
            duration DECIMAL(10,2) COMMENT '操作耗时(秒)',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            INDEX idx_operation (operation),
            INDEX idx_created_at (created_at),
            INDEX idx_user_id (user_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='运维操作日志表（记录系统维护操作日志）';
    '''
}
