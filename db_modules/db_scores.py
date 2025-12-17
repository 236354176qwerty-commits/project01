import logging

from mysql.connector import Error

from models import Score


logger = logging.getLogger(__name__)


class ScoreDbMixin:
    """评分相关数据库操作 mixin。

    依赖宿主类提供:
    - self.get_connection(): 返回数据库连接的上下文管理器
    """

    # ==================== 评分相关操作 ====================

    def create_or_update_score(self, score):
        """创建或更新评分

        - 首次提交：插入一条新的 scores 记录，并尽量补充 event_id。
        - 重复提交（同一参赛者+裁判+轮次）：更新已有记录，并在 score_modification_logs 中记录修改前后分数。
        """
        try:
            with self.get_connection() as conn:
                # 使用 dictionary=True 便于按列名访问
                cursor = conn.cursor(dictionary=True)

                # 先查询是否已有同一参赛者+裁判+轮次的成绩
                cursor.execute(
                    """
                    SELECT score_id, technique_score, performance_score, deduction,
                           total_score, event_id, entry_id, version
                    FROM scores
                    WHERE participant_id = %s AND judge_id = %s AND round_number = %s
                    FOR UPDATE
                    """,
                    (score.participant_id, score.judge_id, score.round_number),
                )
                existing = cursor.fetchone()

                # 确定 event_id / entry_id / 当前版本号
                event_id = None
                entry_id = None
                current_version = 1

                if existing:
                    event_id = existing.get("event_id")
                    entry_id = existing.get("entry_id")
                    current_version = existing.get("version") or 1

                # 如有需要，从 participants / entries 补充 event_id / entry_id
                if event_id is None or entry_id is None:
                    cursor.execute(
                        """
                        SELECT event_id, registration_number
                        FROM participants
                        WHERE participant_id = %s
                        """,
                        (score.participant_id,),
                    )
                    row = cursor.fetchone()
                    if row:
                        # 兼容 dict / tuple 两种返回形式
                        if event_id is None:
                            event_id = (
                                row.get("event_id")
                                if isinstance(row, dict)
                                else row[0]
                            )

                        if entry_id is None:
                            registration_number = (
                                row.get("registration_number")
                                if isinstance(row, dict)
                                else row[1]
                            )
                            if registration_number:
                                cursor.execute(
                                    """
                                    SELECT entry_id
                                    FROM entries
                                    WHERE registration_number = %s
                                    LIMIT 1
                                    """,
                                    (registration_number,),
                                )
                                entry_row = cursor.fetchone()
                                if entry_row:
                                    entry_id = (
                                        entry_row.get("entry_id")
                                        if isinstance(entry_row, dict)
                                        else entry_row[0]
                                    )

                # 新建成绩
                if not existing:
                    cursor.execute(
                        """
                        INSERT INTO scores (
                            participant_id, judge_id, round_number,
                            technique_score, performance_score, deduction, notes,
                            event_id, entry_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            score.participant_id,
                            score.judge_id,
                            score.round_number,
                            score.technique_score,
                            score.performance_score,
                            score.deduction,
                            score.notes,
                            event_id,
                            entry_id,
                        ),
                    )
                    score.score_id = cursor.lastrowid
                else:
                    # 更新已有成绩并写入修改日志
                    old = existing

                    # 计算新的总分供日志使用（避免依赖 GENERATED 列的即时值）
                    try:
                        score.calculate_total()
                        new_total = score.total_score
                    except Exception:
                        new_total = None

                    # 更新 scores 主表
                    cursor.execute(
                        """
                        UPDATE scores
                        SET technique_score = %s,
                            performance_score = %s,
                            deduction = %s,
                            notes = %s,
                            event_id = %s,
                            entry_id = %s,
                            modified_at = CURRENT_TIMESTAMP,
                            modified_by = %s,
                            modification_reason = %s,
                            version = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE score_id = %s
                        """,
                        (
                            score.technique_score,
                            score.performance_score,
                            score.deduction,
                            score.notes,
                            event_id,
                            entry_id,
                            score.judge_id,
                            "overwrite_by_submit_score",
                            current_version + 1,
                            old["score_id"],
                        ),
                    )

                    # 仅在能拿到 event_id 时写入修改日志，避免违反 NOT NULL 约束
                    if event_id is not None:
                        cursor.execute(
                            """
                            INSERT INTO score_modification_logs (
                                score_id, event_id, entry_id, judge_id, round_no,
                                old_technique_score, new_technique_score,
                                old_performance_score, new_performance_score,
                                old_deduction, new_deduction,
                                old_total_score, new_total_score,
                                modification_type, reason, modified_by
                            ) VALUES (%s, %s, %s, %s, %s,
                                      %s, %s, %s, %s,
                                      %s, %s, %s, %s,
                                      %s, %s, %s)
                            """,
                            (
                                old["score_id"],
                                event_id,
                                entry_id,
                                score.judge_id,
                                score.round_number,
                                float(old["technique_score"])
                                if old.get("technique_score") is not None
                                else None,
                                score.technique_score,
                                float(old["performance_score"])
                                if old.get("performance_score") is not None
                                else None,
                                score.performance_score,
                                float(old["deduction"])
                                if old.get("deduction") is not None
                                else None,
                                score.deduction,
                                float(old["total_score"])
                                if old.get("total_score") is not None
                                else None,
                                new_total,
                                "correction",
                                "overwrite_by_submit_score",
                                score.judge_id,
                            ),
                        )

                    score.score_id = old["score_id"]

                conn.commit()
                return score

        except Error as e:
            logger.error(f"保存评分失败: {e}")
            raise

    def get_scores_by_participant(self, participant_id):
        """获取参赛者的所有评分"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT s.*, u.real_name as judge_name 
                    FROM scores s 
                    JOIN users u ON s.judge_id = u.user_id 
                    WHERE s.participant_id = %s 
                    ORDER BY s.round_number, s.judge_id
                """, (participant_id,))
                
                scores = []
                for row in cursor.fetchall():
                    score = Score(
                        score_id=row['score_id'],
                        participant_id=row['participant_id'],
                        judge_id=row['judge_id'],
                        round_number=row['round_number'],
                        technique_score=float(row['technique_score']),
                        performance_score=float(row['performance_score']),
                        deduction=float(row['deduction']),
                        total_score=float(row['total_score']),
                        notes=row['notes'],
                        scored_at=row['scored_at'],
                        updated_at=row['updated_at']
                    )
                    # 添加裁判姓名
                    score.judge_name = row['judge_name']
                    scores.append(score)
                
                return scores
                
        except Error as e:
            logger.error(f"获取评分失败: {e}")
            raise

    def get_event_results(self, event_id, include_scores=False):
        """获取赛事成绩排名"""
        try:
            # 先通过统一的参赛者读取方法获取参赛者列表（已优先基于 event_participants）
            participants = self.get_participants_by_event(event_id)

            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)

                results = []
                for participant in participants:
                    cursor.execute(
                        """
                        SELECT total_score, judge_id, round_number
                        FROM scores
                        WHERE participant_id = %s
                        ORDER BY round_number, judge_id
                        """,
                        (participant.participant_id,),
                    )

                    scores = cursor.fetchall()
                    score_count = len(scores)

                    result = {
                        'participant_id': participant.participant_id,
                        'registration_number': participant.registration_number,
                        'real_name': getattr(participant, 'real_name', None),
                        'category': participant.category,
                        'weight_class': participant.weight_class,
                        'status': participant.status,
                        'score_count': score_count,
                        'average_score': None,
                        'scores_list': [s['total_score'] for s in scores] if scores else [],
                    }

                    if include_scores:
                        result['detailed_scores'] = scores

                    results.append(result)

                return results

        except Error as e:
            logger.error(f"获取赛事成绩失败: {e}")
            raise
