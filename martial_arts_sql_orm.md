# 武术赛事管理系统 - 建表SQL与ORM模型

> **数据库**: MySQL 8.0+  
> **ORM**: SQLAlchemy 2.0+  
> **Python**: 3.10+

---

## 0. 与当前 `wu_shu` 数据库及代码实现的关系

- 当前运行系统使用 `config.Config.DB_NAME` 中配置的 `wu_shu` 数据库，并通过 `database.DatabaseManager` + `mysql.connector` 直接执行 SQL；表结构由 `models.DATABASE_SCHEMA` 定义并在启动时自动创建/迁移，而**没有**使用 SQLAlchemy。
- 本文中的 `CREATE DATABASE martial_arts ...` 及后续建表 SQL / 视图 / 触发器，是面向重构后的标准化数据库设计，与现有 `wu_shu` 库大致有如下映射关系：
  - `martial_arts.users` ←→ 现有 `wu_shu.users`：目标表新增 `password_hash`、`id_card`、`gender`、`birthdate` 等字段，并采用加密存储密码；当前实现仅有明文 `password` 字段，重构时需要在旧表上加列并迁移数据，最终废弃明文密码。
  - `martial_arts.events` ←→ 现有 `wu_shu.events`：字段更规范（`code`、`logo_url`、`start_time` / `end_time`、`pair_fee` / `team_fee` 等），现有表仅有 `start_date` / `end_date`、`individual_fee`、`pair_practice_fee`、`team_competition_fee` 等，需要通过 `ALTER TABLE` 逐步对齐命名和含义。
  - `martial_arts.event_participants` + `entries` + `entry_members` ←→ 现有 `wu_shu.participants` + `team_players`：当前系统将“参赛身份 + 报名条目 + 条目成员”混在少数几张表中，目标方案将其拆为胸牌层 (`event_participants`)、报名条目层 (`entries`) 和条目成员层 (`entry_members`) 三个层级。
  - `martial_arts.scores` + `score_modification_logs` ←→ 现有 `wu_shu.scores`：目标表增加 `event_id`、`event_item_id`、`entry_id`、修改历史等字段，支持成绩修改审计和复杂排名；现有表只依赖 `participant_id`，需要通过新增列或建立新表来演进。
  - `martial_arts.teams` + `team_members` + `payment_records` ←→ 现有 `wu_shu.teams` + `team_staff` + `team_applications` 等：目标结构统一管理队伍成员和费用流水，替代当前分裂的多张表。
- 在现有项目中启用本 SQL 方案有两条典型演进路径：
  - **新库并行方案**：在同一 MySQL 实例中创建独立的 `martial_arts` 库，使用 SQLAlchemy 连接该库，并按模块（报名、编排、成绩等）逐步将读写逻辑从旧的 `DatabaseManager` 迁移到 ORM 层；迁移期间通过同步脚本或视图保持两库数据一致。
  - **原库演进方案**：直接在 `wu_shu` 上按本文件的 DDL 逐步执行 `ALTER TABLE` / `ADD COLUMN` / `ADD INDEX` / `CREATE VIEW` / `CREATE TRIGGER` 等操作，使现有库的结构逼近 `martial_arts` 设计；完成结构收敛后，再将 Python 侧的访问从 `mysql.connector` 切换到 SQLAlchemy Session。

因此，在阅读本文件时，应将其视为**重构后的目标库定义**，并结合上面列出的映射关系与迁移路径，规划从当前实现平滑演进到 SQLAlchemy ORM 架构的具体步骤。

## 第一部分：完整建表SQL

### 1. 创建数据库

```sql
CREATE DATABASE IF NOT EXISTS martial_arts 
  DEFAULT CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

USE martial_arts;
```

---

### 2. 用户表 (users)

```sql
CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
  username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
  password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
  real_name VARCHAR(100) NOT NULL COMMENT '真实姓名',
  nickname VARCHAR(100) COMMENT '昵称',
  email VARCHAR(100) UNIQUE COMMENT '邮箱',
  phone VARCHAR(20) COMMENT '手机号',
  id_card VARCHAR(30) COMMENT '身份证号',
  gender ENUM('male', 'female', 'other') COMMENT '性别',
  birthdate DATE COMMENT '出生日期',
  role ENUM('super_admin', 'admin', 'judge', 'coach', 'athlete', 'staff', 'user') 
    DEFAULT 'user' COMMENT '角色',
  status ENUM('normal', 'abnormal', 'frozen') DEFAULT 'normal' COMMENT '状态',
  is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  deleted_at DATETIME NULL COMMENT '删除时间',
  
  INDEX idx_role (role),
  INDEX idx_phone (phone),
  INDEX idx_id_card (id_card),
  INDEX idx_real_name (real_name),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';
```

---

### 3. 赛事表 (events)

```sql
CREATE TABLE events (
  id INT PRIMARY KEY AUTO_INCREMENT COMMENT '赛事ID',
  code VARCHAR(50) UNIQUE NOT NULL COMMENT '赛事编号',
  name VARCHAR(200) NOT NULL COMMENT '赛事名称',
  description TEXT COMMENT '赛事描述',
  organizer VARCHAR(200) COMMENT '主办方',
  location VARCHAR(200) COMMENT '比赛地点',
  logo_url VARCHAR(500) COMMENT 'Logo地址',
  
  start_time DATETIME NOT NULL COMMENT '开始时间',
  end_time DATETIME NOT NULL COMMENT '结束时间',
  registration_start DATETIME COMMENT '报名开始',
  registration_end DATETIME COMMENT '报名截止',
  
  status ENUM('draft', 'published', 'ongoing', 'completed', 'cancelled') 
    DEFAULT 'draft' COMMENT '状态',
  is_public BOOLEAN DEFAULT TRUE COMMENT '是否公开',
  max_teams INT COMMENT '最大队伍数',
  
  individual_fee DECIMAL(10,2) DEFAULT 0 COMMENT '个人项目费用',
  pair_fee DECIMAL(10,2) DEFAULT 0 COMMENT '对练项目费用',
  team_fee DECIMAL(10,2) DEFAULT 0 COMMENT '团体项目费用',
  
  created_by INT NOT NULL COMMENT '创建人',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  deleted_at DATETIME NULL COMMENT '删除时间',
  
  FOREIGN KEY (created_by) REFERENCES users(id),
  INDEX idx_status (status),
  INDEX idx_start_time (start_time),
  INDEX idx_registration (registration_start, registration_end),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='赛事表';
```

---

### 4. 赛事项目表 (event_items)

```sql
CREATE TABLE event_items (
  id INT PRIMARY KEY AUTO_INCREMENT COMMENT '项目ID',
  event_id INT NOT NULL COMMENT '所属赛事',
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
  
  FOREIGN KEY (event_id) REFERENCES events(id),
  INDEX idx_event (event_id),
  INDEX idx_event_type (event_id, type),
  
  CHECK (min_age IS NULL OR max_age IS NULL OR min_age <= max_age)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='赛事项目表';
```

---

### 5. 队伍表 (teams)

```sql
CREATE TABLE teams (
  id INT PRIMARY KEY AUTO_INCREMENT COMMENT '队伍ID',
  event_id INT NOT NULL COMMENT '所属赛事',
  name VARCHAR(200) NOT NULL COMMENT '队伍名称',
  short_name VARCHAR(50) COMMENT '简称',
  team_type VARCHAR(100) COMMENT '类型',
  address VARCHAR(255) COMMENT '地址',
  
  leader_id INT COMMENT '领队用户ID',
  leader_name VARCHAR(100) COMMENT '领队姓名',
  leader_phone VARCHAR(20) COMMENT '领队电话',
  
  status ENUM('draft', 'active', 'withdrawn', 'deleted') DEFAULT 'active' COMMENT '状态',
  client_team_key VARCHAR(100) UNIQUE COMMENT '前端缓存key',
  
  created_by INT NOT NULL COMMENT '创建人',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  deleted_at DATETIME NULL COMMENT '删除时间',
  
  FOREIGN KEY (event_id) REFERENCES events(id),
  FOREIGN KEY (leader_id) REFERENCES users(id),
  FOREIGN KEY (created_by) REFERENCES users(id),
  INDEX idx_event (event_id),
  INDEX idx_event_status (event_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='队伍表';
```

---

### 6. 队伍成员表 (team_members)

```sql
CREATE TABLE team_members (
  id INT PRIMARY KEY AUTO_INCREMENT COMMENT '成员ID',
  event_id INT NOT NULL COMMENT '赛事ID',
  team_id INT NOT NULL COMMENT '队伍ID',
  user_id INT NOT NULL COMMENT '用户ID',
  member_role ENUM('athlete', 'coach', 'staff', 'leader') NOT NULL COMMENT '角色',
  position VARCHAR(100) COMMENT '职务',
  jersey_no VARCHAR(20) COMMENT '号码',
  status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态',
  source ENUM('direct', 'application') DEFAULT 'direct' COMMENT '来源',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  FOREIGN KEY (event_id) REFERENCES events(id),
  FOREIGN KEY (team_id) REFERENCES teams(id),
  FOREIGN KEY (user_id) REFERENCES users(id),
  UNIQUE KEY uk_event_team_user_role (event_id, team_id, user_id, member_role),
  INDEX idx_event_team (event_id, team_id),
  INDEX idx_user_role (user_id, member_role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='队伍成员表';
```

---

### 7. 赛事参与者表 (event_participants)

```sql
CREATE TABLE event_participants (
  id INT PRIMARY KEY AUTO_INCREMENT COMMENT '参与者ID',
  event_id INT NOT NULL COMMENT '赛事ID',
  user_id INT NOT NULL COMMENT '用户ID',
  team_id INT COMMENT '队伍ID',
  role ENUM('athlete', 'coach', 'staff', 'judge', 'official') DEFAULT 'athlete' COMMENT '角色',
  event_member_no INT COMMENT '赛事编号',
  status ENUM('registered', 'checked_in', 'withdrawn', 'disqualified') 
    DEFAULT 'registered' COMMENT '状态',
  notes TEXT COMMENT '备注',
  registered_at DATETIME COMMENT '注册时间',
  checked_in_at DATETIME COMMENT '签到时间',
  
  FOREIGN KEY (event_id) REFERENCES events(id),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (team_id) REFERENCES teams(id),
  UNIQUE KEY uk_event_user_role (event_id, user_id, role),
  UNIQUE KEY uk_event_member_no (event_id, event_member_no),
  INDEX idx_event_role (event_id, role),
  INDEX idx_event_status (event_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='赛事参与者表';
```

---

### 8. 报名条目表 (entries)

```sql
CREATE TABLE entries (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '报名ID',
  event_id INT NOT NULL COMMENT '赛事ID',
  event_item_id INT NOT NULL COMMENT '项目ID',
  team_id INT COMMENT '队伍ID',
  entry_type ENUM('individual', 'pair', 'team') NOT NULL COMMENT '类型',
  registration_number VARCHAR(50) UNIQUE NOT NULL COMMENT '报名编号',
  
  status ENUM('registered', 'checked_in', 'late_checked_in', 'competing', 
              'completed', 'withdrawn', 'disqualified') 
    DEFAULT 'registered' COMMENT '状态',
  
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
  
  FOREIGN KEY (event_id) REFERENCES events(id),
  FOREIGN KEY (event_item_id) REFERENCES event_items(id),
  FOREIGN KEY (team_id) REFERENCES teams(id),
  FOREIGN KEY (late_checkin_by) REFERENCES users(id),
  FOREIGN KEY (created_by) REFERENCES users(id),
  
  INDEX idx_event_item (event_id, event_item_id),
  INDEX idx_team (event_id, team_id),
  INDEX idx_status (event_id, status),
  INDEX idx_event_item_status (event_id, event_item_id, status),
  INDEX idx_team_status (team_id, status),
  INDEX idx_registration_number (registration_number),
  INDEX idx_checkin_status (event_id, status, checked_in_at),
  INDEX idx_late_checkin (event_id, late_checkin_at),
  
  CHECK (
    (entry_type = 'individual' AND pair_fee = 0 AND team_fee = 0) OR
    (entry_type = 'pair' AND individual_fee = 0 AND team_fee = 0) OR
    (entry_type = 'team' AND individual_fee = 0 AND pair_fee = 0)
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报名条目表';
```

---

### 9. 报名成员表 (entry_members)

```sql
CREATE TABLE entry_members (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '成员ID',
  entry_id BIGINT NOT NULL COMMENT '报名条目ID',
  user_id INT NOT NULL COMMENT '用户ID',
  role ENUM('main', 'substitute') DEFAULT 'main' COMMENT '角色',
  order_in_entry INT COMMENT '顺序',
  
  FOREIGN KEY (entry_id) REFERENCES entries(id),
  FOREIGN KEY (user_id) REFERENCES users(id),
  UNIQUE KEY uk_entry_user (entry_id, user_id),
  INDEX idx_entry (entry_id),
  INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报名成员表';
```

---

### 10. 比赛编排表 (entry_schedules)

```sql
CREATE TABLE entry_schedules (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '编排ID',
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
  
  status ENUM('pending', 'ready', 'in_progress', 'completed', 'skipped') 
    DEFAULT 'pending' COMMENT '编排状态',
  
  is_manually_adjusted BOOLEAN DEFAULT FALSE COMMENT '是否手动调整',
  adjusted_by INT COMMENT '调整人',
  adjusted_at DATETIME COMMENT '调整时间',
  adjustment_reason TEXT COMMENT '调整原因',
  
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  FOREIGN KEY (event_id) REFERENCES events(id),
  FOREIGN KEY (event_item_id) REFERENCES event_items(id),
  FOREIGN KEY (entry_id) REFERENCES entries(id),
  FOREIGN KEY (adjusted_by) REFERENCES users(id),
  
  UNIQUE KEY uk_item_entry (event_item_id, entry_id),
  INDEX idx_item_group_seq (event_item_id, group_no, sequence_no),
  INDEX idx_item_global_seq (event_item_id, global_sequence_no),
  INDEX idx_scheduled_time (scheduled_time),
  INDEX idx_status (event_item_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='比赛编排表';
```

---

### 11. 编排调整历史表 (schedule_adjustment_logs)

```sql
CREATE TABLE schedule_adjustment_logs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '日志ID',
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
  
  FOREIGN KEY (event_item_id) REFERENCES event_items(id),
  FOREIGN KEY (entry_id) REFERENCES entries(id),
  FOREIGN KEY (adjusted_by) REFERENCES users(id),
  
  INDEX idx_item_time (event_item_id, adjusted_at),
  INDEX idx_entry (entry_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='编排调整历史';
```

---

### 12. 成绩记录表 (scores) - 支持修改功能

```sql
CREATE TABLE scores (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '成绩ID',
  event_id INT NOT NULL COMMENT '赛事ID',
  event_item_id INT NOT NULL COMMENT '项目ID',
  entry_id BIGINT NOT NULL COMMENT '报名条目ID',
  judge_id INT NOT NULL COMMENT '裁判ID',
  round_no INT DEFAULT 1 COMMENT '轮次',
  
  technique_score DECIMAL(5,2) DEFAULT 0 COMMENT '技术分',
  performance_score DECIMAL(5,2) DEFAULT 0 COMMENT '表现分',
  deduction DECIMAL(5,2) DEFAULT 0 COMMENT '扣分',
  total_score DECIMAL(5,2) COMMENT '总分',
  rank_in_round INT COMMENT '该轮排名',
  
  is_valid BOOLEAN DEFAULT TRUE COMMENT '是否有效',
  judge_signature VARCHAR(100) COMMENT '裁判签名',
  notes TEXT COMMENT '备注',
  
  scored_at DATETIME COMMENT '初次打分时间',
  modified_at DATETIME COMMENT '最后修改时间',
  modified_by INT COMMENT '修改操作人',
  modification_reason TEXT COMMENT '修改原因',
  version INT DEFAULT 1 COMMENT '版本号(乐观锁)',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  FOREIGN KEY (event_id) REFERENCES events(id),
  FOREIGN KEY (event_item_id) REFERENCES event_items(id),
  FOREIGN KEY (entry_id) REFERENCES entries(id),
  FOREIGN KEY (judge_id) REFERENCES users(id),
  FOREIGN KEY (modified_by) REFERENCES users(id),
  
  UNIQUE KEY uk_entry_judge_round (entry_id, judge_id, round_no),
  INDEX idx_event_item_round (event_id, event_item_id, round_no),
  INDEX idx_judge (judge_id),
  INDEX idx_entry_round (entry_id, round_no),
  INDEX idx_scored_at (scored_at),
  INDEX idx_modified (modified_at),
  
  CHECK (technique_score >= 0 AND performance_score >= 0 AND deduction >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='成绩记录表';
```

---

### 13. 成绩修改历史表 (score_modification_logs)

```sql
CREATE TABLE score_modification_logs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '日志ID',
  score_id BIGINT NOT NULL COMMENT '成绩ID',
  event_id INT NOT NULL COMMENT '赛事ID',
  entry_id BIGINT NOT NULL COMMENT '报名条目ID',
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
  
  FOREIGN KEY (score_id) REFERENCES scores(id),
  FOREIGN KEY (event_id) REFERENCES events(id),
  FOREIGN KEY (entry_id) REFERENCES entries(id),
  FOREIGN KEY (judge_id) REFERENCES users(id),
  FOREIGN KEY (modified_by) REFERENCES users(id),
  
  INDEX idx_score (score_id),
  INDEX idx_entry_time (entry_id, modified_at),
  INDEX idx_event (event_id),
  INDEX idx_judge (judge_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='成绩修改历史表';
```

---

### 14. 支付记录表 (payment_records)

```sql
CREATE TABLE payment_records (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
  event_id INT NOT NULL COMMENT '赛事ID',
  team_id INT NOT NULL COMMENT '队伍ID',
  entry_id BIGINT COMMENT '报名条目ID',
  
  amount DECIMAL(10,2) NOT NULL COMMENT '金额',
  payment_type ENUM('registration', 'additional', 'refund') 
    DEFAULT 'registration' COMMENT '支付类型',
  payment_method ENUM('cash', 'transfer', 'wechat', 'alipay', 'other') COMMENT '支付方式',
  transaction_no VARCHAR(100) COMMENT '交易流水号',
  
  paid_at DATETIME COMMENT '支付时间',
  created_by INT COMMENT '创建人',
  notes TEXT COMMENT '备注',
  
  FOREIGN KEY (event_id) REFERENCES events(id),
  FOREIGN KEY (team_id) REFERENCES teams(id),
  FOREIGN KEY (entry_id) REFERENCES entries(id),
  FOREIGN KEY (created_by) REFERENCES users(id),
  
  INDEX idx_team_payment (team_id, paid_at),
  INDEX idx_event (event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付记录表';
```

---

### 15. 创建视图

```sql
-- 报名统计视图
CREATE VIEW v_entry_statistics AS
SELECT 
  e.event_id,
  e.team_id,
  t.name AS team_name,
  COUNT(DISTINCT e.id) AS total_entries,
  SUM(e.total_fee) AS total_fee,
  SUM(e.paid_amount) AS paid_amount,
  COUNT(DISTINCT em.user_id) AS total_athletes
FROM entries e
LEFT JOIN teams t ON e.team_id = t.id
LEFT JOIN entry_members em ON e.id = em.entry_id
WHERE e.deleted_at IS NULL
GROUP BY e.event_id, e.team_id;

-- 成绩排名视图（处理同分情况）
CREATE VIEW v_scores_ranking AS
SELECT 
  s.event_item_id,
  s.entry_id,
  e.registration_number,
  AVG(s.total_score) AS avg_score,
  MAX(s.technique_score) AS max_technique_score,
  RANK() OVER (
    PARTITION BY s.event_item_id 
    ORDER BY AVG(s.total_score) DESC, MAX(s.technique_score) DESC
  ) AS ranking
FROM scores s
JOIN entries e ON s.entry_id = e.id
WHERE s.is_valid = TRUE
GROUP BY s.event_item_id, s.entry_id;

-- 裁判统计视图
CREATE VIEW v_judge_statistics AS
SELECT 
  u.id AS judge_id,
  u.real_name AS judge_name,
  COUNT(DISTINCT s.event_id) AS events_participated,
  COUNT(DISTINCT s.event_item_id) AS items_judged,
  COUNT(s.id) AS total_scores_given,
  AVG(s.total_score) AS avg_score_given,
  COUNT(sml.id) AS total_modifications
FROM users u
LEFT JOIN scores s ON u.id = s.judge_id AND s.is_valid = TRUE
LEFT JOIN score_modification_logs sml ON u.id = sml.judge_id
WHERE u.role = 'judge' AND u.is_active = TRUE
GROUP BY u.id;

-- 补签记录视图
CREATE VIEW v_late_checkin_records AS
SELECT 
  e.id AS entry_id,
  e.registration_number,
  e.event_id,
  ev.name AS event_name,
  e.event_item_id,
  ei.name AS item_name,
  e.late_checkin_at,
  u.real_name AS operator_name,
  e.late_checkin_reason,
  e.late_checkin_penalty,
  GROUP_CONCAT(u2.real_name SEPARATOR ',') AS athlete_names
FROM entries e
JOIN events ev ON e.event_id = ev.id
JOIN event_items ei ON e.event_item_id = ei.id
LEFT JOIN users u ON e.late_checkin_by = u.id
LEFT JOIN entry_members em ON e.id = em.entry_id
LEFT JOIN users u2 ON em.user_id = u2.id
WHERE e.status = 'late_checked_in'
GROUP BY e.id
ORDER BY e.late_checkin_at DESC;

-- 编排详情视图
CREATE VIEW v_entry_schedule_detail AS
SELECT 
  es.id AS schedule_id,
  es.event_item_id,
  ei.name AS item_name,
  es.entry_id,
  e.registration_number,
  es.group_no,
  es.group_label,
  es.sequence_no,
  es.global_sequence_no,
  es.venue,
  es.scheduled_time,
  es.status,
  es.is_manually_adjusted,
  GROUP_CONCAT(u.real_name ORDER BY em.order_in_entry SEPARATOR ',') AS athlete_names,
  t.name AS team_name,
  es.adjusted_by,
  u2.real_name AS adjuster_name,
  es.adjusted_at,
  es.adjustment_reason
FROM entry_schedules es
JOIN event_items ei ON es.event_item_id = ei.id
JOIN entries e ON es.entry_id = e.id
LEFT JOIN teams t ON e.team_id = t.id
LEFT JOIN entry_members em ON e.id = em.entry_id
LEFT JOIN users u ON em.user_id = u.id
LEFT JOIN users u2 ON es.adjusted_by = u2.id
GROUP BY es.id
ORDER BY es.event_item_id, es.group_no, es.sequence_no;
```

---

### 16. 创建触发器

```sql
-- 自动计算总费用 (INSERT)
DELIMITER $
CREATE TRIGGER trg_entries_total_fee 
BEFORE INSERT ON entries
FOR EACH ROW
BEGIN
  SET NEW.total_fee = NEW.individual_fee + NEW.pair_fee + NEW.team_fee + NEW.other_fee;
END$

-- 自动计算总费用 (UPDATE)
CREATE TRIGGER trg_entries_total_fee_update
BEFORE UPDATE ON entries
FOR EACH ROW
BEGIN
  SET NEW.total_fee = NEW.individual_fee + NEW.pair_fee + NEW.team_fee + NEW.other_fee;
END$

-- 自动计算成绩总分
CREATE TRIGGER trg_scores_total_score
BEFORE INSERT ON scores
FOR EACH ROW
BEGIN
  SET NEW.total_score = NEW.technique_score + NEW.performance_score - NEW.deduction;
  IF NEW.scored_at IS NULL THEN
    SET NEW.scored_at = CURRENT_TIMESTAMP;
  END IF;
END$

CREATE TRIGGER trg_scores_total_score_update
BEFORE UPDATE ON scores
FOR EACH ROW
BEGIN
  SET NEW.total_score = NEW.technique_score + NEW.performance_score - NEW.deduction;
  
  -- 如果分数被修改，记录修改信息
  IF (OLD.technique_score != NEW.technique_score OR 
      OLD.performance_score != NEW.performance_score OR 
      OLD.deduction != NEW.deduction) THEN
    
    -- 插入修改历史
    INSERT INTO score_modification_logs (
      score_id, event_id, entry_id, judge_id, round_no,
      old_technique_score, new_technique_score,
      old_performance_score, new_performance_score,
      old_deduction, new_deduction,
      old_total_score, new_total_score,
      modification_type, reason, modified_by
    ) VALUES (
      NEW.id, NEW.event_id, NEW.entry_id, NEW.judge_id, NEW.round_no,
      OLD.technique_score, NEW.technique_score,
      OLD.performance_score, NEW.performance_score,
      OLD.deduction, NEW.deduction,
      OLD.total_score, NEW.total_score,
      IFNULL(NEW.modification_reason, 'adjustment'),
      IFNULL(NEW.modification_reason, '成绩调整'),
      NEW.modified_by
    );
    
    SET NEW.modified_at = CURRENT_TIMESTAMP;
    SET NEW.version = OLD.version + 1;
  END IF;
END$

-- 自动更新 updated_at
CREATE TRIGGER trg_entries_updated 
BEFORE UPDATE ON entries
FOR EACH ROW
BEGIN
  SET NEW.updated_at = CURRENT_TIMESTAMP;
END$

CREATE TRIGGER trg_teams_updated 
BEFORE UPDATE ON teams
FOR EACH ROW
BEGIN
  SET NEW.updated_at = CURRENT_TIMESTAMP;
END$

CREATE TRIGGER trg_entry_schedules_updated 
BEFORE UPDATE ON entry_schedules
FOR EACH ROW
BEGIN
  SET NEW.updated_at = CURRENT_TIMESTAMP;
END$

DELIMITER ;
```

---

## 第二部分：SQLAlchemy ORM模型

### 常见查询示例

#### 1. 修改成绩（带历史记录）

```python
from datetime import datetime
from sqlalchemy.orm import Session

def update_score(
    db: Session,
    score_id: int,
    new_technique: float,
    new_performance: float,
    new_deduction: float,
    modified_by_id: int,
    reason: str,
    modification_type: str = 'correction'
):
    """
    修改成绩并自动记录历史
    """
    # 查询原始成绩
    score = db.query(Score).filter(Score.id == score_id).with_for_update().first()
    if not score:
        raise ValueError("成绩记录不存在")
    
    # 记录旧值
    old_values = {
        'technique': score.technique_score,
        'performance': score.performance_score,
        'deduction': score.deduction,
        'total': score.total_score
    }
    
    # 更新成绩（触发器会自动记录到 score_modification_logs）
    score.technique_score = new_technique
    score.performance_score = new_performance
    score.deduction = new_deduction
    score.modified_by = modified_by_id
    score.modification_reason = reason
    score.modified_at = datetime.now()
    
    db.commit()
    db.refresh(score)
    
    return {
        'old': old_values,
        'new': {
            'technique': score.technique_score,
            'performance': score.performance_score,
            'deduction': score.deduction,
            'total': score.total_score
        },
        'version': score.version
    }


def handle_tie_break(
    db: Session,
    entry_ids: list[int],
    event_item_id: int,
    modified_by_id: int
):
    """
    处理同分情况：微调技术分
    """
    scores_list = db.query(Score).filter(
        Score.entry_id.in_(entry_ids),
        Score.event_item_id == event_item_id,
        Score.is_valid == True
    ).all()
    
    # 按当前总分排序
    from collections import defaultdict
    entry_scores = defaultdict(list)
    for score in scores_list:
        entry_scores[score.entry_id].append(score)
    
    # 计算平均分
    avg_scores = {}
    for entry_id, scores in entry_scores.items():
        avg_scores[entry_id] = sum(s.total_score for s in scores) / len(scores)
    
    # 找出同分的条目
    print(f"同分情况: {avg_scores}")
    
    # 这里可以实现自动调整逻辑或返回需要人工处理的列表
    return avg_scores


def invalidate_score(
    db: Session,
    score_id: int,
    modified_by_id: int,
    reason: str
):
    """
    标记某个成绩为无效（如误判）
    """
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        raise ValueError("成绩记录不存在")
    
    score.is_valid = False
    score.modified_by = modified_by_id
    score.modification_reason = reason
    score.modified_at = datetime.now()
    
    db.commit()
    return score
```

#### 2. 查询裁判打分统计

```python
def get_judge_statistics(db: Session, event_id: int = None):
    """
    获取裁判打分统计
    """
    from sqlalchemy import func
    
    query = db.query(
        User.id,
        User.real_name,
        func.count(func.distinct(Score.event_id)).label('events_count'),
        func.count(Score.id).label('scores_count'),
        func.avg(Score.total_score).label('avg_score')
    ).join(
        Score, User.id == Score.judge_id
    ).filter(
        User.role == 'judge',
        Score.is_valid == True
    )
    
    if event_id:
        query = query.filter(Score.event_id == event_id)
    
    query = query.group_by(User.id)
    
    return query.all()
```

#### 3. 查询成绩修改历史

```python
def get_score_modification_history(
    db: Session,
    event_id: int = None,
    entry_id: int = None,
    judge_id: int = None
):
    """
    查询成绩修改历史
    """
    query = db.query(ScoreModificationLog).join(
        Entry, ScoreModificationLog.entry_id == Entry.id
    ).join(
        User, ScoreModificationLog.modified_by == User.id
    )
    
    if event_id:
        query = query.filter(ScoreModificationLog.event_id == event_id)
    if entry_id:
        query = query.filter(ScoreModificationLog.entry_id == entry_id)
    if judge_id:
        query = query.filter(ScoreModificationLog.judge_id == judge_id)
    
    query = query.order_by(ScoreModificationLog.modified_at.desc())
    
    return query.all()
```

---

## 第三部分：核心ORM模型代码

### 1. 基础配置 (database.py)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

# 数据库连接配置
DATABASE_URL = "mysql+pymysql://username:password@localhost:3306/martial_arts?charset=utf8mb4"

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # 生产环境设为 False
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 依赖注入函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### 2. 用户模型 (models/user.py)

```python
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    JUDGE = "judge"
    COACH = "coach"
    ATHLETE = "athlete"
    STAFF = "staff"
    USER = "user"

class UserStatus(str, enum.Enum):
    NORMAL = "normal"
    ABNORMAL = "abnormal"
    FROZEN = "frozen"

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(