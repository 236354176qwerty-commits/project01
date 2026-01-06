from flask import jsonify

from utils.decorators import login_required, role_required, log_action, handle_db_errors

from . import scoring_bp, db_manager, logger


@scoring_bp.route('/statistics/event/<int:event_id>', methods=['GET'])
@login_required
@role_required(['admin', 'super_admin'])
@log_action('获取评分统计')
@handle_db_errors
def get_scoring_statistics(event_id):
    """获取评分统计信息"""
    # 获取赛事的所有参赛者
    participants = db_manager.get_participants_by_event(event_id)

    statistics = {
        'total_participants': len(participants),
        'scored_participants': 0,
        'unscored_participants': 0,
        'total_scores': 0,
        'average_technique_score': 0.0,
        'average_performance_score': 0.0,
        'average_total_score': 0.0,
        'highest_score': 0.0,
        'lowest_score': 0.0
    }

    all_scores = []
    technique_scores = []
    performance_scores = []
    total_scores = []

    for participant in participants:
        scores = db_manager.get_scores_by_participant(participant.participant_id)

        if scores:
            statistics['scored_participants'] += 1
            for score in scores:
                all_scores.append(score)
                technique_scores.append(score.technique_score)
                performance_scores.append(score.performance_score)
                total_scores.append(score.total_score)
        else:
            statistics['unscored_participants'] += 1

    statistics['total_scores'] = len(all_scores)

    if total_scores:
        statistics['average_technique_score'] = round(sum(technique_scores) / len(technique_scores), 2)
        statistics['average_performance_score'] = round(sum(performance_scores) / len(performance_scores), 2)
        statistics['average_total_score'] = round(sum(total_scores) / len(total_scores), 2)
        statistics['highest_score'] = max(total_scores)
        statistics['lowest_score'] = min(total_scores)

    return jsonify({
        'success': True,
        'data': statistics,
        'statistics': statistics,
    })
