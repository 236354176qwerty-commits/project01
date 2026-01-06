from flask import jsonify

from utils.decorators import login_required, log_action, handle_db_errors

from . import events_bp, db_manager, logger


@events_bp.route('/summary', methods=['GET'])
@login_required
@log_action('获取赛事概览')
@handle_db_errors
def get_events_summary():
    """获取赛事概览统计API"""
    # 统计各状态的赛事数量（单次聚合查询）
    status_counts = db_manager.count_events_group_by_status()
    total = sum(status_counts.values())
    summary = {
        'total': total,
        'draft': status_counts.get('draft', 0),
        'published': status_counts.get('published', 0),
        'ongoing': status_counts.get('ongoing', 0),
        'completed': status_counts.get('completed', 0),
        'cancelled': status_counts.get('cancelled', 0),
    }
    
    # 获取最近的赛事
    recent_events = db_manager.get_all_events(
        order_by='created_at',
        order_dir='DESC',
        limit=5,
    )

    # 批量获取最近赛事的参赛人数
    recent_event_ids = [event.event_id for event in recent_events]
    recent_participants_counts = db_manager.count_participants_by_events(recent_event_ids) if recent_event_ids else {}
    
    recent_events_data = []
    for event in recent_events:
        event_dict = event.to_dict()
        participants_count = recent_participants_counts.get(event.event_id, 0)
        event_dict['participants_count'] = participants_count
        recent_events_data.append(event_dict)
    
    summary['recent_events'] = recent_events_data
    
    return jsonify({
        'success': True,
        'data': summary,
        'summary': summary,
        'message': '成功获取赛事概览统计',
    })
