from datetime import datetime
import time

from flask import request, jsonify, session

from utils.decorators import log_action, handle_db_errors, cache_result

from . import events_bp, db_manager, logger


@events_bp.route('/', methods=['GET'])
@log_action('获取赛事列表')
@handle_db_errors
@cache_result(timeout=15)
def get_events():
    """获取赛事列表（支持高级筛选与分页）
    可选查询参数：
    - status: 赛事状态 draft/published/ongoing/completed/cancelled
    - keyword: 关键字（匹配名称）
    - location: 举办地点（模糊匹配）
    - created_by: 创建者用户ID（仅管理员可用）
    - date_from: 开始时间起（ISO格式）
    - date_to: 开始时间止（ISO格式）
    - min_participants: 最小参赛人数
    - max_participants: 最大参赛人数
    - page: 第几页，默认1
    - page_size: 每页数量，默认10
    - order_by: 排序字段，默认start_date
    - order_dir: 排序方向，ASC/DESC，默认DESC
    - include_stats: 是否包含统计信息，默认false
    """
    try:
        t_start = time.perf_counter()
        # 获取当前用户信息
        current_user_role = session.get('user_role')
        current_user_id = session.get('user_id')
        
        # 解析和验证筛选条件
        status = request.args.get('status', '').strip()
        status_value = None
        if status:
            # 验证状态值
            valid_statuses = ['draft', 'published', 'ongoing', 'completed', 'cancelled']
            if status not in valid_statuses:
                return jsonify({
                    'success': False, 
                    'message': f'无效的赛事状态: {status}，有效值为: {", ".join(valid_statuses)}'
                }), 400
            status_value = status

        # 支持多种搜索参数名称（兼容前端）
        keyword = request.args.get('keyword', '').strip() or request.args.get('search', '').strip()
        location = request.args.get('location', '').strip()
        
        # 创建者筛选（仅管理员可用）
        created_by = request.args.get('created_by', '').strip()
        created_by_id = None
        if created_by:
            if current_user_role not in ['super_admin', 'admin']:
                return jsonify({
                    'success': False, 
                    'message': '只有管理员可以按创建者筛选赛事'
                }), 403
            try:
                created_by_id = int(created_by)
            except ValueError:
                return jsonify({
                    'success': False, 
                    'message': '创建者ID必须是数字'
                }), 400

        # 解析日期范围
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        date_from_dt = None
        date_to_dt = None
        
        try:
            if date_from:
                date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            if date_to:
                date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                
            # 验证日期范围逻辑
            if date_from_dt and date_to_dt and date_from_dt > date_to_dt:
                return jsonify({
                    'success': False, 
                    'message': '开始日期不能晚于结束日期'
                }), 400
                
        except (ValueError, TypeError):
            return jsonify({
                'success': False, 
                'message': '日期格式无效，请使用ISO格式，如 2025-04-10T09:00:00'
            }), 400

        # 参赛人数范围筛选
        min_participants = request.args.get('min_participants', '').strip()
        max_participants = request.args.get('max_participants', '').strip()
        min_participants_int = None
        max_participants_int = None
        
        try:
            if min_participants:
                min_participants_int = int(min_participants)
                if min_participants_int < 0:
                    raise ValueError("最小参赛人数不能为负数")
            if max_participants:
                max_participants_int = int(max_participants)
                if max_participants_int < 0:
                    raise ValueError("最大参赛人数不能为负数")
                    
            if (min_participants_int is not None and max_participants_int is not None and 
                min_participants_int > max_participants_int):
                return jsonify({
                    'success': False, 
                    'message': '最小参赛人数不能大于最大参赛人数'
                }), 400
                
        except ValueError as e:
            return jsonify({
                'success': False, 
                'message': f'参赛人数参数无效: {str(e)}'
            }), 400

        # 分页与排序参数验证
        try:
            page = int(request.args.get('page', 1) or 1)
            page_size = int(request.args.get('page_size', 10) or 10)
        except ValueError:
            return jsonify({
                'success': False, 
                'message': '分页参数必须是数字'
            }), 400
            
        page = max(page, 1)
        page_size = max(min(page_size, 100), 1)  # 限制每页最多100条
        offset = (page - 1) * page_size
        
        # 排序参数验证
        order_by = request.args.get('order_by', 'start_date').strip()
        order_dir = request.args.get('order_dir', 'DESC').strip().upper()
        
        allowed_order_fields = ['start_date', 'end_date', 'created_at', 'updated_at', 'name', 'max_participants']
        if order_by not in allowed_order_fields:
            return jsonify({
                'success': False, 
                'message': f'无效的排序字段: {order_by}，有效值为: {", ".join(allowed_order_fields)}'
            }), 400
            
        if order_dir not in ['ASC', 'DESC']:
            return jsonify({
                'success': False, 
                'message': '排序方向必须是 ASC 或 DESC'
            }), 400

        # 是否包含统计信息
        include_stats = request.args.get('include_stats', 'false').lower() == 'true'

        t_after_params = time.perf_counter()

        # 查询总数
        total = db_manager.count_events(
            status=status_value, 
            keyword=keyword, 
            date_from=date_from_dt, 
            date_to=date_to_dt, 
            location=location,
            created_by=created_by_id,
            min_participants=min_participants_int,
            max_participants=max_participants_int
        )

        t_after_count = time.perf_counter()

        # 查询列表
        events = db_manager.get_all_events(
            status=status_value, 
            keyword=keyword, 
            date_from=date_from_dt, 
            date_to=date_to_dt,
            location=location, 
            created_by=created_by_id,
            min_participants=min_participants_int,
            max_participants=max_participants_int,
            order_by=order_by, 
            order_dir=order_dir, 
            limit=page_size, 
            offset=offset
        )

        t_after_list = time.perf_counter()

        # 批量获取参赛人数，避免 N+1 查询
        event_ids = [event.event_id for event in events]
        participants_counts = db_manager.count_participants_by_events(event_ids) if event_ids else {}

        t_after_participants = time.perf_counter()

        # 转换为字典格式并添加额外信息
        events_data = []
        now = datetime.now() if include_stats else None
        for event in events:
            event_dict = event.to_dict()
            participants_count = participants_counts.get(event.event_id, 0)
            
            # 如果需要统计信息，添加参赛人数等
            if include_stats:
                try:
                    event_dict['participants_count'] = participants_count
                    
                    # 计算报名进度百分比
                    if event.max_participants and event.max_participants > 0:
                        progress = (participants_count / event.max_participants) * 100
                        event_dict['registration_progress'] = min(progress, 100)
                        event_dict['is_full'] = participants_count >= event.max_participants
                    else:
                        event_dict['registration_progress'] = 0
                        event_dict['is_full'] = False
                        
                    # 添加时间相关的便利字段
                    if event.start_date and now is not None:
                        days_until_start = (event.start_date - now).days
                        event_dict['days_until_start'] = days_until_start
                        event_dict['is_upcoming'] = days_until_start > 0 and days_until_start <= 30
                    
                except Exception as e:
                    logger.warning(f"获取赛事 {event.event_id} 统计信息失败: {e}")
                    event_dict['participants_count'] = 0
                    event_dict['registration_progress'] = 0
                    event_dict['is_full'] = False
            else:
                # 基本参赛人数信息
                event_dict['participant_count'] = participants_count
            
            events_data.append(event_dict)

        # 计算分页信息
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1

        t_after_python = time.perf_counter()
        logger.info(
            "get_events timings: params=%.1fms, count=%.1fms, list=%.1fms, participants=%.1fms, python=%.1fms, total=%.1fms",
            (t_after_params - t_start) * 1000,
            (t_after_count - t_after_params) * 1000,
            (t_after_list - t_after_count) * 1000,
            (t_after_participants - t_after_list) * 1000,
            (t_after_python - t_after_participants) * 1000,
            (t_after_python - t_start) * 1000,
        )

        return jsonify({
            'success': True,
            'data': events_data,
            'events': events_data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev
            },
            'filters': {
                'status': status,
                'keyword': keyword,
                'location': location,
                'date_from': date_from,
                'date_to': date_to,
                'order_by': order_by,
                'order_dir': order_dir
            }
        })
        
    except Exception as e:
        logger.error(f"获取赛事列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '获取赛事列表失败'
        }), 500
