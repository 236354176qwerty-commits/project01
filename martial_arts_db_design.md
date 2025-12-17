# 武术赛事管理系统数据库结构设计（改进版）

> **版本**: v2.0  
> **数据库**: MySQL 8.0+  
> **ORM框架**: SQLAlchemy 2.0+  
> **更新日期**: 2024-11-27

---

## 0. 与现有项目实现的对应关系

- 当前运行代码使用数据库名 `wu_shu`，由 `config.Config.DB_NAME` 配置，并通过 `database.DatabaseManager` + `mysql.connector` 直接访问 MySQL，而非 SQLAlchemy。表结构主要来自 `models.DATABASE_SCHEMA` 中的 DDL 加上 `_migrate_database`、`_ensure_event_columns` 等迁移逻辑。
- 已落地的核心表包括：`users`、`events`、`participants`、`scores`、`teams`、`team_applications`、`team_players`、`team_staff`、`team_drafts` 以及通知公告、维护日志等辅助表。本设计文档中的实体可以视为对这些表的规范化重构目标，而不是一一对应的现状描述：
  - 现有 `users` 与本文的 `users` 实体基本对应，但缺少 `password_hash`、`id_card`、`gender`、`birthdate` 等字段，且当前实际使用的是明文 `password` 字段；重构时需要新增哈希字段并设计逐步迁移方案。
  - 现有 `events` 仅包含 `name` / `description` / `start_date` / `end_date` / `location` / `max_participants` / `registration_start_time` / `registration_deadline` / 状态 / 创建信息及费用字段（`individual_fee`、`pair_practice_fee`、`team_competition_fee`）和扩展列 `contact_phone`、`organizer`、`co_organizer` 等，与本文 `events` 设计中的 `code`、`logo_url`、`pair_fee`、`team_fee`、`start_time` / `end_time` 等字段存在命名和粒度差异，需要通过 `ALTER TABLE` / `RENAME COLUMN` 渐进统一。
  - 现有 `participants` 同时承担“某个用户参加某场赛事”的身份信息和粗粒度的报名信息（`category` / `weight_class` 等），而本文将这部分职责拆分为 `EventParticipant`（胸牌/签到层）+ `Entry`（项目报名条目）+ `EntryMember`（条目内的人员列表）；重构时可以先在服务层抽象出这三个概念，再逐步把数据从 `participants` / `team_players` 迁移到新表。
  - 现有 `scores` 只依赖 `participant_id` + `judge_id` + `round_number`，通过 `participants` 关联到赛事，没有显式的 `event_id` / `event_item_id` / `entry_id` 外键；本文的 `scores` 与 `score_modification_logs` 在结构上更完整，支持修改历史和按项目统计，需要通过加列或新表的方式演进。
  - 现有 `teams`、`team_players`、`team_staff`、`team_applications`、`team_drafts` 是早期为报名表单定制的一组合表，本文中则推荐统一为 `teams` + `team_members` + `entries` + `entry_members` + `payment_records` 等通用结构。
- 推荐的分阶段迁移策略：
  - 第一阶段：在现有 `wu_shu` 库上引入 `event_items` / `entries` / `entry_members` / `event_participants` 等新表，并在服务层为旧表 (`participants`、`team_players` 等) 提供兼容读取，保持接口不变。
  - 第二阶段：将报名、编排、成绩相关接口逐步切换到新模型，`participants` 逐渐退化为只读视图或过渡表，新的费用与支付逻辑落在 `entries` + `payment_records` 上。
  - 第三阶段：清理 `team_players` / `team_staff` / `team_applications` 等冗余结构，仅保留新表及必要的兼容视图，并在数据库层统一命名（如费用字段和时间字段）。

下文从“一、总体设计思路”起仍然以重构后的**目标结构**为主描述，理解和落地时需要结合本节给出的表映射关系以及迁移阶段。

## 一、总体设计思路

### 1.1 设计目标

- **统一数据模型**：用一套清晰的表结构覆盖 "用户 / 赛事 / 项目 / 队伍 / 报名 / 成绩" 全流程
- **优先 ORM**：大部分业务逻辑通过 SQLAlchemy ORM 完成，仅在统计聚合等场景使用原生 SQL
- **结构规范化**：遵循 3NF（第三范式）为主，必要时做有限的反范式以提升查询性能
- **性能可控**：关键字段和外键建立合适索引，支持分页、高并发查询
- **业务完整**：支持补签、手动编排、费用管理等实际业务需求

### 1.2 业务范围

- **网页报名**：
  - 用户注册登录
  - 赛事发布与设置（报名时间、费用标准、项目列表）
  - 队伍创建与管理
  - 队员/随队人员在项目上的报名（个人、对练、团体）
  - 报名费用管理和支付记录
  
- **线下比赛管理**：
  - 报到签到与补签
  - 项目分组、手动编排出场顺序
  - 裁判分配与评分
  - 成绩统计与排名

---

## 二、核心实体与关系概览

### 2.1 核心实体

| 实体 | 说明 |
|------|------|
| `User` | 系统用户与个人基础信息 |
| `Event` | 一场完整的赛事（可包含多个项目） |
| `EventItem` | 赛事中的具体比赛项目/组别 |
| `Team` | 某赛事下的代表队/俱乐部/学校 |
| `EventParticipant` | 某用户在某场赛事中的参与身份 |
| `TeamMember` | 队伍成员（在队伍层面的角色） |
| `Entry` | 对某个项目的一次报名条目 |
| `EntryMember` | 组成某个报名条目的具体人员 |
| `EntrySchedule` | 比赛编排信息（分组、出场顺序） |
| `JudgeAssignment` | 裁判分配表 |
| `Score` | 裁判评分记录 |
| `PaymentRecord` | 费用支付记录 |

### 2.2 关系结构（ER图文字版）

```
User (1) ─── (N) Event [创建赛事]
User (1) ─── (N) EventParticipant [参与赛事]
User (1) ─── (N) TeamMember [队伍成员]
User (1) ─── (N) EntryMember [报名成员]
User (1) ─── (N) Score [裁判打分]

Event (1) ─── (N) EventItem [包含项目]
Event (1) ─── (N) Team [参赛队伍]
Event (1) ─── (N) EventParticipant [所有参与者]

EventItem (1) ─── (N) Entry [项目报名]
EventItem (1) ─── (N) JudgeAssignment [裁判分配]
EventItem (1) ─── (N) EntrySchedule [比赛编排]

Team (1) ─── (N) TeamMember [队伍结构]
Team (1) ─── (N) Entry [队伍报名]
Team (1) ─── (N) PaymentRecord [支付记录]

Entry (1) ─── (N) EntryMember [参赛人员]
Entry (1) ─── (N) Score [成绩记录]
Entry (1) ─── (1) EntrySchedule [编排信息]
```

---

## 三、表结构设计

### 3.1 用户管理：`users`

#### 作用
统一管理系统账号及个人基础信息，为报名、队伍、成绩等所有模块提供用户主键。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 用户ID |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希 |
| real_name | VARCHAR(100) | NOT NULL | 真实姓名 |
| nickname | VARCHAR(100) | | 昵称 |
| email | VARCHAR(100) | UNIQUE | 邮箱 |
| phone | VARCHAR(20) | | 手机号 |
| id_card | VARCHAR(30) | | 身份证号 |
| gender | ENUM | 'male','female','other' | 性别 |
| birthdate | DATE | | 出生日期 |
| role | ENUM | DEFAULT 'user' | 角色 |
| status | ENUM | DEFAULT 'normal' | 状态 |
| is_active | BOOLEAN | DEFAULT TRUE | 是否激活 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| deleted_at | DATETIME | NULL | 软删除时间 |

#### 索引
- `idx_role(role)`
- `idx_phone(phone)`
- `idx_id_card(id_card)`
- `idx_real_name(real_name)`
- `idx_created_at(created_at)`

---

### 3.2 赛事管理：`events`

#### 作用
描述一场完整赛事的基本信息与报名/比赛时间窗口，以及赛事级别的费用标准。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 赛事ID |
| code | VARCHAR(50) | UNIQUE, NOT NULL | 赛事编号 |
| name | VARCHAR(200) | NOT NULL | 赛事名称 |
| description | TEXT | | 赛事描述 |
| organizer | VARCHAR(200) | | 主办方 |
| location | VARCHAR(200) | | 比赛地点 |
| logo_url | VARCHAR(500) | | Logo地址 |
| start_time | DATETIME | NOT NULL | 开始时间 |
| end_time | DATETIME | NOT NULL | 结束时间 |
| registration_start | DATETIME | | 报名开始 |
| registration_end | DATETIME | | 报名截止 |
| status | ENUM | DEFAULT 'draft' | 状态 |
| is_public | BOOLEAN | DEFAULT TRUE | 是否公开 |
| max_teams | INT | | 最大队伍数 |
| individual_fee | DECIMAL(10,2) | DEFAULT 0 | 个人项目费用 |
| pair_fee | DECIMAL(10,2) | DEFAULT 0 | 对练项目费用 |
| team_fee | DECIMAL(10,2) | DEFAULT 0 | 团体项目费用 |
| created_by | INT | FK → users.id | 创建人 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| deleted_at | DATETIME | NULL | 软删除时间 |

#### 索引
- `idx_status(status)`
- `idx_start_time(start_time)`
- `idx_registration(registration_start, registration_end)`
- `idx_created_at(created_at)`

---

### 3.3 赛事项目：`event_items`

#### 作用
将赛事拆成若干参赛项目（例如：男子套路A组、女子对练B组、团体赛）。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 项目ID |
| event_id | INT | FK → events.id | 所属赛事 |
| name | VARCHAR(200) | NOT NULL | 项目名称 |
| code | VARCHAR(50) | | 项目编码 |
| description | TEXT | | 项目说明 |
| type | ENUM | NOT NULL | 'individual','pair','team' |
| gender_limit | ENUM | | 'male','female','mixed' |
| min_age | INT | | 最小年龄 |
| max_age | INT | | 最大年龄 |
| weight_class | VARCHAR(50) | | 体重级别 |
| min_members | INT | | 最少人数（团体） |
| max_members | INT | | 最多人数（团体） |
| max_entries | INT | | 最大报名数 |
| equipment_required | VARCHAR(200) | | 器械要求 |
| rounds | INT | DEFAULT 1 | 比赛轮次 |
| scoring_mode | ENUM | DEFAULT 'sum' | 计分模式 |
| sort_order | INT | DEFAULT 0 | 排序权重 |
| is_active | BOOLEAN | DEFAULT TRUE | 是否启用 |

#### 索引
- `idx_event(event_id)`
- `idx_event_type(event_id, type)`

#### 约束
```sql
CHECK (min_age IS NULL OR max_age IS NULL OR min_age <= max_age)
```

---

### 3.4 队伍管理：`teams`

#### 作用
表示在某场赛事中的一个代表队/俱乐部/学校等组织实体。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 队伍ID |
| event_id | INT | FK → events.id | 所属赛事 |
| name | VARCHAR(200) | NOT NULL | 队伍名称 |
| short_name | VARCHAR(50) | | 简称 |
| team_type | VARCHAR(100) | | 类型（学校/俱乐部） |
| address | VARCHAR(255) | | 地址 |
| leader_id | INT | FK → users.id | 领队用户ID |
| leader_name | VARCHAR(100) | | 领队姓名 |
| leader_phone | VARCHAR(20) | | 领队电话 |
| status | ENUM | DEFAULT 'active' | 状态 |
| client_team_key | VARCHAR(100) | UNIQUE | 前端缓存key |
| created_by | INT | FK → users.id | 创建人 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| deleted_at | DATETIME | NULL | 软删除时间 |

#### 索引
- `idx_event(event_id)`
- `idx_event_status(event_id, status)`

---

### 3.5 队伍成员：`team_members`

#### 作用
统一管理队内所有角色（运动员、教练、工作人员、领队）。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 成员ID |
| event_id | INT | FK → events.id | 赛事ID |
| team_id | INT | FK → teams.id | 队伍ID |
| user_id | INT | FK → users.id | 用户ID |
| member_role | ENUM | NOT NULL | 'athlete','coach','staff','leader' |
| position | VARCHAR(100) | | 职务 |
| jersey_no | VARCHAR(20) | | 号码 |
| status | ENUM | DEFAULT 'active' | 状态 |
| source | ENUM | DEFAULT 'direct' | 来源 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

#### 索引
- `idx_event_team(event_id, team_id)`
- `idx_user_role(user_id, member_role)`

#### 约束
```sql
UNIQUE(event_id, team_id, user_id, member_role)
```

---

### 3.6 赛事参与者：`event_participants`

#### 作用
每条记录代表"某个用户以某种身份参与了某场赛事"，是胸牌/签到层数据。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 参与者ID |
| event_id | INT | FK → events.id | 赛事ID |
| user_id | INT | FK → users.id | 用户ID |
| team_id | INT | FK → teams.id | 队伍ID |
| role | ENUM | DEFAULT 'athlete' | 角色 |
| event_member_no | INT | | 赛事编号 |
| status | ENUM | DEFAULT 'registered' | 状态 |
| notes | TEXT | | 备注 |
| registered_at | DATETIME | | 注册时间 |
| checked_in_at | DATETIME | | 签到时间 |

#### 索引
- `idx_event_role(event_id, role)`
- `idx_event_status(event_id, status)`

#### 约束
```sql
UNIQUE(event_id, user_id, role)
UNIQUE(event_id, event_member_no)
```

---

### 3.7 报名条目：`entries`

#### 作用
一行 = 某赛事中某项目下的一个"参赛单位"（可以是单人、对练组合或一支队伍）。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 报名ID |
| event_id | INT | FK → events.id | 赛事ID |
| event_item_id | INT | FK → event_items.id | 项目ID |
| team_id | INT | FK → teams.id | 队伍ID |
| entry_type | ENUM | NOT NULL | 'individual','pair','team' |
| registration_number | VARCHAR(50) | UNIQUE, NOT NULL | 报名编号 |
| status | ENUM | DEFAULT 'registered' | 状态 |
| checked_in_at | DATETIME | | 报到时间 |
| late_checkin_at | DATETIME | | 补签时间 |
| late_checkin_by | INT | FK → users.id | 补签操作人 |
| late_checkin_reason | TEXT | | 补签原因 |
| late_checkin_penalty | DECIMAL(10,2) | DEFAULT 0 | 补签罚款 |
| individual_fee | DECIMAL(10,2) | DEFAULT 0 | 个人项目费 |
| pair_fee | DECIMAL(10,2) | DEFAULT 0 | 对练项目费 |
| team_fee | DECIMAL(10,2) | DEFAULT 0 | 团体项目费 |
| other_fee | DECIMAL(10,2) | DEFAULT 0 | 其他费用 |
| total_fee | DECIMAL(10,2) | DEFAULT 0 | 总费用 |
| payment_status | ENUM | DEFAULT 'unpaid' | 支付状态 |
| paid_amount | DECIMAL(10,2) | DEFAULT 0 | 已付金额 |
| payment_time | DATETIME | | 支付时间 |
| withdrawn_reason | TEXT | | 退赛原因 |
| created_by | INT | FK → users.id | 创建人 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

#### 索引
- `idx_event_item(event_id, event_item_id)`
- `idx_team(event_id, team_id)`
- `idx_status(event_id, status)`
- `idx_event_item_status(event_id, event_item_id, status)`
- `idx_team_status(team_id, status)`
- `idx_registration_number(registration_number)`
- `idx_checkin_status(event_id, status, checked_in_at)`
- `idx_late_checkin(event_id, late_checkin_at)`

#### 约束
```sql
CHECK (
  (entry_type = 'individual' AND pair_fee = 0 AND team_fee = 0) OR
  (entry_type = 'pair' AND individual_fee = 0 AND team_fee = 0) OR
  (entry_type = 'team' AND individual_fee = 0 AND pair_fee = 0)
)
```

---

### 3.8 报名成员：`entry_members`

#### 作用
描述构成某个报名条目的具体参赛人员集合。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 成员ID |
| entry_id | BIGINT | FK → entries.id | 报名条目ID |
| user_id | INT | FK → users.id | 用户ID |
| role | ENUM | DEFAULT 'main' | 'main','substitute' |
| order_in_entry | INT | | 顺序 |

#### 索引
- `idx_entry(entry_id)`
- `idx_user(user_id)`

#### 约束
```sql
UNIQUE(entry_id, user_id)
```

---

### 3.9 比赛编排：`entry_schedules`

#### 作用
管理比赛的分组和出场顺序，支持手动调整。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 编排ID |
| event_id | INT | FK → events.id | 赛事ID |
| event_item_id | INT | FK → event_items.id | 项目ID |
| entry_id | BIGINT | FK → entries.id | 报名条目ID |
| group_label | VARCHAR(50) | | 组别标识 |
| group_no | INT | NOT NULL | 组号 |
| sequence_no | INT | NOT NULL | 出场序号 |
| global_sequence_no | INT | | 全局序号 |
| venue | VARCHAR(100) | | 场地 |
| scheduled_time | DATETIME | | 预计时间 |
| actual_start_time | DATETIME | | 实际开始 |
| actual_end_time | DATETIME | | 实际结束 |
| status | ENUM | DEFAULT 'pending' | 编排状态 |
| is_manually_adjusted | BOOLEAN | DEFAULT FALSE | 是否手动调整 |
| adjusted_by | INT | FK → users.id | 调整人 |
| adjusted_at | DATETIME | | 调整时间 |
| adjustment_reason | TEXT | | 调整原因 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

#### 索引
- `idx_item_group_seq(event_item_id, group_no, sequence_no)`
- `idx_item_global_seq(event_item_id, global_sequence_no)`
- `idx_scheduled_time(scheduled_time)`
- `idx_status(event_item_id, status)`

#### 约束
```sql
UNIQUE(event_item_id, entry_id)
```

---

### 3.10 编排调整历史：`schedule_adjustment_logs`

#### 作用
记录所有编排调整的历史，用于审计和回溯。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 日志ID |
| event_item_id | INT | FK → event_items.id | 项目ID |
| entry_id | BIGINT | FK → entries.id | 报名条目ID |
| old_group_no | INT | | 原组号 |
| new_group_no | INT | | 新组号 |
| old_sequence_no | INT | | 原序号 |
| new_sequence_no | INT | | 新序号 |
| old_global_sequence_no | INT | | 原全局序号 |
| new_global_sequence_no | INT | | 新全局序号 |
| adjustment_type | ENUM | | 'manual','auto','swap' |
| reason | TEXT | | 调整原因 |
| adjusted_by | INT | FK → users.id | 操作人 |
| adjusted_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 调整时间 |

#### 索引
- `idx_item_time(event_item_id, adjusted_at)`
- `idx_entry(entry_id)`

---

### 3.11 裁判分配：`judge_assignments` (已废弃)

> **说明**: 由于实际业务中裁判人数固定（不到10人），所有项目都由这些裁判评分，不需要单独的裁判分配表。所有裁判信息通过 `users` 表的 `role='judge'` 即可管理。

**建议**: 如果后续需要记录裁判参与赛事的情况，可以使用 `event_participants` 表，设置 `role='judge'` 即可。

---

### 3.12 成绩记录：`scores`

#### 作用
每条记录代表"某裁判在某轮对某报名条目打出的成绩"。支持成绩修改和修改历史追踪。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 成绩ID |
| event_id | INT | FK → events.id | 赛事ID |
| event_item_id | INT | FK → event_items.id | 项目ID |
| entry_id | BIGINT | FK → entries.id | 报名条目ID |
| judge_id | INT | FK → users.id | 裁判ID |
| round_no | INT | DEFAULT 1 | 轮次 |
| technique_score | DECIMAL(5,2) | DEFAULT 0 | 技术分 |
| performance_score | DECIMAL(5,2) | DEFAULT 0 | 表现分 |
| deduction | DECIMAL(5,2) | DEFAULT 0 | 扣分 |
| total_score | DECIMAL(5,2) | | 总分 |
| rank_in_round | INT | | 该轮排名 |
| is_valid | BOOLEAN | DEFAULT TRUE | 是否有效 |
| judge_signature | VARCHAR(100) | | 裁判签名 |
| notes | TEXT | | 备注 |
| scored_at | DATETIME | | 初次打分时间 |
| modified_at | DATETIME | | 最后修改时间 |
| modified_by | INT | FK → users.id | 修改操作人 |
| modification_reason | TEXT | | 修改原因 |
| version | INT | DEFAULT 1 | 版本号(用于乐观锁) |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

#### 索引
- `idx_event_item_round(event_id, event_item_id, round_no)`
- `idx_judge(judge_id)`
- `idx_entry_round(entry_id, round_no)`
- `idx_scored_at(scored_at)`
- `idx_modified(modified_at)`

#### 约束
```sql
UNIQUE(entry_id, judge_id, round_no)
CHECK (technique_score >= 0 AND performance_score >= 0 AND deduction >= 0)
```

---

### 3.13 成绩修改历史：`score_modification_logs`

#### 作用
记录所有成绩修改的历史，用于审计和追溯，解决同分调整需求。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 日志ID |
| score_id | BIGINT | FK → scores.id | 成绩ID |
| event_id | INT | FK → events.id | 赛事ID |
| entry_id | BIGINT | FK → entries.id | 报名条目ID |
| judge_id | INT | FK → users.id | 裁判ID |
| round_no | INT | | 轮次 |
| old_technique_score | DECIMAL(5,2) | | 原技术分 |
| new_technique_score | DECIMAL(5,2) | | 新技术分 |
| old_performance_score | DECIMAL(5,2) | | 原表现分 |
| new_performance_score | DECIMAL(5,2) | | 新表现分 |
| old_deduction | DECIMAL(5,2) | | 原扣分 |
| new_deduction | DECIMAL(5,2) | | 新扣分 |
| old_total_score | DECIMAL(5,2) | | 原总分 |
| new_total_score | DECIMAL(5,2) | | 新总分 |
| modification_type | ENUM | NOT NULL | 'correction','tie_break','adjustment' |
| reason | TEXT | NOT NULL | 修改原因 |
| modified_by | INT | FK → users.id | 修改人 |
| modified_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 修改时间 |

#### 索引
- `idx_score(score_id)`
- `idx_entry_time(entry_id, modified_at)`
- `idx_event(event_id)`
- `idx_judge(judge_id)`

#### 用途
- 追踪所有成绩变更记录
- 处理同分情况的调整历史
- 审计和合规性检查

---

### 3.14 支付记录：`payment_records`

#### 作用
记录所有费用支付流水，支持分次缴费和退费。

#### 字段列表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 记录ID |
| event_id | INT | FK → events.id | 赛事ID |
| team_id | INT | FK → teams.id | 队伍ID |
| entry_id | BIGINT | FK → entries.id | 报名条目ID |
| amount | DECIMAL(10,2) | NOT NULL | 金额 |
| payment_type | ENUM | DEFAULT 'registration' | 支付类型 |
| payment_method | ENUM | | 支付方式 |
| transaction_no | VARCHAR(100) | | 交易流水号 |
| paid_at | DATETIME | | 支付时间 |
| created_by | INT | FK → users.id | 创建人 |
| notes | TEXT | | 备注 |

#### 索引
- `idx_team_payment(team_id, paid_at)`
- `idx_event(event_id)`

---

## 四、视图设计

### 4.1 报名统计视图

```sql
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
```

### 4.2 成绩排名视图

```sql
CREATE VIEW v_scores_ranking AS
SELECT 
  s.event_item_id,
  s.entry_id,
  e.registration_number,
  AVG(s.total_score) AS avg_score,
  RANK() OVER (PARTITION BY s.event_item_id ORDER BY AVG(s.total_score) DESC) AS ranking
FROM scores s
JOIN entries e ON s.entry_id = e.id
WHERE s.is_valid = TRUE
GROUP BY s.event_item_id, s.entry_id;
```

### 4.3 补签记录查询视图

```sql
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
```

### 4.4 编排详情视图

```sql
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

## 五、触发器设计

### 5.1 自动计算总费用

```sql
DELIMITER $
CREATE TRIGGER trg_entries_total_fee 
BEFORE INSERT ON entries
FOR EACH ROW
BEGIN
  SET NEW.total_fee = NEW.individual_fee + NEW.pair_fee + NEW.team_fee + NEW.other_fee;
END$

CREATE TRIGGER trg_entries_total_fee_update
BEFORE UPDATE ON entries
FOR EACH ROW
BEGIN
  SET NEW.total_fee = NEW.individual_fee + NEW.pair_fee + NEW.team_fee + NEW.other_fee;
END$
DELIMITER ;
```

### 5.2 自动更新 updated_at

```sql
DELIMITER $
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

## 六、索引策略总结

### 6.1 核心查询场景与对应索引

| 查询场景 | 涉及表 | 索引 |
|----------|--------|------|
| 查看某赛事所有项目 | event_items | idx_event(event_id) |
| 查看某队伍所有报名 | entries | idx_team(team_id) |
| 查看某项目所有报名 | entries | idx_event_item(event_id, event_item_id) |
| 查看某项目比赛编排 | entry_schedules | idx_item_group_seq(event_item_id, group_no, sequence_no) |
| 查看某条目所有成绩 | scores | idx_entry_round(entry_id, round_no) |
| 查看补签记录 | entries | idx_late_checkin(event_id, late_checkin_at) |
| 按姓名搜索用户 | users | idx_real_name(real_name) |
| 查看某人参赛记录 | entry_members | idx_user(user_id) |

### 6.2 性能优化建议

1. **分页查询**：所有列表查询必须使用 LIMIT + OFFSET，配合主键索引
2. **避免 SELECT ***：明确指定需要的字段，减少数据传输
3. **JOIN 优化**：优先使用 INNER JOIN，必要时使用 LEFT JOIN
4. **统计查询**：使用视图或缓存，避免实时聚合大表
5. **分区表**：历史数据超过100万行时考虑按年份分区

---

## 七、数据完整性保障

### 7.1 外键约束

所有外键关系都已在表结构中定义，确保：
- 删除赛事时级联处理相关数据
- 用户删除时检查是否有关联数据
- 队伍删除时处理报名记录

### 7.2 CHECK 约束

- 年龄范围：min_age <= max_age
- 费用类型：根据 entry_type 限制对应费用字段
- 分数范围：所有分数字段 >= 0

### 7.3 唯一性约束

- 用户名、邮箱唯一
- 赛事编号唯一
- 报名编号唯一
- 同一项目同一条目只能有一个编排
- 同一轮次同一裁判不能重复打分

---

## 八、业务流程说明

### 8.1 报名流程

```
1. 用户注册/登录 → users
2. 创建队伍 → teams
3. 添加队员 → team_members
4. 报名项目 → entries + entry_members
5. 支付费用 → payment_records
6. 现场报到 → entries.status = 'checked_in'
7. 补签（逾期） → entries.status = 'late_checked_in'
```

### 8.2 编排流程

```
1. 系统自动生成初始编排 → entry_schedules
2. 项目经理手动调整 → 更新 entry_schedules
3. 记录调整历史 → schedule_adjustment_logs
4. 前端拖拽排序 → 批量更新 sequence_no
5. 重新计算全局序号 → global_sequence_no
```

### 8.3 比赛与评分流程

```
1. 按编排顺序开始比赛 → entry_schedules.status = 'in_progress'
2. 所有裁判打分 → scores (无需预分配)
3. 发现同分或需要调整 → 修改 scores 表
4. 记录修改历史 → score_modification_logs
5. 重新计算排名 → v_scores_ranking 视图
6. 完成比赛 → entry_schedules.status = 'completed'
```

### 8.4 成绩修改流程

```python
成绩修改业务逻辑：
1. 查询原始成绩记录
2. 验证修改权限（只有管理员或指定人员）
3. 记录修改前的值到 score_modification_logs
4. 更新 scores 表的成绩字段
5. 更新 modified_at, modified_by, version
6. 触发排名重新计算
7. 通知相关人员成绩已变更
```

### 8.5 同分处理策略

```sql
-- 场景1：完全同分，需要人工调整某项分数
UPDATE scores 
SET technique_score = 9.52,
    total_score = technique_score + performance_score - deduction,
    modified_by = ?,
    modified_at = NOW(),
    modification_reason = '同分调整',
    version = version + 1
WHERE id = ?;

-- 场景2：标记某个分数为无效（如误判）
UPDATE scores 
SET is_valid = FALSE,
    modified_by = ?,
    modified_at = NOW(),
    modification_reason = '裁判误判，该分数作废'
WHERE id = ?;

-- 场景3：查询同分情况
SELECT entry_id, AVG(total_score) as avg_score, COUNT(*) as entry_count
FROM scores
WHERE event_item_id = ? AND is_valid = TRUE
GROUP BY entry_id
HAVING entry_count > 1
ORDER BY avg_score DESC;
```

### 8.4 补签业务规则

```python
补签条件检查：
- 当前状态必须是 'registered'
- 比赛尚未开始（轮次 = 1）
- 在允许补签的时间范围内

补签操作：
- 更新状态为 'late_checked_in'
- 记录补签时间、操作人、原因
- 如有罚款，更新费用字段
- 创建支付记录（如需补缴）
```

---

## 九、扩展性设计

### 9.1 预留字段

各主表都预留了软删除字段 `deleted_at`，支持数据恢复。

### 9.2 配置化设计

- 赛事费用标准在 events 表中配置
- 项目规则在 event_items 表中配置
- 评分模式支持扩展（sum/avg/drop_high_low）

### 9.3 多租户支持

如需支持多个赛事组织方，可添加：
```sql
ALTER TABLE events ADD COLUMN organization_id INT;
ALTER TABLE users ADD COLUMN organization_id INT;
```

### 9.4 国际化支持

所有文本字段使用 utf8mb4 编码，支持：
- 中文、日文、韩文等多语言
- Emoji 表情符号
- 生僻汉字

---

## 十、安全性设计

### 10.1 密码安全

- 使用 bcrypt 或 argon2 加密密码
- password_hash 字段长度 255 字符
- 强制密码复杂度策略

### 10.2 敏感信息保护

- 身份证号 id_card 需加密存储
- 手机号 phone 需脱敏显示
- 支付流水号需加密传输

### 10.3 操作审计

所有关键操作都记录：
- created_by：创建人
- adjusted_by：调整人
- 时间戳：created_at, updated_at, deleted_at

---

## 十一、监控与维护

### 11.1 慢查询监控

```sql
-- 开启慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';
```

### 11.2 表空间监控

```sql
-- 查看表大小
SELECT 
  table_name,
  ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.TABLES
WHERE table_schema = 'martial_arts'
ORDER BY size_mb DESC;
```

### 11.3 定期维护

```sql
-- 优化表
OPTIMIZE TABLE entries;
OPTIMIZE TABLE scores;

-- 分析表
ANALYZE TABLE entries;
ANALYZE TABLE scores;
```

---

## 十二、数据迁移策略

### 12.1 从旧系统迁移

1. **导出旧数据**：使用 mysqldump 或编写导出脚本
2. **数据清洗**：统一字段格式、处理空值
3. **映射转换**：旧表字段映射到新表字段
4. **验证数据**：检查外键完整性、数据一致性
5. **灰度切换**：先迁移历史数据，再切换实时数据

### 12.2 回滚方案

- 保留旧表备份
- 使用事务批量导入
- 记录迁移日志便于追溯

---

## 十三、性能基准

### 13.1 预期性能指标

| 操作 | 响应时间 | 并发数 |
|------|----------|--------|
| 用户登录 | < 100ms | 1000 |
| 报名提交 | < 200ms | 500 |
| 编排查询 | < 150ms | 800 |
| 成绩录入 | < 100ms | 500 |
| 成绩排名 | < 300ms | 200 |

### 13.2 压力测试建议

使用 JMeter 或 Locust 进行压测：
- 模拟 1000+ 并发用户同时报名
- 模拟 100+ 裁判同时打分
- 模拟大量成绩查询请求

---

## 十四、总结

本数据库设计具备以下特点：

### ✅ 完整性
- 覆盖报名、编排、比赛、成绩全流程
- 支持补签、手动排序等实际业务需求
- 完善的费用管理和支付记录

### ✅ 规范性
- 遵循数据库设计范式
- 统一命名规范和字段类型
- 完整的约束和索引设计

### ✅ 扩展性
- 灵活的项目配置
- 可扩展的评分维度
- 预留多租户支持

### ✅ 性能
- 合理的索引策略
- 视图简化复杂查询
- 支持分区和缓存

### ✅ 安全性
- 密码加密存储
- 敏感信息保护
- 完整操作审计

---

## 附录：常用查询示例

### A.1 查询某赛事的报名统计

```sql
SELECT 
  t.name AS team_name,
  COUNT(DISTINCT e.id) AS entry_count,
  SUM(e.total_fee) AS total_fee,
  SUM(e.paid_amount) AS paid_amount,
  COUNT(DISTINCT em.user_id) AS athlete_count
FROM entries e
JOIN teams t ON e.team_id = t.id
LEFT JOIN entry_members em ON e.id = em.entry_id
WHERE e.event_id = ? AND e.deleted_at IS NULL
GROUP BY t.id
ORDER BY entry_count DESC;
```

### A.2 查询某项目的成绩排名（处理同分）

```sql
SELECT 
  e.registration_number,
  GROUP_CONCAT(u.real_name SEPARATOR ',') AS athletes,
  t.name AS team_name,
  AVG(s.total_score) AS avg_score,
  MAX(s.technique_score) AS max_technique_score,  -- 同分时按技术分高低
  RANK() OVER (ORDER BY AVG(s.total_score) DESC, MAX(s.technique_score) DESC) AS ranking
FROM scores s
JOIN entries e ON s.entry_id = e.id
JOIN entry_members em ON e.id = em.entry_id
JOIN users u ON em.user_id = u.id
LEFT JOIN teams t ON e.team_id = t.id
WHERE s.event_item_id = ? AND s.is_valid = TRUE
GROUP BY e.id
ORDER BY avg_score DESC, max_technique_score DESC;
```

### A.3 查询成绩修改历史

```sql
SELECT 
  sml.id,
  e.registration_number,
  GROUP_CONCAT(u.real_name SEPARATOR ',') AS athletes,
  uj.real_name AS judge_name,
  sml.old_total_score,
  sml.new_total_score,
  sml.modification_type,
  sml.reason,
  um.real_name AS modifier_name,
  sml.modified_at
FROM score_modification_logs sml
JOIN entries e ON sml.entry_id = e.id
JOIN users uj ON sml.judge_id = uj.id
JOIN users um ON sml.modified_by = um.id
LEFT JOIN entry_members em ON e.id = em.entry_id
LEFT JOIN users u ON em.user_id = u.id
WHERE sml.event_id = ?
GROUP BY sml.id
ORDER BY sml.modified_at DESC;
```

### A.4 查询所有裁判列表

```sql
SELECT 
  u.id,
  u.real_name,
  u.phone,
  COUNT(DISTINCT s.event_id) AS events_participated,
  COUNT(s.id) AS total_scores_given,
  AVG(s.total_score) AS avg_score_given
FROM users u
LEFT JOIN scores s ON u.id = s.judge_id
WHERE u.role = 'judge' AND u.is_active = TRUE
GROUP BY u.id
ORDER BY u.real_name;
```

```sql
SELECT 
  e.registration_number,
  ei.name AS item_name,
  GROUP_CONCAT(u.real_name SEPARATOR ',') AS athletes,
  e.checked_in_at,
  TIMESTAMPDIFF(HOUR, ev.registration_end, NOW()) AS hours_late
FROM entries e
JOIN event_items ei ON e.event_item_id = ei.id
JOIN events ev ON e.event_id = ev.id
LEFT JOIN entry_members em ON e.id = em.entry_id
LEFT JOIN users u ON em.user_id = u.id
WHERE e.event_id = ? 
  AND e.status = 'registered'
  AND NOW() > ev.registration_end
GROUP BY e.id;
```

---

**文档版本**: v2.0  
**最后更新**: 2024-11-27  
**维护人员**: 数据库设计团队