import logging
import time

from mysql.connector import Error

from models import Event


logger = logging.getLogger(__name__)

_event_participants_cache = {}
_EVENT_PARTICIPANTS_CACHE_TTL = 10
_event_count_cache = {}
_EVENT_COUNT_CACHE_TTL = 10


class EventDbMixin:
    """赛事相关数据库操作 mixin。

    依赖宿主类提供:
    - self.get_connection(): 返回数据库连接的上下文管理器
    """

    # ==================== 赛事相关操作 ====================
    
    def _ensure_event_columns(self, cursor):
        """确保events表包含新的列"""
        try:
            # 检查contact_phone列是否存在
            cursor.execute("SHOW COLUMNS FROM events LIKE 'contact_phone'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE events ADD COLUMN contact_phone VARCHAR(20) DEFAULT NULL")
            
            # 检查organizer列是否存在
            cursor.execute("SHOW COLUMNS FROM events LIKE 'organizer'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE events ADD COLUMN organizer VARCHAR(255) DEFAULT NULL")
            
            # 检查co_organizer列是否存在
            cursor.execute("SHOW COLUMNS FROM events LIKE 'co_organizer'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE events ADD COLUMN co_organizer VARCHAR(255) DEFAULT NULL")
            
            # 检查code列是否存在
            cursor.execute("SHOW COLUMNS FROM events LIKE 'code'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE events ADD COLUMN code VARCHAR(50) DEFAULT NULL")

            # 检查logo_url列是否存在
            cursor.execute("SHOW COLUMNS FROM events LIKE 'logo_url'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE events ADD COLUMN logo_url VARCHAR(500) DEFAULT NULL")

            # 检查is_public列是否存在
            cursor.execute("SHOW COLUMNS FROM events LIKE 'is_public'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE events ADD COLUMN is_public BOOLEAN DEFAULT TRUE")

            # 检查max_teams列是否存在
            cursor.execute("SHOW COLUMNS FROM events LIKE 'max_teams'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE events ADD COLUMN max_teams INT DEFAULT NULL")

            # 检查deleted_at列是否存在
            cursor.execute("SHOW COLUMNS FROM events LIKE 'deleted_at'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE events ADD COLUMN deleted_at TIMESTAMP NULL")

            # 赛事费用字段（有些历史库可能缺列）
            cursor.execute("SHOW COLUMNS FROM events LIKE 'individual_fee'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE events ADD COLUMN individual_fee DECIMAL(10,2) DEFAULT 0.00")

            cursor.execute("SHOW COLUMNS FROM events LIKE 'pair_practice_fee'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE events ADD COLUMN pair_practice_fee DECIMAL(10,2) DEFAULT 0.00")

            cursor.execute("SHOW COLUMNS FROM events LIKE 'team_competition_fee'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE events ADD COLUMN team_competition_fee DECIMAL(10,2) DEFAULT 0.00")
                
        except Error as e:
            logger.warning(f"检查/添加events表列时出错: {e}")
    
    def create_event(self, event):
        """创建赛事"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO events (name, description, start_date, end_date, location, 
                                      max_participants, registration_start_time, registration_deadline, 
                                      status, created_by, contact_phone, organizer, co_organizer,
                                      individual_fee, pair_practice_fee, team_competition_fee)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (event.name, event.description, event.start_date, event.end_date,
                      event.location, event.max_participants, event.registration_start_time, event.registration_deadline,
                      event.status.value, event.created_by, event.contact_phone, event.organizer, event.co_organizer,
                      getattr(event, 'individual_fee', 0) or 0,
                      getattr(event, 'pair_practice_fee', 0) or 0,
                      getattr(event, 'team_competition_fee', 0) or 0))
                
                event.event_id = cursor.lastrowid
                conn.commit()
                return event
                
        except Error as e:
            logger.error(f"创建赛事失败: {e}")
            raise

    def get_event_by_id(self, event_id):
        """根据ID获取赛事"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                cursor.execute("SELECT * FROM events WHERE event_id = %s", (event_id,))
                row = cursor.fetchone()
                
                if row:
                    return Event(
                        event_id=row['event_id'],
                        name=row['name'],
                        description=row['description'],
                        start_date=row['start_date'],
                        end_date=row['end_date'],
                        location=row['location'],
                        max_participants=row['max_participants'],
                        registration_start_time=row.get('registration_start_time'),
                        registration_deadline=row['registration_deadline'],
                        status=row['status'],
                        created_by=row['created_by'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        contact_phone=row.get('contact_phone'),
                        organizer=row.get('organizer'),
                        co_organizer=row.get('co_organizer'),
                        individual_fee=row.get('individual_fee') or 0,
                        pair_practice_fee=row.get('pair_practice_fee') or 0,
                        team_competition_fee=row.get('team_competition_fee') or 0
                    )
                return None
                
        except Error as e:
            logger.error(f"获取赛事失败: {e}")
            raise

    def _build_event_where(self, status=None, keyword=None, date_from=None, date_to=None,
                           location=None, created_by=None, min_participants=None, max_participants=None):
        """构建赛事查询的 WHERE 子句和参数（复用于 count / list）"""
        where_clauses = []
        params = []

        if status:
            where_clauses.append("status = %s")
            params.append(status)
        if keyword:
            where_clauses.append("name LIKE %s")
            params.append(f"%{keyword}%")
        if date_from:
            where_clauses.append("start_date >= %s")
            params.append(date_from)
        if date_to:
            where_clauses.append("start_date <= %s")
            params.append(date_to)
        if location:
            where_clauses.append("location LIKE %s")
            params.append(f"%{location}%")
        if created_by:
            where_clauses.append("created_by = %s")
            params.append(created_by)
        if min_participants:
            where_clauses.append("max_participants >= %s")
            params.append(min_participants)
        if max_participants:
            where_clauses.append("max_participants <= %s")
            params.append(max_participants)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        return where_sql, params

    def get_events_with_count(self, status=None, keyword=None, date_from=None, date_to=None,
                              location=None, created_by=None, min_participants=None, max_participants=None,
                              order_by='start_date', order_dir='DESC', limit=None, offset=None):
        """在同一连接中同时获取赛事列表和总数，减少连接开销"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)

                if not getattr(self, '_event_columns_ensured', False):
                    self._ensure_event_columns(cursor)
                    setattr(self, '_event_columns_ensured', True)

                where_sql, params = self._build_event_where(
                    status=status, keyword=keyword, date_from=date_from, date_to=date_to,
                    location=location, created_by=created_by,
                    min_participants=min_participants, max_participants=max_participants)

                # 查总数
                cursor.execute("SELECT COUNT(*) AS cnt FROM events" + where_sql, params)
                total = cursor.fetchone()['cnt']

                # 查列表
                allowed_order_fields = ['start_date', 'end_date', 'created_at', 'updated_at', 'name', 'max_participants']
                if order_by in allowed_order_fields and order_dir in ['ASC', 'DESC']:
                    order_clause = f" ORDER BY {order_by} {order_dir}"
                else:
                    order_clause = " ORDER BY start_date DESC"

                list_sql = "SELECT * FROM events" + where_sql + order_clause
                list_params = list(params)
                if limit:
                    list_sql += " LIMIT %s"
                    list_params.append(limit)
                    if offset:
                        list_sql += " OFFSET %s"
                        list_params.append(offset)

                cursor.execute(list_sql, list_params)

                events = []
                for row in cursor.fetchall():
                    events.append(Event(
                        event_id=row['event_id'],
                        name=row['name'],
                        description=row['description'],
                        start_date=row['start_date'],
                        end_date=row['end_date'],
                        location=row['location'],
                        max_participants=row['max_participants'],
                        registration_start_time=row.get('registration_start_time'),
                        registration_deadline=row['registration_deadline'],
                        status=row['status'],
                        created_by=row['created_by'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        contact_phone=row.get('contact_phone'),
                        organizer=row.get('organizer'),
                        co_organizer=row.get('co_organizer')
                    ))

                # 批量获取参赛人数（同一连接）
                event_ids = [e.event_id for e in events]
                participants_counts = {}
                if event_ids:
                    placeholders = ','.join(['%s'] * len(event_ids))
                    cursor.execute(
                        "SELECT event_id, COUNT(*) AS cnt FROM event_participants "
                        f"WHERE event_id IN ({placeholders}) AND role = 'athlete' GROUP BY event_id",
                        tuple(event_ids),
                    )
                    participants_counts = {row['event_id']: row['cnt'] for row in cursor.fetchall()}

                    missing_ids = [eid for eid in event_ids if eid not in participants_counts]
                    if missing_ids:
                        ph2 = ','.join(['%s'] * len(missing_ids))
                        cursor.execute(
                            f"SELECT event_id, COUNT(*) AS cnt FROM participants WHERE event_id IN ({ph2}) GROUP BY event_id",
                            tuple(missing_ids),
                        )
                        for row in cursor.fetchall():
                            participants_counts[row['event_id']] = row['cnt']

                return total, events, participants_counts

        except Error as e:
            logger.error(f"获取赛事列表失败: {e}")
            raise

    def get_all_events(self, status=None, keyword=None, date_from=None, date_to=None, 
                       location=None, created_by=None, min_participants=None, max_participants=None,
                       order_by='start_date', order_dir='DESC', limit=None, offset=None):
        """获取所有赛事（支持高级筛选）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)

                if not getattr(self, '_event_columns_ensured', False):
                    self._ensure_event_columns(cursor)
                    setattr(self, '_event_columns_ensured', True)

                where_sql, params = self._build_event_where(
                    status=status, keyword=keyword, date_from=date_from, date_to=date_to,
                    location=location, created_by=created_by,
                    min_participants=min_participants, max_participants=max_participants)

                allowed_order_fields = ['start_date', 'end_date', 'created_at', 'updated_at', 'name', 'max_participants']
                if order_by in allowed_order_fields and order_dir in ['ASC', 'DESC']:
                    order_clause = f" ORDER BY {order_by} {order_dir}"
                else:
                    order_clause = " ORDER BY start_date DESC"

                sql = "SELECT * FROM events" + where_sql + order_clause
                list_params = list(params)
                if limit:
                    sql += " LIMIT %s"
                    list_params.append(limit)
                    if offset:
                        sql += " OFFSET %s"
                        list_params.append(offset)
                
                cursor.execute(sql, list_params)
                
                events = []
                for row in cursor.fetchall():
                    events.append(Event(
                        event_id=row['event_id'],
                        name=row['name'],
                        description=row['description'],
                        start_date=row['start_date'],
                        end_date=row['end_date'],
                        location=row['location'],
                        max_participants=row['max_participants'],
                        registration_start_time=row.get('registration_start_time'),
                        registration_deadline=row['registration_deadline'],
                        status=row['status'],
                        created_by=row['created_by'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        contact_phone=row.get('contact_phone'),
                        organizer=row.get('organizer'),
                        co_organizer=row.get('co_organizer')
                    ))
                
                return events
                
        except Error as e:
            logger.error(f"获取赛事列表失败: {e}")
            raise

    def count_events(self, status=None, keyword=None, date_from=None, date_to=None, 
                     location=None, created_by=None, min_participants=None, max_participants=None):
        """统计赛事数量（支持筛选条件）"""
        key = (
            status,
            keyword,
            date_from,
            date_to,
            location,
            created_by,
            min_participants,
            max_participants,
        )
        now = time.time()
        entry = _event_count_cache.get(key)
        if entry:
            expires_at, cached_total = entry
            if now < expires_at:
                return cached_total

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建查询条件
                where_clauses = []
                params = []
                
                if status:
                    where_clauses.append("status = %s")
                    params.append(status)
                
                if keyword:
                    where_clauses.append("name LIKE %s")
                    params.append(f"%{keyword}%")
                
                if date_from:
                    where_clauses.append("start_date >= %s")
                    params.append(date_from)
                
                if date_to:
                    where_clauses.append("start_date <= %s")
                    params.append(date_to)
                
                if location:
                    where_clauses.append("location LIKE %s")
                    params.append(f"%{location}%")
                
                if created_by:
                    where_clauses.append("created_by = %s")
                    params.append(created_by)
                
                if min_participants:
                    where_clauses.append("max_participants >= %s")
                    params.append(min_participants)
                
                if max_participants:
                    where_clauses.append("max_participants <= %s")
                    params.append(max_participants)
                
                # 构建SQL查询
                sql = "SELECT COUNT(*) FROM events"
                if where_clauses:
                    sql += " WHERE " + " AND ".join(where_clauses)
                
                cursor.execute(sql, params)
                row = cursor.fetchone()
                total = row[0] if row else 0
                _event_count_cache[key] = (now + _EVENT_COUNT_CACHE_TTL, total)
                return total
                
        except Error as e:
            logger.error(f"统计赛事数量失败: {e}")
            raise

    def count_events_group_by_status(self):
        """按状态统计赛事数量，返回 {status: count}"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT status, COUNT(*) FROM events GROUP BY status")
                return {row[0]: row[1] for row in cursor.fetchall()}
        except Error as e:
            logger.error(f"按状态统计赛事数量失败: {e}")
            raise

    def count_participants_by_event(self, event_id):
        """统计指定赛事的参赛人数"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM event_participants WHERE event_id = %s AND role = 'athlete'",
                    (event_id,),
                )
                row = cursor.fetchone()
                count = row[0] if row else 0
                if count == 0:
                    cursor.execute(
                        "SELECT COUNT(*) FROM participants WHERE event_id = %s",
                        (event_id,),
                    )
                    row = cursor.fetchone()
                    count = row[0] if row else 0
                return count
        except Error as e:
            logger.error(f"统计参赛人数失败: {e}")
            raise

    def count_participants_by_events(self, event_ids):
        """批量统计多个赛事的参赛人数，返回 {event_id: count}"""
        if not event_ids:
            return {}

        key = tuple(sorted(set(event_ids)))
        now = time.time()
        entry = _event_participants_cache.get(key)
        if entry:
            expires_at, cached_result = entry
            if now < expires_at:
                return cached_result

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                placeholders = ','.join(['%s'] * len(event_ids))
                sql = (
                    "SELECT event_id, COUNT(*) FROM event_participants "
                    f"WHERE event_id IN ({placeholders}) AND role = 'athlete' GROUP BY event_id"
                )
                cursor.execute(sql, tuple(event_ids))
                result = {event_id: count for event_id, count in cursor.fetchall()}

                missing_ids = [eid for eid in event_ids if eid not in result]
                if missing_ids:
                    placeholders_missing = ','.join(['%s'] * len(missing_ids))
                    sql_fallback = (
                        "SELECT event_id, COUNT(*) FROM participants "
                        f"WHERE event_id IN ({placeholders_missing}) GROUP BY event_id"
                    )
                    cursor.execute(sql_fallback, tuple(missing_ids))
                    for event_id, count in cursor.fetchall():
                        result[event_id] = count

                _event_participants_cache[key] = (now + _EVENT_PARTICIPANTS_CACHE_TTL, result)
                return result
        except Error as e:
            logger.error(f"批量统计参赛人数失败: {e}")
            raise

    def delete_event(self, event_id):
        """删除赛事"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 先删除与新结构相关的记录（按依赖顺序）

                # 1) 成绩修改日志
                cursor.execute(
                    "DELETE FROM score_modification_logs WHERE event_id = %s",
                    (event_id,),
                )

                # 2) 比赛编排表
                cursor.execute(
                    "DELETE FROM entry_schedules WHERE event_id = %s",
                    (event_id,),
                )

                # 3) 编排调整日志（通过 event_items 反查赛事）
                cursor.execute(
                    """
                    DELETE l FROM schedule_adjustment_logs l
                    JOIN event_items ei ON l.event_item_id = ei.event_item_id
                    WHERE ei.event_id = %s
                    """,
                    (event_id,),
                )

                # 4) 支付记录
                cursor.execute(
                    "DELETE FROM payment_records WHERE event_id = %s",
                    (event_id,),
                )

                # 5) 报名成员（依赖 entries）
                cursor.execute(
                    """
                    DELETE em FROM entry_members em
                    JOIN entries e ON em.entry_id = e.entry_id
                    WHERE e.event_id = %s
                    """,
                    (event_id,),
                )

                # 6) 报名条目
                cursor.execute(
                    "DELETE FROM entries WHERE event_id = %s",
                    (event_id,),
                )

                # 7) 删除旧结构中的评分记录（通过 participant 关联）
                cursor.execute(
                    """
                    DELETE s FROM scores s
                    INNER JOIN participants p ON s.participant_id = p.participant_id
                    WHERE p.event_id = %s
                    """,
                    (event_id,),
                )

                # 8) 然后删除相关的参赛者记录
                cursor.execute("DELETE FROM participants WHERE event_id = %s", (event_id,))
                # 同步删除新结构表中的赛事参与者记录
                cursor.execute("DELETE FROM event_participants WHERE event_id = %s", (event_id,))

                # 9) 最后删除赛事本身（event_items 等通过 FK ON DELETE CASCADE 自动删除）
                cursor.execute("DELETE FROM events WHERE event_id = %s", (event_id,))

                # 检查是否真的删除了
                affected_rows = cursor.rowcount
                conn.commit()

                return affected_rows > 0
                
        except Error as e:
            logger.error(f"删除赛事失败: {e}")
            raise

    def get_event_participants(self, event_id):
        """获取赛事的参赛者列表（用于删除前检查）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT p.*, u.username, u.real_name 
                    FROM participants p 
                    JOIN users u ON p.user_id = u.user_id 
                    WHERE p.event_id = %s
                """, (event_id,))
                return cursor.fetchall()
                
        except Error as e:
            logger.error(f"获取赛事参赛者失败: {e}")
            raise

    def update_event(self, event_id, event):
        """更新赛事"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE events SET 
                        name = %s, 
                        description = %s, 
                        start_date = %s, 
                        end_date = %s, 
                        location = %s, 
                        max_participants = %s, 
                        registration_start_time = %s, 
                        registration_deadline = %s, 
                        status = %s,
                        contact_phone = %s,
                        organizer = %s,
                        co_organizer = %s,
                        individual_fee = %s,
                        pair_practice_fee = %s,
                        team_competition_fee = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE event_id = %s
                """, (
                    event.name, 
                    event.description, 
                    event.start_date, 
                    event.end_date,
                    event.location, 
                    event.max_participants, 
                    event.registration_start_time, 
                    event.registration_deadline,
                    event.status.value,
                    event.contact_phone,
                    event.organizer,
                    event.co_organizer,
                    getattr(event, 'individual_fee', 0) or 0,
                    getattr(event, 'pair_practice_fee', 0) or 0,
                    getattr(event, 'team_competition_fee', 0) or 0,
                    event_id
                ))
                
                affected_rows = cursor.rowcount
                conn.commit()
                
                if affected_rows > 0:
                    # 返回更新后的赛事
                    return self.get_event_by_id(event_id)
                else:
                    return None
                
        except Error as e:
            logger.error(f"更新赛事失败: {e}")
            raise
