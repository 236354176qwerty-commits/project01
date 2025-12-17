from flask import jsonify, current_app

from utils.decorators import login_required, role_required, log_action, handle_db_errors
from utils.helpers import calculate_average_score

from . import scoring_bp, db_manager, logger


@scoring_bp.route('/event/<int:event_id>/scores', methods=['GET'])
@login_required
@role_required(['admin', 'super_admin'])
@log_action('获取赛事所有评分')
@handle_db_errors
def get_event_scores(event_id):
    """获取赛事的所有评分"""
    try:
        # 获取赛事的所有参赛者
        participants = db_manager.get_participants_by_event(event_id)
        
        event_scores = []
        for participant in participants:
            scores = db_manager.get_scores_by_participant(participant.participant_id)
            
            participant_data = {
                'participant': participant.to_dict(),
                'scores': [score.to_dict() for score in scores]
            }
            
            # 计算平均分
            if scores:
                scoring_config = current_app.config.get('SCORING_CONFIG', {})
                total_scores = [score.total_score for score in scores]
                average_score = calculate_average_score(
                    total_scores,
                    drop_highest=scoring_config.get('drop_highest', True),
                    drop_lowest=scoring_config.get('drop_lowest', True)
                )
                participant_data['average_score'] = average_score
            else:
                participant_data['average_score'] = 0.0
            
            event_scores.append(participant_data)
        
        # 按平均分排序
        event_scores.sort(key=lambda x: x['average_score'], reverse=True)
        
        return jsonify({
            'success': True,
            'event_scores': event_scores
        })
        
    except Exception as e:
        logger.error(f"获取赛事评分失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '获取赛事评分失败'
        }), 500
