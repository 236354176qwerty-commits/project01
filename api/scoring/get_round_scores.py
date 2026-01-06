from flask import jsonify

from utils.decorators import login_required, role_required, log_action, handle_db_errors

from . import scoring_bp, db_manager, logger


@scoring_bp.route('/participant/<int:participant_id>/round/<int:round_number>', methods=['GET'])
@login_required
@role_required(['judge', 'admin', 'super_admin'])
@log_action('获取轮次评分')
@handle_db_errors
def get_round_scores(participant_id, round_number):
    """获取特定轮次的评分"""
    scores = db_manager.get_scores_by_participant(participant_id)

    # 筛选特定轮次的评分
    round_scores = [score for score in scores if score.round_number == round_number]

    scores_data = []
    for score in round_scores:
        score_dict = score.to_dict()
        # 添加裁判姓名
        if hasattr(score, 'judge_name'):
            score_dict['judge_name'] = score.judge_name
        scores_data.append(score_dict)

    return jsonify({
        'success': True,
        'data': {
            'scores': scores_data,
            'round_number': round_number,
        },
        'scores': scores_data,
        'round_number': round_number,
    })
