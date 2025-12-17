# 武术赛事管理系统数据库重构设计（统一版）

> **版本**: v1.0  
> **数据库**: MySQL 8.0+（现有库名：`wu_shu`）  
> **现有访问方式**: `mysql.connector` + `DatabaseManager`  
> **目标访问方式**: SQLAlchemy 2.x ORM（库名可沿用 `wu_shu` 或迁移至 `martial_arts`）  
> **关联文档**：  
> - `database_schema.md`（ORM 目标结构概览）  
> - `martial_arts_db_design.md`（改进版表级设计）  
> - `martial_arts_sql_orm.md`（建表 SQL + ORM 模型）

---

## 0. 当前实现概况

### 0.1 技术栈与架构

- **后端框架**：Flask 单应用，`app.py` 负责创建应用并注册多个 Blueprint：
  - 账号：`api.account.auth` / `api.account.users`
  - 赛事+参赛：`api.events`、`api.participants`、`api.players`、`api.teams`、`api.scoring`、`api.categories`
  - 仪表盘、通知、维护：`api.dashboard`、`api.communication`、`api.announcements`、`api.maintenance`
- **数据库访问**：
  - `database.DatabaseManager` 使用 `mysql.connector` + 连接池访问 MySQL；
  - 数据库名通过 `config.Config.DB_NAME` 配置，当前默认值为 `wu_shu`；
  - 表结构来自 `models.DATABASE_SCHEMA` 中的 DDL 字符串，以及 `DatabaseManager._migrate_database()` / `_ensure_event_columns()` 这类迁移逻辑，与三份设计文档中的 SQLAlchemy/新库设计尚未打通。

### 0.2 已落地的核心表（`models.DATABASE_SCHEMA`）

> 下列仅列出与赛事/报名/成绩直接相关的表，其余通知/维护类表在本设计中保持基本不变。

- **`users`**
  - 职责：账号与基础信息。  
  - 字段要点：`user_id` / `username` / `real_name` / `nickname` / `team_name` / `email` / `phone` / `role` / `status` / `is_active` / `password(明文)` / 时间戳索引。  
  - 角色范围：`super_admin` / `admin` / `judge` / `user`。

- **`events`**
  - 职责：赛事基本信息与报名窗口。  
  - 字段要点：`event_id` / `name` / `description` / `start_date` / `end_date` / `location` / `max_participants` / `registration_start_time` / `registration_deadline` / `status` / `created_by` / 费用字段 (`individual_fee` / `pair_practice_fee` / `team_competition_fee`) / 扩展信息（`contact_phone` / `organizer` / `co_organizer`）。  
  - API 使用：`api/events/get_events.py`、`create_event.py`、`get_event.py`、仪表盘统计等。

- **`participants`**
  - 职责：当前实现中，“某用户参加某场赛事”的报名记录，附带粗粒度项目信息。  
  - 字段要点：`participant_id` / `event_id` / `user_id` / `registration_number` / `event_member_no` / `category` / `weight_class` / `gender` / `age_group` / `status` / `registered_at` / `checked_in_at`，并有 `UNIQUE(event_id, user_id)` 与 `UNIQUE(event_id, event_member_no)`。  
  - 业务承担：
    - 报名接口：`api/events/register_event.py` 直接创建 `Participant`；
    - 参赛者列表：`api/events/get_participants.py`；
    - 成绩统计：`DatabaseManager.get_event_results()` 以 `participant_id` 聚合 `scores`。
  - 问题：将胸牌身份、项目报名条目、条目成员等概念混合在同一层次，难以扩展到多项目、多人/团体赛。

- **`scores`**
  - 职责：基于参赛者的评分记录。  
  - 字段要点：`score_id` / `participant_id` / `judge_id` / `round_number` / `technique_score` / `performance_score` / `deduction` / 派生列 `total_score` / `scored_at` / `updated_at`；
  - 约束：`UNIQUE(participant_id, judge_id, round_number)`、`idx_participant_round`、`idx_judge`。  
  - 业务：被 `DatabaseManager.create_or_update_score()`、`get_scores_by_participant()`、`get_event_results()` 使用，并由 `api/events/get_event_results.py` 根据配置进行去最高/最低分与排序。

- **队伍与报名相关表**
  - `teams`：赛事代表队/俱乐部，包括领队信息、`client_team_key` 等，用于前端队伍管理。  
  - `team_applications`：团队报名申请与费用明细草稿。  
  - `team_players`：队员名单，包含 `participant_id`、报名项目描述、选项等。  
  - `team_staff`：工作人员/教练；  
  - `team_drafts`：队伍草稿。  
  它们共同构成交互复杂但模型不统一的一套“老设计”。

- **通知与维护表**
  - `notifications` / `user_notifications` / `announcements` / `maintenance_logs`：与本次数据库核心重构关系较弱，仅做必要字段级演进即可。

---

## 1. 重构目标与边界

### 1.1 目标

- **统一数据模型**：
  - 用一套清晰的一致的表结构覆盖“用户 / 赛事 / 项目 / 队伍 / 报名 / 成绩 / 费用”全流程；
  - 消除历史遗留的 `participants` / `team_players` / `team_staff` / `team_applications` 等表职责重叠与语义不清的问题。

- **显式项目与条目层**：
  - 将当前 `participants.category/weight_class` 中隐含的“项目”概念，拆解为：
    - 赛事项目：`event_items`；
    - 报名条目：`entries`；
    - 条目成员：`entry_members`；
    - 赛事参与身份：`event_participants`（胸牌/签到层）。

- **安全与审计**：
  - 用户密码从明文 `password` 迁移到 `password_hash`，并逐渐引入密码强度校验；
  - 成绩支持修改历史与审计：`score_modification_logs` + 视图/统计。

- **性能与查询友好**：
  - 所有外键字段建立合理索引；
  - 高频列表（报名列表、成绩列表、编排列表）使用符合业务的复合索引；
  - 适当引入视图和触发器简化查询与保证数据一致性。

- **向 SQLAlchemy 过渡**：
  - 在保持现有 `DatabaseManager` 可用的前提下，引入 SQLAlchemy ORM 模型文件，并通过分层（models / repositories / services）逐步迁移查询与写入逻辑。

### 1.2 边界

- 不在本次重构中大改前端协议，仅通过后端适配与数据结构演进保证兼容；
- `notifications`、`announcements`、`maintenance_logs` 等辅助表结构保持基本不变，仅按需要补充索引/软删除字段。

---

## 2. 目标数据模型概览（统一）

> 该部分整合 `database_schema.md` 和 `martial_arts_db_design.md` 中的目标实体，保持与现有业务范围一致。

### 2.1 核心实体

- `User`：系统用户与个人基础信息。  
- `Event`：一场完整赛事（可以包含多个项目）。  
- `EventItem`：赛事项目/组别（个人/对练/团体，限性别/年龄/体重等）。  
- `Team`：赛事下的代表队/俱乐部/学校。  
- `TeamMember`：队内成员（运动员/教练/领队/工作人员）。  
- `EventParticipant`：某用户在某场赛事中的参与身份（运动员/教练/裁判/官员等），对应胸牌/证件。  
- `Entry`：在某个 `EventItem` 下的一条报名记录（单人、对练组合或一支队伍）。  
- `EntryMember`：构成某个 `Entry` 的人员明细（一人/二人/多人）。  
- `EntrySchedule`：比赛编排（分组、出场顺序、场地、时间等）。  
- `ScheduleAdjustmentLog`：编排调整历史。  
- `Score`：裁判在某轮对某报名条目的评分。  
- `ScoreModificationLog`：成绩修改历史记录。  
- `PaymentRecord`：报名及相关费用支付流水。

### 2.2 统一关系（文字 ER）

```text
User (1) ─── (N) Event           [创建赛事]
User (1) ─── (N) Team            [创建队伍/领队]
User (1) ─── (N) TeamMember      [队内成员]
User (1) ─── (N) EventParticipant[参加赛事：运动员/教练/裁判/官员]
User (1) ─── (N) EntryMember     [某条目中的运动员]
User (1) ─── (N) Score           [裁判打分]

Event (1) ─── (N) EventItem      [赛事项目]
Event (1) ─── (N) Team           [参赛队伍]
Event (1) ─── (N) EventParticipant
Event (1) ─── (N) Entry          [报名条目]

EventItem (1) ─── (N) Entry      [项目下的所有条目]
EventItem (1) ─── (N) EntrySchedule

Team (1) ─── (N) TeamMember
Team (1) ─── (N) Entry           [队伍在项目中的报名]
Team (1) ─── (N) PaymentRecord

Entry (1) ─── (N) EntryMember
Entry (1) ─── (N) Score
Entry (1) ─── (1) EntrySchedule

Score (1) ─── (N) ScoreModificationLog
```

该模型即 `martial_arts_db_design.md` 与 `martial_arts_sql_orm.md` 中表结构设计的抽象统一版本。

---

## 3. 现状 vs 目标映射（按模块）

### 3.1 用户与安全

- **现状**：
  - 表：`wu_shu.users`；字段中存在明文 `password`，无 `password_hash`、`id_card`、`gender`、`birthdate`、`deleted_at` 等；
  - 登录认证：`user_manager.UserManager.authenticate_user()` 直接比较明文密码。

- **目标**（参考 `martial_arts_db_design.md`、`martial_arts_sql_orm.md`）：
  - 增加安全字段：`password_hash`、`id_card`、`gender`、`birthdate`、`deleted_at`；
  - 密码只以哈希形式存储，明文仅在迁移期保留；
  - 支持更多角色（`coach` / `athlete` / `staff` 等）与操作审计字段。

- **迁移要点**：
  - 在 `wu_shu.users` 上 `ALTER TABLE` 增加上述字段；
  - 注册/重置密码接口改为写 `password_hash`，并逐步迁移旧用户密码；
  - 登录逻辑优先使用哈希验证，旧的明文字段仅在过渡期使用；
  - 数据稳定后，移除对明文 `password` 的依赖，必要时将其置空或废弃。

### 3.2 赛事管理

- **现状**：
  - 表：`wu_shu.events`；字段为 `event_id` / `name` / `description` / `start_date` / `end_date` / `location` / `max_participants` / 报名时间 / 状态 / 费用字段 / 扩展列；
  - API 已经支持高级筛选、分页与统计（`get_events.py`）。

- **目标**（`events` in `martial_arts_*`）：
  - 引入统一赛事编号 `code`，用于短链接与对外展示；
  - 时间字段命名一致（`start_time` / `end_time`），兼容现有 `start_date` / `end_date`；
  - 费用字段拆分并统一命名（`individual_fee` / `pair_fee` / `team_fee`）；
  - 软删除字段 `deleted_at`，及更丰富的公开性配置（`is_public`、`max_teams` 等）。

- **迁移要点**：
  - 在现有 `events` 表上 `ADD COLUMN code / logo_url / is_public / max_teams / deleted_at` 等；
  - 将 `start_date` / `end_date` 与新字段并行存在（视业务是否需要物理重命名）；
  - 将 `pair_practice_fee` / `team_competition_fee` 语义上对齐为 `pair_fee` / `team_fee`，可采用视图或兼容字段名。

### 3.3 报名与队伍

- **现状**：
  - 参赛身份+报名条目：`participants`（承担胸牌+项目信息）；
  - 队伍与队内结构：`teams` + `team_players` + `team_staff` + `team_applications` + `team_drafts`；
  - 无独立的 `event_items` / `entries` / `entry_members` 结构，难以精确表达“项目 + 单位 + 成员”。

- **目标**：
  - 赛事项目：`event_items`；
  - 赛事参与身份（胸牌）：`event_participants`；
  - 报名条目：`entries`（带报名编号、状态、费用、签到与补签字段）；
  - 条目成员：`entry_members`；
  - 队伍成员：`team_members`；
  - 支付流水：`payment_records`；
  - 详见 `martial_arts_db_design.md` 3.2–3.9、3.14 章节。

- **迁移要点**：
  - 在 `wu_shu` 库中 **新增** 目标表，而不是直接替换旧表；
  - 引入服务层映射层，将现有 `participants` / `team_players` 等数据映射到 `event_participants` / `entries` / `entry_members` / `team_members`；
  - 分阶段把报名/队伍相关 API 的读写从旧表迁移到新表，最终将旧表降级为兼容视图或只读历史数据表。

### 3.4 成绩与裁判

- **现状**：
  - 成绩表：`scores`，以 `participant_id` 为主外键；
  - 仅记录当前成绩，不含修改历史、有效性标记等；
  - `get_event_results()` 按参赛者维度汇总成绩，未显式区分项目/条目。

- **目标**：
  - 完整的 `scores` 表：包含 `event_id` / `event_item_id` / `entry_id` / `judge_id` / `round_no` / 分数字段 / 有效性 /签名 / 修改信息 / 乐观锁版本等；
  - `score_modification_logs`：成绩修改历史；
  - 视图：`v_scores_ranking` / `v_judge_statistics` 等；
  - 详见 `martial_arts_db_design.md` 3.12–3.13 与 `martial_arts_sql_orm.md` 对应部分。

- **迁移要点**：
  - 在现有 `scores` 表中增列（如 `event_id` / `event_item_id` / `entry_id` / `is_valid` / `version` 等），或按目标结构新建 `scores_v2` 表并逐步迁移；
  - 引入触发器自动维护 `total_score`、修改历史与版本号（已在 `martial_arts_sql_orm.md` 中给出）；
  - 将 `DatabaseManager.get_event_results()` 改造为基于 `entries` / `event_items` 统计的实现，兼容旧逻辑。

---

## 4. 分阶段迁移与重构计划

> 该计划整合三份文档中的迁移思路，并明确在现有 `wu_shu` 库上渐进演进的步骤。

### 阶段 0：准备与安全加固

1. **用户表加固**：
   - 在 `wu_shu.users` 上 `ADD COLUMN`：`password_hash`、`id_card`、`gender`、`birthdate`、`deleted_at`（可选）；
   - 更新注册/重置密码接口：写入 `password_hash`，保留旧 `password` 仅供迁移期间使用；
   - 登录逻辑调整为优先验证 `password_hash`。

2. **赛事表补全**：
   - 在 `events` 表中 `ADD COLUMN`：`code`、`logo_url`、`is_public`、`max_teams`、`deleted_at`；
   - 兼容现有字段与费用命名，将具体 DDL 对齐到 `martial_arts_db_design.md` 的 `events` 设计。

### 阶段 1：引入新结构（不切流量）

1. 在 `wu_shu` 中创建以下**新表**（按 `martial_arts_sql_orm.md` 的 DDL 适配）：
   - `event_items`
   - `event_participants`
   - `entries`
   - `entry_members`
   - `entry_schedules`
   - `schedule_adjustment_logs`
   - `payment_records`
   - `score_modification_logs`（以及对 `scores` 的字段增补）

2. 此阶段 **不修改** 现有业务读写逻辑：
   - 所有报名、队伍、成绩操作仍走 `participants` / `teams` / `team_players` / 老 `scores`；
   - 新表仅提供结构，并可用脚本从旧数据增量同步，验证模型正确性与性能。

### 阶段 2：服务层抽象与双写

1. 在 Python 侧引入新的服务/仓储层：
   - `services/registration_service.py`：统一封装从“用户报名赛事”到创建 `event_participants` / `entries` / `entry_members` 的逻辑；
   - `services/scoring_service.py`：封装评分与成绩修改，写入新 `scores` + `score_modification_logs`；
   - `repositories/*`：基于 SQLAlchemy 或现有 `DatabaseManager` 提供表级 CRUD（根据你后续选择的技术路径）。

2. 对关键写入操作实施“双写”策略：
   - 报名时：写旧表 (`participants` / `team_players`) 的同时写新表 (`event_participants` / `entries` / `entry_members`)；
   - 成绩录入时：在旧 `scores` 保持兼容的前提下，优先写入新 `scores` 结构与修改日志；
   - 队伍结构同理。

### 阶段 3：切换读路径

1. 报名/参赛列表：
   - 把参赛者/报名列表 API 的数据来源从 `participants` / `team_players` 改为 `entries` + `entry_members` + `event_participants`；
   - 保持输出 JSON 结构兼容（必要时在服务层适配字段名）。

2. 成绩/排名：
   - 将 `get_event_results()` 改造为基于新 `scores` + `entries` + `event_items`；
   - 利用 `v_scores_ranking` 等视图进行复杂聚合。

3. 队伍/费用：
   - 队伍成员列表改为基于 `teams` + `team_members`；
   - 费用统计基于 `entries` + `payment_records`；
   - 老的 `team_applications` / `team_players` / `team_staff` 逐步退化为只读历史或视图。

### 阶段 4：清理与 ORM 完成迁移

1. 删除或重命名不再使用的表字段：
   - 视情况废弃 `participants`（或转为视图）、`team_applications`、`team_players`、`team_staff`、`team_drafts` 等；
   - 移除对明文 `password` 的依赖。

2. SQLAlchemy 集成：
   - 按 `martial_arts_sql_orm.md` 中的模型定义拆分 Python ORM 模型文件；
   - 将新业务逻辑优先使用 SQLAlchemy Session，实现查询/更新；
   - 保留 `DatabaseManager` 仅用于兼容阶段，最终可被替换为基于 ORM 的仓储类。

---

## 5. 与三份详细设计文档的关系

- **`database_schema.md`**：
  - 提供了较为抽象的 ORM 版核心实体结构和设计思路；
  - 本统一文档的第 2 章基本对应其“实体与关系概览”。

- **`martial_arts_db_design.md`**：
  - 给出了详尽的字段级设计、索引策略、视图/触发器建议和业务流程说明；
  - 本统一文档在第 3–4 章中只抽取了与迁移直接相关的部分，字段细节以该文档为准。

- **`martial_arts_sql_orm.md`**：
  - 提供可直接执行的建表 SQL、视图与触发器脚本，以及部分 ORM 示例；
  - 本统一文档只定义“在何时创建哪些表/视图/触发器”，具体 SQL 依赖该文件实现。

---

## 6. 实施建议（优先级）

1. **立即可做（风险低）**：
   - 阶段 0：给 `users` 与 `events` 补安全和管理字段；
   - 在 `events` 与 `users` 相关 API 中引入对新字段的读写（不影响现有字段）。

2. **下一个里程碑**：
   - 创建 `event_items` / `event_participants` / `entries` / `entry_members` / `score_modification_logs` 等关键新表；
   - 在服务层实现写入双写策略，保证新旧结构数据一致。

3. **集中窗口改造**：
   - 选定一个版本周期，完成报名与成绩读路径切换到新模型，确保列表/统计/导出全部基于 `entries` / `scores` 新结构；
   - 随后进行老表的清理与视图化处理。

本统一文档作为“**从当前 `wu_shu` 实现到目标 SQLAlchemy 模型的路线图**”，配合三份详细设计文档，可以指导团队进行分阶段的数据库和代码重构。
