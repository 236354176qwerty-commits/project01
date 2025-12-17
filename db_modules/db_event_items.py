import logging

from mysql.connector import Error


logger = logging.getLogger(__name__)


class EventItemDbMixin:
    def create_event_item(
        self,
        event_id,
        name,
        item_type,
        code=None,
        description=None,
        gender_limit=None,
        min_age=None,
        max_age=None,
        weight_class=None,
        min_members=None,
        max_members=None,
        max_entries=None,
        equipment_required=None,
        rounds=1,
        scoring_mode="sum",
        sort_order=0,
        is_active=True,
    ):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO event_items (
                        event_id, name, code, description, type,
                        gender_limit, min_age, max_age, weight_class,
                        min_members, max_members, max_entries,
                        equipment_required, rounds, scoring_mode,
                        sort_order, is_active
                    ) VALUES (%s, %s, %s, %s, %s,
                              %s, %s, %s, %s,
                              %s, %s, %s,
                              %s, %s, %s,
                              %s, %s)
                    """,
                    (
                        event_id,
                        name,
                        code,
                        description,
                        item_type,
                        gender_limit,
                        min_age,
                        max_age,
                        weight_class,
                        min_members,
                        max_members,
                        max_entries,
                        equipment_required,
                        rounds,
                        scoring_mode,
                        sort_order,
                        is_active,
                    ),
                )
                event_item_id = cursor.lastrowid
                conn.commit()
                return event_item_id
        except Error as e:  # noqa: BLE001
            logger.error(f"创建赛事项目失败: {e}")
            raise

    def get_event_item(self, event_item_id):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT * FROM event_items WHERE event_item_id = %s",
                    (event_item_id,),
                )
                return cursor.fetchone()
        except Error as e:  # noqa: BLE001
            logger.error(f"获取赛事项目失败: {e}")
            raise

    def get_event_items_by_event(self, event_id, only_active=True):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                sql = "SELECT * FROM event_items WHERE event_id = %s"
                params = [event_id]
                if only_active:
                    sql += " AND is_active = TRUE"
                sql += " ORDER BY sort_order, event_item_id"
                cursor.execute(sql, tuple(params))
                return cursor.fetchall()
        except Error as e:  # noqa: BLE001
            logger.error(f"获取赛事项目列表失败: {e}")
            raise

    def get_event_item_by_name(self, event_id, name):
        """按 (event_id, name) 获取单个赛事项目"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    """
                    SELECT * FROM event_items
                    WHERE event_id = %s AND name = %s
                    LIMIT 1
                    """,
                    (event_id, name),
                )
                return cursor.fetchone()
        except Error as e:  # noqa: BLE001
            logger.error(f"按名称获取赛事项目失败: {e}")
            raise

    def ensure_event_item_by_name(self, event_id, name, item_type="individual"):
        """确保给定赛事下存在指定名称的项目，返回 event_item_id。

        - 如果已存在则直接返回已有记录的 event_item_id；
        - 如果不存在则按给定类型创建一个基础项目记录。
        """
        row = self.get_event_item_by_name(event_id, name)
        if row:
            return row["event_item_id"]
        return self.create_event_item(
            event_id=event_id,
            name=name,
            item_type=item_type,
        )

    def update_event_item(self, event_item_id, fields):
        if not fields:
            return False
        allowed_fields = {
            "name",
            "code",
            "description",
            "type",
            "gender_limit",
            "min_age",
            "max_age",
            "weight_class",
            "min_members",
            "max_members",
            "max_entries",
            "equipment_required",
            "rounds",
            "scoring_mode",
            "sort_order",
            "is_active",
        }
        set_parts = []
        params = []
        for key, value in fields.items():
            if key in allowed_fields:
                set_parts.append(f"{key} = %s")
                params.append(value)
        if not set_parts:
            return False
        params.append(event_item_id)
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = (
                    "UPDATE event_items SET "
                    + ", ".join(set_parts)
                    + " WHERE event_item_id = %s"
                )
                cursor.execute(sql, tuple(params))
                conn.commit()
                return cursor.rowcount > 0
        except Error as e:  # noqa: BLE001
            logger.error(f"更新赛事项目失败: {e}")
            raise
