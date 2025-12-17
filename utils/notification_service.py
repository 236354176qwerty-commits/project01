#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知服务工具类
用于封装系统通知发送逻辑
"""

from database import DatabaseManager
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务类"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def send_registration_success_notification(self, user_id, event_id, participant_info=None):
        """
        发送报名成功通知
        
        Args:
            user_id: 用户ID
            event_id: 赛事ID
            participant_info: 参赛者信息字典，包含额外信息
        
        Returns:
            bool: 发送成功返回True，否则返回False
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                # 获取赛事信息
                cursor.execute('''
                    SELECT event_id, name, location, start_date, end_date, 
                           registration_deadline, description
                    FROM events 
                    WHERE event_id = %s
                ''', (event_id,))
                event = cursor.fetchone()
                
                if not event:
                    logger.error(f"赛事不存在: event_id={event_id}")
                    return False
                
                # 获取用户信息
                cursor.execute('''
                    SELECT user_id, username, real_name, phone, email
                    FROM users 
                    WHERE user_id = %s
                ''', (user_id,))
                user = cursor.fetchone()
                
                if not user:
                    logger.error(f"用户不存在: user_id={user_id}")
                    return False
                
                # 构建通知标题
                title = f"【{event['name']}】报名成功通知"
                
                # 构建通知内容
                content_parts = [
                    f"恭喜！您已成功报名参加【{event['name']}】",
                    "",
                    "📋 参赛信息",
                ]
                
                # 添加队伍和领队信息（显示"无"如果为空）
                team_name = "无"
                leader_name = "无"
                category = "无"
                
                if participant_info:
                    if participant_info.get('team_name'):
                        team_name = participant_info['team_name']
                    if participant_info.get('leader_name'):
                        leader_name = participant_info['leader_name']
                    if participant_info.get('category'):
                        category = participant_info['category']
                
                content_parts.extend([
                    f"🔹 队伍名称：{team_name}",
                    f"👥 领队名称：{leader_name}",
                    f"📍 比赛地点：{event['location'] or '待定'}",
                    f"📅 比赛时间：{event['start_date'].strftime('%Y年%m月%d日')} 至 {event['end_date'].strftime('%Y年%m月%d日')}",
                    f"🏆 参赛项目：{category}",
                ])
                
                content_parts.extend([
                    "",
                    "⏰ 重要提醒",
                    "• 请按时到达比赛现场签到，具体签到时间及地点将在赛前另行通知；",
                    "• 入场需携带有效身份证件（如身份证、护照等），以备核验；",
                    "• 赛事细则、流程等信息请以组委会后续通知或官网最新公告为准。",
                    "",
                    "📞 联系方式",
                    f"如有疑问，请联系【{event['name']}】组委会：",
                ])
                
                # 添加联系方式（如果有）
                contact_info = []
                if participant_info and participant_info.get('contact_phone'):
                    contact_info.append(f"☎️ 联系电话：{participant_info['contact_phone']}")
                if participant_info and participant_info.get('contact_email'):
                    contact_info.append(f"✉️ 联系邮箱：{participant_info['contact_email']}")
                
                if contact_info:
                    content_parts.extend(contact_info)
                else:
                    content_parts.append("（联系方式请查看赛事详情或官网公告）")
                
                content_parts.extend([
                    "",
                    "祝您比赛顺利，取得优异成绩！🏆"
                ])
                
                content = '\n'.join(content_parts)
                
                # 构建附加信息（JSON格式存储）
                additional_info = {
                    'event_id': event_id,
                    'event_name': event['name'],
                    'event_location': event['location'],
                    'start_date': event['start_date'].isoformat() if event['start_date'] else None,
                    'end_date': event['end_date'].isoformat() if event['end_date'] else None,
                    'notification_type': 'registration_success',
                }
                
                if participant_info:
                    additional_info.update({
                        'team_name': participant_info.get('team_name'),
                        'leader_name': participant_info.get('leader_name'),
                        'category': participant_info.get('category'),
                        'registration_number': participant_info.get('registration_number'),
                        'participant_id': participant_info.get('participant_id'),
                        'contact_phone': participant_info.get('contact_phone'),
                        'contact_email': participant_info.get('contact_email'),
                    })
                
                # 使用系统管理员ID（假设为1）作为发送者
                system_sender_id = 1
                
                # 插入通知记录
                cursor.execute('''
                    INSERT INTO notifications 
                    (sender_id, title, content, recipient_type, priority, additional_info, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ''', (system_sender_id, title, content, 'system', 'important', json.dumps(additional_info)))
                
                notification_id = cursor.lastrowid
                
                # 创建用户通知记录
                cursor.execute('''
                    INSERT INTO user_notifications 
                    (notification_id, user_id, is_read, created_at)
                    VALUES (%s, %s, FALSE, NOW())
                ''', (notification_id, user_id))
                
                conn.commit()
                
                logger.info(f"报名成功通知已发送 - 用户ID: {user_id}, 赛事ID: {event_id}, 通知ID: {notification_id}")
                return True
                
        except Exception as e:
            logger.error(f"发送报名成功通知失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_approval_notification(self, user_id, event_id, approval_info=None):
        """
        发送审核通过通知
        
        Args:
            user_id: 用户ID
            event_id: 赛事ID
            approval_info: 审核信息字典
        
        Returns:
            bool: 发送成功返回True，否则返回False
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                # 获取赛事信息
                cursor.execute('''
                    SELECT event_id, name, location, start_date, end_date
                    FROM events 
                    WHERE event_id = %s
                ''', (event_id,))
                event = cursor.fetchone()
                
                if not event:
                    logger.error(f"赛事不存在: event_id={event_id}")
                    return False
                
                # 构建通知
                title = "资格审核通过通知"
                content_parts = [
                    f"您好！您的【{event['name']}】参赛资格审核已通过。",
                    f"\n📍 比赛地点：{event['location'] or '待定'}",
                    f"📅 比赛时间：{event['start_date'].strftime('%Y年%m月%d日')} 至 {event['end_date'].strftime('%Y年%m月%d日')}",
                    "\n接下来您需要：",
                    "✅ 按时参加赛前签到",
                    "✅ 准备好相关参赛资料",
                    "✅ 关注后续通知信息",
                    "\n祝您取得好成绩！"
                ]
                
                content = '\n'.join(content_parts)
                
                # 附加信息
                additional_info = {
                    'event_id': event_id,
                    'event_name': event['name'],
                    'notification_type': 'approval_success',
                }
                
                if approval_info:
                    additional_info.update(approval_info)
                
                # 系统管理员发送
                system_sender_id = 1
                
                # 插入通知
                cursor.execute('''
                    INSERT INTO notifications 
                    (sender_id, title, content, recipient_type, priority, additional_info, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ''', (system_sender_id, title, content, 'system', 'important', json.dumps(additional_info)))
                
                notification_id = cursor.lastrowid
                
                # 创建用户通知
                cursor.execute('''
                    INSERT INTO user_notifications 
                    (notification_id, user_id, is_read, created_at)
                    VALUES (%s, %s, FALSE, NOW())
                ''', (notification_id, user_id))
                
                conn.commit()
                
                logger.info(f"审核通过通知已发送 - 用户ID: {user_id}, 赛事ID: {event_id}")
                return True
                
        except Exception as e:
            logger.error(f"发送审核通过通知失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_final_confirmation_notification(self, user_id, event_id, participant_info=None):
        """
        发送报名截止/审核通过后的正式参赛确认通知
        当用户的报名申请审核通过或赛事报名截止时，发送包含完整参赛信息的正式通知
        
        Args:
            user_id: 用户ID
            event_id: 赛事ID
            participant_info: 参赛者详细信息字典，包含：
                - team_name: 队伍名称
                - leader_name: 领队名称
                - category: 参赛项目
                - registration_number: 参赛编号
                - contact_phone: 组委会联系电话
                - contact_email: 组委会联系邮箱
        
        Returns:
            bool: 发送成功返回True，否则返回False
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                # 获取赛事信息
                cursor.execute('''
                    SELECT event_id, name, location, start_date, end_date, 
                           registration_deadline, description
                    FROM events 
                    WHERE event_id = %s
                ''', (event_id,))
                event = cursor.fetchone()
                
                if not event:
                    logger.error(f"赛事不存在: event_id={event_id}")
                    return False
                
                # 获取用户信息
                cursor.execute('''
                    SELECT user_id, username, real_name, phone, email
                    FROM users 
                    WHERE user_id = %s
                ''', (user_id,))
                user = cursor.fetchone()
                
                if not user:
                    logger.error(f"用户不存在: user_id={user_id}")
                    return False
                
                # 构建通知标题
                title = f"【{event['name']}】参赛资格确认通知"
                
                # 构建通知内容
                content_parts = [
                    f"尊敬的参赛选手，您好！",
                    "",
                    f"恭喜您已获得【{event['name']}】的正式参赛资格，报名流程已全部完成。",
                    "",
                    "📋 参赛信息确认",
                ]
                
                # 添加队伍和领队信息（显示"无"如果为空）
                team_name = "无"
                leader_name = "无"
                category = "无"
                
                if participant_info:
                    if participant_info.get('team_name'):
                        team_name = participant_info['team_name']
                    if participant_info.get('leader_name'):
                        leader_name = participant_info['leader_name']
                    if participant_info.get('category'):
                        category = participant_info['category']
                
                content_parts.extend([
                    f"🔹 队伍名称：{team_name}",
                    f"👥 领队名称：{leader_name}",
                    f"📍 比赛地点：{event['location'] or '待定'}",
                    f"📅 比赛时间：{event['start_date'].strftime('%Y年%m月%d日')} 至 {event['end_date'].strftime('%Y年%m月%d日')}",
                    f"🏆 参赛项目：{category}",
                ])
                
                content_parts.extend([
                    "",
                    "⏰ 赛前重要提醒",
                    "• 请务必按时到达比赛现场进行签到，具体签到时间和地点将在赛前通过短信或邮件另行通知；",
                    "• 参赛时请务必携带有效身份证件（身份证、护照等）原件，用于现场核验身份；",
                    "• 请提前准备好参赛所需的装备和资料，确保符合赛事规则要求；",
                    "• 建议提前熟悉比赛场地和交通路线，预留充足时间避免迟到；",
                    "• 请密切关注赛事组委会发布的最新通知和公告，如有赛程调整将及时通知；",
                    "• 比赛期间请遵守赛事规则和现场秩序，服从裁判和工作人员的安排。",
                    "",
                    "📞 组委会联系方式",
                    f"如有任何疑问或特殊情况，请及时联系【{event['name']}】组委会：",
                ])
                
                # 添加联系方式
                contact_info = []
                if participant_info and participant_info.get('contact_phone'):
                    contact_info.append(f"☎️ 联系电话：{participant_info['contact_phone']}")
                if participant_info and participant_info.get('contact_email'):
                    contact_info.append(f"✉️ 联系邮箱：{participant_info['contact_email']}")
                
                if contact_info:
                    content_parts.extend(contact_info)
                else:
                    content_parts.append("（联系方式请查看赛事详情或官网公告）")
                
                content_parts.extend([
                    "",
                    "━━━━━━━━━━━━━━━━━━",
                    "报名阶段已正式结束，期待您在赛场上的精彩表现！",
                    "预祝您比赛顺利，取得优异成绩！🏆"
                ])
                
                content = '\n'.join(content_parts)
                
                # 构建附加信息（JSON格式存储）
                additional_info = {
                    'event_id': event_id,
                    'event_name': event['name'],
                    'event_location': event['location'],
                    'start_date': event['start_date'].isoformat() if event['start_date'] else None,
                    'end_date': event['end_date'].isoformat() if event['end_date'] else None,
                    'notification_type': 'final_confirmation',
                }
                
                if participant_info:
                    additional_info.update({
                        'team_name': participant_info.get('team_name'),
                        'leader_name': participant_info.get('leader_name'),
                        'category': participant_info.get('category'),
                        'registration_number': participant_info.get('registration_number'),
                        'participant_id': participant_info.get('participant_id'),
                        'contact_phone': participant_info.get('contact_phone'),
                        'contact_email': participant_info.get('contact_email'),
                    })
                
                # 使用系统管理员ID作为发送者
                system_sender_id = 1
                
                # 插入通知记录
                cursor.execute('''
                    INSERT INTO notifications 
                    (sender_id, title, content, recipient_type, priority, additional_info, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ''', (system_sender_id, title, content, 'system', 'urgent', json.dumps(additional_info)))
                
                notification_id = cursor.lastrowid
                
                # 创建用户通知记录
                cursor.execute('''
                    INSERT INTO user_notifications 
                    (notification_id, user_id, is_read, created_at)
                    VALUES (%s, %s, FALSE, NOW())
                ''', (notification_id, user_id))
                
                conn.commit()
                
                logger.info(f"参赛确认通知已发送 - 用户ID: {user_id}, 赛事ID: {event_id}, 通知ID: {notification_id}")
                return True
                
        except Exception as e:
            logger.error(f"发送参赛确认通知失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_batch_final_confirmation_notifications(self, event_id):
        """
        批量发送参赛确认通知（用于报名截止时）
        给指定赛事中所有审核通过的参赛者发送正式参赛确认通知
        
        Args:
            event_id: 赛事ID
        
        Returns:
            dict: 包含成功和失败数量的字典 {'success_count': int, 'failed_count': int, 'total': int}
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                # 获取该赛事所有审核通过的参赛者信息
                cursor.execute('''
                    SELECT DISTINCT
                        p.user_id,
                        p.participant_id,
                        p.registration_number,
                        t.team_name,
                        t.leader_name,
                        c.category_name as category
                    FROM participants p
                    LEFT JOIN teams t ON p.team_id = t.team_id
                    LEFT JOIN categories c ON p.category_id = c.category_id
                    WHERE p.event_id = %s 
                    AND p.review_status = 'approved'
                ''', (event_id,))
                
                participants = cursor.fetchall()
                
                if not participants:
                    logger.info(f"赛事 {event_id} 没有已审核通过的参赛者")
                    return {'success_count': 0, 'failed_count': 0, 'total': 0}
                
                # 获取赛事的联系方式（如果有）
                cursor.execute('''
                    SELECT name, description
                    FROM events 
                    WHERE event_id = %s
                ''', (event_id,))
                event = cursor.fetchone()
                
                # 尝试从赛事描述中提取联系方式（这里可以根据实际情况调整）
                contact_phone = None
                contact_email = None
                
                success_count = 0
                failed_count = 0
                
                # 批量发送通知
                for participant in participants:
                    participant_info = {
                        'team_name': participant.get('team_name'),
                        'leader_name': participant.get('leader_name'),
                        'category': participant.get('category'),
                        'registration_number': participant.get('registration_number'),
                        'participant_id': participant.get('participant_id'),
                        'contact_phone': contact_phone,
                        'contact_email': contact_email,
                    }
                    
                    # 发送通知
                    if self.send_final_confirmation_notification(
                        participant['user_id'], 
                        event_id, 
                        participant_info
                    ):
                        success_count += 1
                    else:
                        failed_count += 1
                
                total = len(participants)
                logger.info(f"批量发送参赛确认通知完成 - 赛事ID: {event_id}, 总数: {total}, 成功: {success_count}, 失败: {failed_count}")
                
                return {
                    'success_count': success_count,
                    'failed_count': failed_count,
                    'total': total
                }
                
        except Exception as e:
            logger.error(f"批量发送参赛确认通知失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'success_count': 0, 'failed_count': 0, 'total': 0, 'error': str(e)}
    
    def get_notification_detail(self, notification_id, user_id):
        """
        获取通知详情（包含附加信息）
        
        Args:
            notification_id: 通知ID
            user_id: 用户ID
        
        Returns:
            dict: 通知详情字典，包含附加信息
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                cursor.execute('''
                    SELECT n.*, un.is_read, un.created_at as received_at
                    FROM user_notifications un
                    JOIN notifications n ON un.notification_id = n.id
                    WHERE n.id = %s AND un.user_id = %s
                ''', (notification_id, user_id))
                
                notification = cursor.fetchone()
                
                if notification and notification.get('additional_info'):
                    try:
                        notification['additional_info'] = json.loads(notification['additional_info'])
                    except:
                        notification['additional_info'] = {}
                
                return notification
                
        except Exception as e:
            logger.error(f"获取通知详情失败: {str(e)}")
            return None
    
    def get_unread_count(self, user_id):
        """
        获取用户未读通知数量
        
        Args:
            user_id: 用户ID
        
        Returns:
            int: 未读通知数量
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM user_notifications
                    WHERE user_id = %s AND is_read = FALSE
                ''', (user_id,))
                
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            logger.error(f"获取未读通知数量失败: {str(e)}")
            return 0


# 创建全局通知服务实例
notification_service = NotificationService()
