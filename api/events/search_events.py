from flask import request, jsonify

from utils.decorators import login_required, log_action, handle_db_errors

from . import events_bp, db_manager, logger


@events_bp.route('/search', methods=['GET'])
@login_required
@log_action('搜索赛事')
@handle_db_errors
def search_events():
    """高级搜索赛事API"""
    try:
        keyword = request.args.get('keyword', '').strip()
        if not keyword:
            return jsonify({
                'success': False,
                'message': '搜索关键词不能为空'
            }), 400
        
        # 使用高级搜索功能
        events = db_manager.get_all_events(keyword=keyword, limit=20)

        # 批量获取参赛人数，避免 N+1 查询
        event_ids = [event.event_id for event in events]
        participants_counts = db_manager.count_participants_by_events(event_ids) if event_ids else {}
        
        events_data = []
        for event in events:
            event_dict = event.to_dict()
            participants_count = participants_counts.get(event.event_id, 0)
            event_dict['participants_count'] = participants_count
            events_data.append(event_dict)
        
        return jsonify({
            'success': True,
            'events': events_data,
            'keyword': keyword,
            'count': len(events_data)
        })
        
    except Exception as e:
        logger.error(f"搜索赛事失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '搜索赛事失败'
        }), 500
