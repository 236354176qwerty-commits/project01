from flask import jsonify, current_app

from utils.decorators import login_required, role_required, log_action, handle_db_errors
from utils.helpers import calculate_average_score, format_score

from . import scoring_bp, db_manager, logger


@scoring_bp.route('/participant/<int:participant_id>', methods=['GET'])
@login_required
@role_required(['judge', 'admin', 'super_admin'])
@log_action('获取参赛者评分')
@handle_db_errors
def get_participant_scores(participant_id):
    """获取参赛者的所有评分"""
    scores = db_manager.get_scores_by_participant(participant_id)

    scores_data = []
    for score in scores:
        score_dict = score.to_dict()
        # 添加裁判姓名
        if hasattr(score, 'judge_name'):
            score_dict['judge_name'] = score.judge_name
        scores_data.append(score_dict)

    # 计算平均分
    if scores_data:
        scoring_config = current_app.config.get('SCORING_CONFIG', {})
        total_scores = [score['total_score'] for score in scores_data]
        average_score = calculate_average_score(
            total_scores,
            drop_highest=scoring_config.get('drop_highest', True),
            drop_lowest=scoring_config.get('drop_lowest', True)
        )
    else:
        average_score = 0.0

    formatted_average = format_score(average_score)

    return jsonify({
        'success': True,
        'data': {
            'scores': scores_data,
            'average_score': average_score,
            'formatted_average': formatted_average,
        },
        'scores': scores_data,
        'average_score': average_score,
        'formatted_average': formatted_average,
    })
