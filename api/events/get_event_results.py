from flask import jsonify, current_app

from utils.decorators import login_required, log_action, handle_db_errors
from utils.helpers import calculate_average_score

from . import events_bp, db_manager, logger


@events_bp.route('/<int:event_id>/results', methods=['GET'])
@login_required
@log_action('获取赛事成绩')
@handle_db_errors
def get_event_results(event_id):
    """获取赛事成绩"""
    # 检查赛事是否存在
    event = db_manager.get_event_by_id(event_id)
    if not event:
        return jsonify({
            'success': False,
            'message': '赛事不存在'
        }), 404
    
    # 获取原始成绩数据
    results = db_manager.get_event_results(event_id, include_scores=False)
    
    # 获取评分配置
    scoring_config = current_app.config.get('SCORING_CONFIG', {})
    min_judges = scoring_config.get('min_judges', 3)
    drop_highest = scoring_config.get('drop_highest', True)
    drop_lowest = scoring_config.get('drop_lowest', True)
    
    processed_results = []
    for result in results:
        score_count = result['score_count']
        scores_list = result['scores_list']
        
        # 数据验证
        validation = {
            'is_complete': False,
            'is_valid': False,
            'warnings': [],
            'status': 'incomplete'
        }
        
        # 检查是否有评分
        if score_count == 0:
            validation['warnings'].append('暂无评分')
            validation['status'] = 'no_scores'
        # 检查评分数量是否达到最小要求
        elif score_count < min_judges:
            validation['warnings'].append(f'评分数量不足（当前{score_count}个，需要至少{min_judges}个）')
            validation['status'] = 'insufficient_scores'
        else:
            validation['is_complete'] = True
            validation['is_valid'] = True
            validation['status'] = 'valid'
        
        # 计算平均分（使用统一的去最高最低分算法）
        if scores_list:
            average_score = calculate_average_score(
                scores_list,
                drop_highest=drop_highest,
                drop_lowest=drop_lowest
            )
        else:
            average_score = None
        
        # 构建处理后的结果
        processed_result = {
            'participant_id': result['participant_id'],
            'registration_number': result['registration_number'],
            'real_name': result['real_name'],
            'category': result['category'],
            'weight_class': result['weight_class'],
            'status': result['status'],
            'score_count': score_count,
            'average_score': average_score,
            'validation': validation
        }
        
        processed_results.append(processed_result)
    
    # 按平均分排序（None值排在最后）
    processed_results.sort(
        key=lambda x: (
            x['average_score'] is None,
            -x['average_score'] if x['average_score'] is not None else 0,
            x['registration_number'],
        )
    )
    
    return jsonify({
        'success': True,
        'results': processed_results,
        'scoring_config': {
            'min_judges': min_judges,
            'drop_highest': drop_highest,
            'drop_lowest': drop_lowest,
        },
        'data': processed_results,
    })
