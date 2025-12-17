# 武术赛事管理系统数据库结构设计（SQLAlchemy ORM 版）

> 说明：本方案以 SQLAlchemy ORM 为主，仅在必要场景使用原生 SQL（如复杂批量统计、迁移脚本），目标是支撑“网页报名 + 线下比赛成绩评分”的完整流程，并兼顾可读性、扩展性和性能。

---

## 0. 当前项目实现概况（与现有代码对齐）

- 使用 `mysql.connector` + 手写 SQL，通过 `database.py` 中的 `DatabaseManager` 访问 MySQL 数据库（默认库名 `wu_shu`，在 `config.Config.DB_NAME` 中配置）。
- 实际落地的核心表由 `models.DATABASE_SCHEMA` 和若干迁移函数定义，当前版本包含：
  - `users`：账号与基础信息（username / real_name / email / phone / role / status / password / nickname / team_name 等），角色仅有 `super_admin`、`admin`、`judge`、`user` 四类，密码暂为明文存储。
  - `events`：赛事基本信息与报名窗口（name / description / start_date / end_date / location / max_participants / registration_start_time / registration_deadline / status / created_by 及 `contact_phone`、`organizer`、`co_organizer` 等扩展字段）。
  - `participants`：用户在某场赛事中的报名记录（registration_number / event_member_no / category / weight_class / gender / age_group / status / registered_at / checked_in_at 等），同时承担本设计中 `EventParticipant` 与部分 `Entry` 的职责。
  - `scores`：基于参赛者维度的评分记录（participant_id + judge_id + round_number + technique_score + performance_score + deduction + total_score 等），通过 `participants` 关联到赛事。
  - `teams`、`team_applications`、`team_players`、`team_staff`、`team_drafts`：用于当前网页报名与队伍/队员管理，是本方案中 `Team`、`TeamMember`、`Entry` 等实体的历史实现形态。
  - `notifications`、`user_notifications`、`announcements`、`maintenance_logs`：通知公告与系统维护日志等辅助表。
- 本文后续章节描述的是**目标规范模型**（包含 `EventItem` / `Entry` / `EntryMember` / `EventParticipant` 等拆分设计），当前实现仅覆盖其中一部分功能。
- 在实际重构时，应结合上面列出的现有表结构，按“先抽象出统一模型，再通过迁移脚本平滑迁移数据”的思路演进，而不是一次性重建全部表。

## 一、总体设计思路

### 1.1 设计目标

- **统一数据模型**：用一套清晰的表结构覆盖 “用户 / 赛事 / 项目 / 队伍 / 报名 / 成绩” 全流程，避免历史遗留的重复表与含义不清的字段。
- **优先 ORM**：大部分业务逻辑通过 SQLAlchemy ORM 完成，保证代码层结构清晰、可维护；仅在统计聚合等场景使用原生 SQL。
- **结构规范化**：遵循 3NF（第三范式）为主，必要时做有限的反范式（如费用汇总字段）以提升查询性能。
- **性能可控**：关键字段和外键建立合适索引，易于做分页、高并发查询和后续读写分离优化。

### 1.2 业务范围

- **网页报名**：
  - 用户注册登录
  - 赛事发布与设置（报名时间、费用标准、项目列表）
  - 队伍创建与管理
  - 队员/随队人员在项目上的报名（个人、对练、团体）
- **线下比赛结果**：
  - 项目分组、出场顺序
  - 裁判评分（多裁判、多轮、多维度评分）
  - 成绩统计（按项目/轮次/裁判维度聚合）

---

## 二、核心实体与关系概览

### 2.1 核心实体

- `User`：系统用户与个人基础信息
- `Event`：一场完整的赛事（可包含多个项目）
- `EventItem`：赛事中的具体比赛项目/组别（个人/对练/团体）
- `Team`：某赛事下的代表队/俱乐部/学校
- `EventParticipant`：某用户在某场赛事中的参与身份（运动员/教练/裁判等），对应胸牌/证件
- `TeamMember`：队伍成员（在队伍层面的角色）
- `Entry`：对某个 `EventItem` 的一次报名条目（单人/一对/一队）
- `EntryMember`：组成某个 `Entry` 的具体人员（1 人、2 人或 N 人）
- `Score`：针对某个 `Entry` 在某轮次由某裁判打出的成绩记录

### 2.2 关系结构（文字 ER 图）

- `User (1) —— (N) Event`    （创建赛事）
- `User (1) —— (N) EventParticipant`（同一人可参加多场赛事）
- `User (1) —— (N) TeamMember` / `EntryMember` / `Score`（分别对应队内角色、报名项目成员、裁判）
- `Event (1) —— (N) EventItem`（赛事包含多个项目/组别）
- `Event (1) —— (N) Team`（每场赛事下许多队伍）
- `Event (1) —— (N) EventParticipant`（所有参赛/随队/裁判）
- `EventItem (1) —— (N) Entry`（一个项目下的所有报名条目）
- `Team (1) —— (N) TeamMember`（队伍成员结构）
- `Team (1) —— (N) Entry`（该队报名的各项目条目）
- `Entry (1) —— (N) EntryMember`（条目的具体参与人集合）
- `Entry (1) —— (N) Score`（条目在不同轮/不同裁判下的成绩）

---

## 三、表结构设计（按业务维度分组）

### 3.1 用户与账号：`users`

#### 3.1.1 作用

统一管理系统账号及个人基础信息，为报名、队伍、成绩等所有模块提供用户主键。

#### 3.1.2 字段

- `id` INT PK
- `username` VARCHAR(50) UNIQUE NOT NULL
- `password_hash` VARCHAR(255) NOT NULL
- `real_name` VARCHAR(100) NOT NULL
- `nickname` VARCHAR(100)
- `email` VARCHAR(100) UNIQUE
- `phone` VARCHAR(20)
- `id_card` VARCHAR(30)   —— 身份证/证件号，用于年龄、性别推导
- `gender` ENUM('male','female','other')
- `birthdate` DATE
- `role` ENUM('super_admin','admin','judge','coach','athlete','staff','user') DEFAULT 'user'
- `status` ENUM('normal','abnormal','frozen') DEFAULT 'normal'
- `is_active` BOOLEAN DEFAULT TRUE
- `created_at` DATETIME
- `updated_at` DATETIME

#### 3.1.3 索引与关系

- 索引：`idx_role(role)`, `idx_phone(phone)`, `idx_id_card(id_card)`
- 关系：
  - 1–N `events.created_by`
  - 1–N `event_participants.user_id`
  - 1–N `teams.leader_id` / `teams.created_by`
  - 1–N `team_members.user_id`
  - 1–N `entry_members.user_id`
  - 1–N `scores.judge_id`

---

### 3.2 赛事管理：`events`、`event_items`

#### 3.2.1 `events` 赛事表

**作用**：描述一场完整赛事的基本信息与报名/比赛时间窗口，以及赛事级别的费用标准。

**字段**：

- `id` INT PK
- `code` VARCHAR(50) UNIQUE       —— 内部赛事编号，可用于短链接、导出文件名
- `name` VARCHAR(200) NOT NULL
- `description` TEXT
- `location` VARCHAR(200)
- `start_time` DATETIME NOT NULL
- `end_time` DATETIME NOT NULL
- `registration_start` DATETIME
- `registration_end` DATETIME
- `status` ENUM('draft','published','ongoing','completed','cancelled') DEFAULT 'draft'
- 费用标准：
  - `individual_fee` DECIMAL(10,2) DEFAULT 0
  - `pair_fee` DECIMAL(10,2) DEFAULT 0
  - `team_fee` DECIMAL(10,2) DEFAULT 0
- `created_by` INT FK → `users.id`
- `created_at` DATETIME
- `updated_at` DATETIME

**索引**：`idx_status(status)`, `idx_start(start_time)`, `idx_registration(registration_start)`

**关系**：

- 1–N `event_items`
- 1–N `teams`
- 1–N `event_participants`
- 1–N `entries`

#### 3.2.2 `event_items` 赛事项目/组别表

**作用**：将赛事拆成若干参赛项目（例如：男子套路 A 组、女子对练 B 组 团体赛）。

**字段**：

- `id` INT PK
- `event_id` INT FK → `events.id`
- `name` VARCHAR(200) NOT NULL        —— 展示给前端的项目名
- `code` VARCHAR(50)                   —— 内部项目编码
- `type` ENUM('individual','pair','team') NOT NULL
- `gender_limit` ENUM('male','female','mixed') NULL
- `min_age` INT NULL
- `max_age` INT NULL
- `weight_class` VARCHAR(50) NULL
- `max_entries` INT NULL               —— 该项目允许的最大报名条目数
- `rounds` INT DEFAULT 1               —— 比赛轮次数
- `scoring_mode` ENUM('sum','avg','drop_high_low') DEFAULT 'sum'
- `sort_order` INT DEFAULT 0
- `is_active` BOOLEAN DEFAULT TRUE

**索引**：`idx_event(event_id)`, `idx_event_type(event_id, type)`

**关系**：

- 1–N `entries`（一个项目下多个报名条目）

---

### 3.3 队伍与队内结构：`teams`、`team_members`

#### 3.3.1 `teams` 队伍表

**作用**：表示在某场赛事中的一个代表队/俱乐部/学校等组织实体。

**字段**：

- `id` INT PK
- `event_id` INT FK → `events.id`
- `name` VARCHAR(200) NOT NULL
- `short_name` VARCHAR(50)
- `team_type` VARCHAR(100)            —— 例如“学校”、“俱乐部”
- `address` VARCHAR(255)
- 领队：
  - `leader_id` INT FK → `users.id`
  - `leader_name` VARCHAR(100)
  - `leader_phone` VARCHAR(20)
- `status` ENUM('draft','active','withdrawn','deleted') DEFAULT 'active'
- `client_team_key` VARCHAR(100) UNIQUE   —— 前端生成的唯一 key，用于本地缓存和对接
- `created_by` INT FK → `users.id`
- `created_at` DATETIME
- `updated_at` DATETIME

**索引**：`idx_event(event_id)`, `idx_event_status(event_id,status)`

**关系**：

- 1–N `team_members`
- 1–N `entries`（该队在各项目中的报名条目）
- 可与 `event_participants` 关联（队员对应的赛事参与记录挂队伍）

#### 3.3.2 `team_members` 队伍成员表

**作用**：统一管理队内所有角色（运动员、教练、工作人员、领队），代替旧项目中的 `team_players` / `team_staff` 分裂设计。

**字段**：

- `id` INT PK
- `event_id` INT FK → `events.id`
- `team_id` INT FK → `teams.id`
- `user_id` INT FK → `users.id`
- `member_role` ENUM('athlete','coach','staff','leader') NOT NULL
- `position` VARCHAR(100) NULL        —— 职务，例如“主教练”、“队医”
- `jersey_no` VARCHAR(20) NULL        —— 若需要球衣号/场次号
- `status` ENUM('active','inactive') DEFAULT 'active'
- `source` ENUM('direct','application') DEFAULT 'direct'
- `created_at` DATETIME
- `updated_at` DATETIME

**约束与索引**：

- `UNIQUE(event_id, team_id, user_id, member_role)` —— 避免重复身份
- 索引：`idx_event_team(event_id, team_id)`

**关系**：

- 方便根据 `team_id` 快速拿到所有队内成员及其角色

---

### 3.4 赛事参与者：`event_participants`

**作用**：每条记录代表“某个用户以某种身份参与了某场赛事”，是胸牌/签到层数据，独立于具体报了哪些项目。

**字段**：

- `id` INT PK
- `event_id` INT FK → `events.id`
- `user_id` INT FK → `users.id`
- `team_id` INT FK → `teams.id` NULL
- `role` ENUM('athlete','coach','staff','judge','official') DEFAULT 'athlete'
- `event_member_no` INT NULL     —— 赛事内部编号/证件号
- `status` ENUM('registered','checked_in','withdrawn','disqualified') DEFAULT 'registered'
- `notes` TEXT
- `registered_at` DATETIME
- `checked_in_at` DATETIME NULL

**约束与索引**：

- `UNIQUE(event_id, user_id, role)` —— 控制同一人同一赛事同一角色唯一
- `UNIQUE(event_id, event_member_no)`
- 索引：`idx_event_role(event_id, role)`, `idx_event_status(event_id, status)`

**关系与作用**：

- 为成绩表、报名表提供统一的人–赛事映射
- 方便按赛事导出所有胸牌名单、签到状态

---

### 3.5 报名系统：`entries`、`entry_members`

#### 3.5.1 `entries` 报名条目表

**作用**：一行 = 某赛事中某项目下的一个“参赛单位”（可以是单人、对练组合或一支队伍），是成绩统计的主键。

**字段**：

- `id` BIGINT PK
- `event_id` INT FK → `events.id`
- `event_item_id` INT FK → `event_items.id`
- `team_id` INT FK → `teams.id` NULL
- `entry_type` ENUM('individual','pair','team') NOT NULL
- `registration_number` VARCHAR(50) UNIQUE NOT NULL
- `status` ENUM('registered','checked_in','competing','completed','withdrawn','disqualified') DEFAULT 'registered'
- 编排信息：
  - `group_no` INT NULL
  - `order_in_group` INT NULL
- 费用摘要：
  - `individual_fee` DECIMAL(10,2) DEFAULT 0
  - `pair_fee` DECIMAL(10,2) DEFAULT 0
  - `team_fee` DECIMAL(10,2) DEFAULT 0
  - `other_fee` DECIMAL(10,2) DEFAULT 0
  - `total_fee` DECIMAL(10,2) 默认可由业务层维护
- `created_by` INT FK → `users.id`
- `created_at` DATETIME
- `updated_at` DATETIME

**索引**：

- `idx_event_item(event_id, event_item_id)`
- `idx_team(event_id, team_id)`
- `idx_status(event_id, status)`

**关系与用途**：

- 统计 “某项目的参赛单位数/名单” 时直接查 `entries`
- 费用统计可以按 `team_id` 聚合 entries 的费用字段，配合 `events` 中的费率做检查

#### 3.5.2 `entry_members` 报名条目成员表

**作用**：描述构成某个 `Entry` 的具体参赛人员集合，支持：

- 个人赛：1 条成员记录
- 对练：2 条记录
- 团体赛：N 条记录

**字段**：

- `id` BIGINT PK
- `entry_id` BIGINT FK → `entries.id`
- `user_id` INT FK → `users.id`
- `role` ENUM('main','substitute') DEFAULT 'main'
- `order_in_entry` INT NULL

**约束与索引**：

- `UNIQUE(entry_id, user_id)`
- 索引：`idx_entry(entry_id)`, `idx_user(user_id)`

**关系与用途**：

- 从 `entries` 反查其所有 `entry_members` 可以构建对练组合、团体名单
- 成绩导出时可以带出所有成员信息

---

### 3.6 成绩系统：`scores`

**作用**：每条记录代表“某裁判在某轮对某报名条目打出的成绩”。

**字段**：

- `id` BIGINT PK
- `event_id` INT FK → `events.id`
- `event_item_id` INT FK → `event_items.id`
- `entry_id` BIGINT FK → `entries.id`
- `judge_id` INT FK → `users.id`（role=judge）
- `round_no` INT DEFAULT 1
- 评分字段（可扩展）：
  - `technique_score` DECIMAL(5,2) DEFAULT 0
  - `performance_score` DECIMAL(5,2) DEFAULT 0
  - `deduction` DECIMAL(5,2) DEFAULT 0
  - `total_score` DECIMAL(5,2)
  - `rank_in_round` INT NULL
- `notes` TEXT
- `scored_at` DATETIME
- `updated_at` DATETIME

**约束与索引**：

- `UNIQUE(entry_id, judge_id, round_no)` —— 避免同轮重复打分
- 索引：
  - `idx_event_item_round(event_id, event_item_id, round_no)`
  - `idx_judge(judge_id)`

**用途**：

- 按 `entry_id` 汇总得到该单位的总成绩/名次
- 支持多裁判打分、多轮比拼的完整记录

---

## 四、SQLAlchemy ORM 使用策略

### 4.1 ORM 为主，原生 SQL 为辅

- **业务查询与写入**（报名、队伍管理、成绩录入）全部使用 ORM：
  - 保持模型层（models.py）与业务服务层（services/*）隔离；
  - 使用 relationship 管理外键关系，减少手写 JOIN。
- **统计报表 & 复杂聚合**：
  - 优先使用 SQLAlchemy 的 query + func/窗口函数；
  - 遇到 ORM 表达力有限的聚合（如复杂排名、跨多表的窗口函数）时，在“报表层”封装 原生 SQL，但返回结果尽量映射为 Pydantic/DTO，而不是在业务核心层大量散落原生 SQL。

### 4.2 性能与索引

- 所有外键字段均建立索引：`event_id`, `team_id`, `user_id`, `event_item_id`, `entry_id`。
- 频繁筛选字段（如 `status`, `round_no`, `role`）建立组合索引，支持分页与条件查询：
  - 示例：
    - 参赛者列表：`event_id + status + gender/age_group` 可以通过 `event_participants` 或 `entries + entry_members` 配合 `users` 获取；
    - 成绩表：`event_id + event_item_id + round_no` 索引帮助裁判/记录员快速查看同组成绩。

### 4.3 架构与监控建议

- **分层架构**：
  - `models/` 只放 ORM 模型；
  - `repositories/` 负责具体查询、写入（可返回 ORM 对象或 DTO）；
  - `services/` 做业务组合逻辑（报名流程、队伍审核、成绩汇总等）。
- **性能监控**：
  - 开启 SQLAlchemy 的 `echo` 或使用 logging handler，在开发环境输出慢查询日志；
  - 对关键接口（参赛列表、成绩查询、费用汇总）加上耗时统计与 explain 分析（必要时用原生 SQL + EXPLAIN）。

---

## 五、总结

这版数据库结构的特点：

- **实体职责清晰**：
  - `EventParticipant` 管“人参加赛事”；
  - `Entry/EntryMember` 管“人（或队）报了哪个项目”；
  - `Score` 管“在这个项目上某轮由某裁判打了多少分”。
- **适配现有业务**：
  - 与你目前的 `users / events / teams / team_players / participants / scores` 等表一一对应，并加以规范化和统一；
  - 队伍费用统计可直接基于 `entries` 与 `events` 中的费率做聚合；
  - 报名导出和成绩导出都有清晰主表（`Entry`）。
- **演进友好**：
  - 后续若要支持更多项目类型、评分维度、视频回放等，可通过扩展 `EventItem` 配置和 `Score` 字段而无需大改核心模型。

这份 `.md` 文档可以直接给项目经理和小组成员作为数据库重构的设计说明，如果你需要，我可以在此基础上继续：

- 给出完整的 SQLAlchemy 模型代码骨架（分文件）、
- 或设计从旧表结构迁移到新表结构的逐步迁移脚本和数据迁移策略。
