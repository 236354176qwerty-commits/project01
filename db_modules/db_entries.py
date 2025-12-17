import logging

from mysql.connector import Error


logger = logging.getLogger(__name__)


class EntryDbMixin:
    def create_entry(
        self,
        event_id,
        event_item_id,
        entry_type,
        registration_number,
        team_id=None,
        status="registered",
        created_by=None,
        individual_fee=0,
        pair_fee=0,
        team_fee=0,
        other_fee=0,
        total_fee=None,
        payment_status="unpaid",
    ):
        if total_fee is None:
            total_fee = individual_fee + pair_fee + team_fee + other_fee
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO entries (
                        event_id, event_item_id, team_id,
                        entry_type, registration_number,
                        status,
                        individual_fee, pair_fee, team_fee, other_fee, total_fee,
                        payment_status,
                        created_by
                    ) VALUES (%s, %s, %s,
                              %s, %s,
                              %s,
                              %s, %s, %s, %s, %s,
                              %s,
                              %s)
                    """,
                    (
                        event_id,
                        event_item_id,
                        team_id,
                        entry_type,
                        registration_number,
                        status,
                        individual_fee,
                        pair_fee,
                        team_fee,
                        other_fee,
                        total_fee,
                        payment_status,
                        created_by,
                    ),
                )
                entry_id = cursor.lastrowid
                conn.commit()
                return entry_id
        except Error as e:  # noqa: BLE001
            logger.error(f"创建报名条目失败: {e}")
            raise

    def get_entry(self, entry_id):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT * FROM entries WHERE entry_id = %s",
                    (entry_id,),
                )
                return cursor.fetchone()
        except Error as e:  # noqa: BLE001
            logger.error(f"获取报名条目失败: {e}")
            raise

    def get_entries_by_event(self, event_id, event_item_id=None, team_id=None, status=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                sql = "SELECT * FROM entries WHERE event_id = %s"
                params = [event_id]
                if event_item_id is not None:
                    sql += " AND event_item_id = %s"
                    params.append(event_item_id)
                if team_id is not None:
                    sql += " AND team_id = %s"
                    params.append(team_id)
                if status is not None:
                    sql += " AND status = %s"
                    params.append(status)
                sql += " ORDER BY entry_id"
                cursor.execute(sql, tuple(params))
                return cursor.fetchall()
        except Error as e:  # noqa: BLE001
            logger.error(f"获取报名条目列表失败: {e}")
            raise

    def update_entry(self, entry_id, fields):
        if not fields:
            return False
        allowed_fields = {
            "status",
            "checked_in_at",
            "late_checkin_at",
            "late_checkin_by",
            "late_checkin_reason",
            "late_checkin_penalty",
            "individual_fee",
            "pair_fee",
            "team_fee",
            "other_fee",
            "total_fee",
            "payment_status",
            "paid_amount",
            "payment_time",
            "withdrawn_reason",
        }
        set_parts = []
        params = []
        for key, value in fields.items():
            if key in allowed_fields:
                set_parts.append(f"{key} = %s")
                params.append(value)
        if not set_parts:
            return False
        params.append(entry_id)
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = (
                    "UPDATE entries SET "
                    + ", ".join(set_parts)
                    + " WHERE entry_id = %s"
                )
                cursor.execute(sql, tuple(params))
                conn.commit()
                return cursor.rowcount > 0
        except Error as e:  # noqa: BLE001
            logger.error(f"更新报名条目失败: {e}")
            raise

    def add_entry_member(self, entry_id, user_id, role="main", order_in_entry=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO entry_members (
                        entry_id, user_id, role, order_in_entry
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (entry_id, user_id, role, order_in_entry),
                )
                entry_member_id = cursor.lastrowid
                conn.commit()
                return entry_member_id
        except Error as e:  # noqa: BLE001
            logger.error(f"添加报名成员失败: {e}")
            raise

    def get_entry_members(self, entry_id):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT * FROM entry_members WHERE entry_id = %s ORDER BY entry_member_id",
                    (entry_id,),
                )
                return cursor.fetchall()
        except Error as e:  # noqa: BLE001
            logger.error(f"获取报名成员失败: {e}")
            raise

    def create_individual_entry_for_user(
        self,
        event_id,
        item_name,
        registration_number,
        user_id,
        team_id=None,
        created_by=None,
        status="registered",
    ):
        """为单个用户创建个人项目报名 entries + entry_members 记录。

        这是一个组合方法：
        - 通过 EventItemDbMixin.ensure_event_item_by_name 确保存在 (event_id, item_name) 项目；
        - 在 entries 中插入一条 entry；
        - 在 entry_members 中插入一条主成员记录。

        不改变现有 API 的行为，仅作为新结构的补充写入。
        """
        ensure_item = getattr(self, "ensure_event_item_by_name", None)
        if ensure_item is None:
            raise RuntimeError("EventItemDbMixin.ensure_event_item_by_name 未挂载到当前 DatabaseManager")

        event_item_id = self.ensure_event_item_by_name(
            event_id=event_id,
            name=item_name,
            item_type="individual",
        )

        entry_id = self.create_entry(
            event_id=event_id,
            event_item_id=event_item_id,
            entry_type="individual",
            registration_number=registration_number,
            team_id=team_id,
            status=status,
            created_by=created_by,
        )
        self.add_entry_member(entry_id, user_id, role="main", order_in_entry=None)
        return entry_id

    def get_entries_with_members_by_event(
        self,
        event_id,
        event_item_id=None,
        team_id=None,
        status=None,
    ):
        """按赛事获取报名条目及其成员列表（仅内部使用）。

        返回 entries 的字典列表，每个元素在原有字段基础上增加:
        - members: 该 entry 下的 entry_members 字典列表。
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)

                # 先获取符合条件的 entries
                sql = "SELECT * FROM entries WHERE event_id = %s"
                params = [event_id]
                if event_item_id is not None:
                    sql += " AND event_item_id = %s"
                    params.append(event_item_id)
                if team_id is not None:
                    sql += " AND team_id = %s"
                    params.append(team_id)
                if status is not None:
                    sql += " AND status = %s"
                    params.append(status)
                sql += " ORDER BY entry_id"

                cursor.execute(sql, tuple(params))
                entries = cursor.fetchall()
                if not entries:
                    return []

                entry_ids = [e["entry_id"] for e in entries]

                # 一次性拉取所有成员，避免 N+1 查询
                placeholders = ",".join(["%s"] * len(entry_ids))
                cursor.execute(
                    f"""
                    SELECT *
                    FROM entry_members
                    WHERE entry_id IN ({placeholders})
                    ORDER BY entry_id, entry_member_id
                    """,
                    tuple(entry_ids),
                )
                members_rows = cursor.fetchall()

                members_by_entry = {eid: [] for eid in entry_ids}
                for row in members_rows:
                    members_by_entry.setdefault(row["entry_id"], []).append(row)

                for entry in entries:
                    entry["members"] = members_by_entry.get(entry["entry_id"], [])

                return entries
        except Error as e:  # noqa: BLE001
            logger.error(f"获取赛事报名条目及成员失败: {e}")
            raise
