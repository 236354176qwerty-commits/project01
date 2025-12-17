import logging
from datetime import datetime as _dt

from mysql.connector import Error

from models import Participant


logger = logging.getLogger(__name__)


class ParticipantDbMixin:
    """参赛者相关数据库操作 mixin。

    依赖宿主类提供:
    - self.get_connection(): 返回数据库连接的上下文管理器
    """

    def _upsert_event_participant(
        self,
        conn,
        event_id,
        user_id,
        team_id=None,
        role="athlete",
        event_member_no=None,
        status="registered",
        notes=None,
        registered_at=None,
    ):
        """在 event_participants 中 upsert 一条记录。

        - (event_id, user_id, role) 唯一。
        - 不存在则插入；已存在仅在原来的 event_member_no 为空且本次有编号时补齐。
        - 任意异常只记录 warning，不抛出。
        """
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT event_participant_id, event_member_no
                FROM event_participants
                WHERE event_id = %s AND user_id = %s AND role = %s
                FOR UPDATE
                """,
                (event_id, user_id, role),
            )
            row = cursor.fetchone()

            if not row:
                if registered_at is None:
                    cursor.execute(
                        """
                        INSERT INTO event_participants (
                            event_id, user_id, team_id, role,
                            event_member_no, status, notes, registered_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (event_id, user_id, team_id, role, event_member_no, status, notes),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO event_participants (
                            event_id, user_id, team_id, role,
                            event_member_no, status, notes, registered_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (event_id, user_id, team_id, role, event_member_no, status, notes, registered_at),
                    )
            else:
                if row.get("event_member_no") is None and event_member_no is not None:
                    cursor.execute(
                        "UPDATE event_participants SET event_member_no = %s WHERE event_participant_id = %s",
                        (event_member_no, row["event_participant_id"]),
                    )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"同步 event_participants 失败（不影响主流程）: {e}")

    def ensure_participant_with_conn(
        self,
        conn,
        event_id,
        user_id,
        registration_number,
        category,
        participant_status="registered",
        event_participant_status=None,
        gender=None,
        age_group=None,
        notes=None,
        team_id=None,
        registered_at=None,
        update_gender_age_group=True,
        event_member_no=None,
    ):
        """在给定连接上确保 participants / event_participants 记录存在，返回 participant_id。

        - 仅使用传入的 conn，不负责提交事务。
        - participants 不存在时插入基础记录；存在时可按需补全 gender/age_group。
        - 始终尝试同步 event_participants（状态可与 participants 不同）。
        """
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT participant_id, gender, age_group
            FROM participants
            WHERE event_id = %s AND user_id = %s
            FOR UPDATE
            """,
            (event_id, user_id),
        )
        row = cursor.fetchone()

        if not row:
            if registered_at is None:
                cursor.execute(
                    """
                    INSERT INTO participants (
                        event_id, user_id, registration_number,
                        category, status, gender, age_group, notes, registered_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        event_id,
                        user_id,
                        registration_number,
                        category,
                        participant_status,
                        gender,
                        age_group,
                        notes,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO participants (
                        event_id, user_id, registration_number,
                        category, status, gender, age_group, notes, registered_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event_id,
                        user_id,
                        registration_number,
                        category,
                        participant_status,
                        gender,
                        age_group,
                        notes,
                        registered_at,
                    ),
                )
            participant_id = cursor.lastrowid
        else:
            participant_id = row["participant_id"]
            if update_gender_age_group and (gender is not None or age_group is not None):
                cursor.execute(
                    """
                    UPDATE participants
                    SET gender = COALESCE(%s, gender),
                        age_group = COALESCE(%s, age_group)
                    WHERE participant_id = %s
                    """,
                    (gender, age_group, participant_id),
                )

        ep_status = event_participant_status or participant_status
        self._upsert_event_participant(
            conn,
            event_id,
            user_id,
            team_id=team_id,
            role="athlete",
            event_member_no=event_member_no,
            status=ep_status,
            notes=notes,
            registered_at=registered_at,
        )
        return participant_id

    def create_participant(self, participant):
        """创建参赛者，并同步 event_participants 结构。

        行为与原 DatabaseManager.create_participant 等价。
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "SELECT MAX(event_member_no) FROM participants WHERE event_id = %s",
                        (participant.event_id,),
                    )
                    row = cursor.fetchone()
                    next_no = (row[0] or 0) + 1
                except Error as e:  # noqa: BLE001
                    logger.warning(f"计算event_member_no失败，将使用NULL: {e}")
                    next_no = None
                participant.event_member_no = next_no

                # 根据身份证号计算性别和年龄组（如果可能），写入持久化字段
                gender_value = None
                age_group_value = None
                id_card = participant.registration_number or ""
                if len(id_card) == 18:
                    try:
                        gender_digit = int(id_card[-2])
                        gender_value = "男" if gender_digit % 2 == 1 else "女"

                        birth_year = int(id_card[6:10])
                        birth_month = int(id_card[10:12])
                        birth_day = int(id_card[12:14])

                        today = _dt.now()
                        age = today.year - birth_year
                        if (today.month, today.day) < (birth_month, birth_day):
                            age -= 1

                        if age is not None:
                            if age < 12:
                                age_group_value = "儿童组"
                            elif 12 <= age <= 17:
                                age_group_value = "少年组"
                            elif 18 <= age <= 39:
                                age_group_value = "青年组"
                            elif 40 <= age <= 59:
                                age_group_value = "中年组"
                            elif age >= 60:
                                age_group_value = "老年组"
                    except Exception:  # noqa: BLE001
                        gender_value = None
                        age_group_value = None

                cursor.execute(
                    """
                    INSERT INTO participants (
                        event_id, user_id, registration_number,
                        event_member_no, category, weight_class, gender, age_group, status, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        participant.event_id,
                        participant.user_id,
                        participant.registration_number,
                        participant.event_member_no,
                        participant.category,
                        participant.weight_class,
                        gender_value,
                        age_group_value,
                        participant.status.value,
                        participant.notes,
                    ),
                )
                participant.participant_id = cursor.lastrowid

                # 双写到新结构表 event_participants（不切读流量，仅补结构）
                self._upsert_event_participant(
                    conn,
                    participant.event_id,
                    participant.user_id,
                    team_id=None,
                    role="athlete",
                    event_member_no=participant.event_member_no,
                    status="registered",
                    notes=participant.notes,
                    registered_at=None,
                )

                conn.commit()
                return participant

        except Error as e:  # noqa: BLE001
            logger.error(f"创建参赛者失败: {e}")
            raise

    def update_participant_fields(self, participant_id, fields):
        """按字段更新参赛者基础信息"""
        if not fields:
            return False

        allowed_fields = {"category", "weight_class", "status", "notes"}
        set_parts = []
        params = []
        for key, value in fields.items():
            if key in allowed_fields:
                set_parts.append(f"{key} = %s")
                params.append(value)

        if not set_parts:
            return False

        params.append(participant_id)

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = (
                    "UPDATE participants SET "
                    + ", ".join(set_parts)
                    + " WHERE participant_id = %s"
                )
                cursor.execute(sql, tuple(params))
                conn.commit()
                return cursor.rowcount > 0
        except Error as e:  # noqa: BLE001
            logger.error(f"更新参赛者信息失败: {e}")
            raise

    def set_participant_review_status_with_conn(self, conn, participant_id, review_status):
        """在给定连接上更新参赛者审核状态，不提交事务。"""
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE participants
            SET review_status = %s,
                reviewed_at = NOW()
            WHERE participant_id = %s
            """,
            (review_status, participant_id),
        )

    def get_participants_by_event(self, event_id):
        """获取赛事的所有参赛者。

        行为与原 DatabaseManager.get_participants_by_event 等价。
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    """
                    SELECT
                        p.participant_id,
                        ep.event_id AS event_id,
                        ep.user_id AS user_id,
                        p.registration_number,
                        COALESCE(p.event_member_no, ep.event_member_no) AS event_member_no,
                        p.category,
                        p.weight_class,
                        COALESCE(p.status, ep.status) AS status,
                        COALESCE(p.notes, ep.notes) AS notes,
                        COALESCE(p.registered_at, ep.registered_at) AS registered_at,
                        COALESCE(p.checked_in_at, ep.checked_in_at) AS checked_in_at,
                        u.real_name,
                        u.username
                    FROM event_participants ep
                    JOIN users u ON ep.user_id = u.user_id
                    LEFT JOIN participants p
                        ON p.event_id = ep.event_id
                       AND p.user_id = ep.user_id
                    WHERE ep.event_id = %s
                      AND ep.role = 'athlete'
                    ORDER BY p.registration_number, ep.event_participant_id
                    """,
                    (event_id,),
                )

                rows = cursor.fetchall()

                # 如果新结构中没有记录，则退回旧结构 participants
                if not rows:
                    cursor.execute(
                        """
                        SELECT p.*, u.real_name, u.username
                        FROM participants p
                        JOIN users u ON p.user_id = u.user_id
                        WHERE p.event_id = %s
                        ORDER BY p.registration_number
                        """,
                        (event_id,),
                    )
                    rows = cursor.fetchall()

                participants = []
                for row in rows:
                    participant = Participant(
                        participant_id=row["participant_id"],
                        event_id=row["event_id"],
                        user_id=row["user_id"],
                        registration_number=row["registration_number"],
                        event_member_no=row.get("event_member_no"),
                        category=row["category"],
                        weight_class=row["weight_class"],
                        status=row["status"],
                        notes=row["notes"],
                        registered_at=row["registered_at"],
                        checked_in_at=row["checked_in_at"],
                    )
                    participant.real_name = row["real_name"]
                    participant.username = row["username"]
                    participants.append(participant)

                return participants

        except Error as e:  # noqa: BLE001
            logger.error(f"获取参赛者列表失败: {e}")
            raise
