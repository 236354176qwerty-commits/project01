from flask import request, jsonify, session, current_app

from models import Score
from utils.decorators import login_required, role_required, validate_json, log_action, handle_db_errors

from . import scoring_bp, db_manager, logger


@scoring_bp.route('/participant/<int:participant_id>', methods=['POST'])
@login_required
@role_required(['judge', 'admin', 'super_admin'])
@validate_json(['technique_score', 'performance_score'])
@log_action('提交评分')
@handle_db_errors
def submit_score(participant_id):
    """提交评分"""
    data = request.get_json()
    judge_id = session.get('user_id')
    
    try:
        # 验证分数范围
        scoring_config = current_app.config.get('SCORING_CONFIG', {})
        technique_max = scoring_config.get('technique_max', 10.0)
        performance_max = scoring_config.get('performance_max', 10.0)
        deduction_max = scoring_config.get('deduction_max', 5.0)
        
        technique_score = float(data['technique_score'])
        performance_score = float(data['performance_score'])
        deduction = float(data.get('deduction', 0.0))
        round_number = int(data.get('round_number', 1))
        
        # 验证分数范围
        if not (0 <= technique_score <= technique_max):
            return jsonify({
                'success': False,
                'message': f'技术分必须在0-{technique_max}之间'
            }), 400
        
        if not (0 <= performance_score <= performance_max):
            return jsonify({
                'success': False,
                'message': f'表现分必须在0-{performance_max}之间'
            }), 400
        
        if not (0 <= deduction <= deduction_max):
            return jsonify({
                'success': False,
                'message': f'扣分必须在0-{deduction_max}之间'
            }), 400
        
        # 创建评分对象
        score = Score(
            participant_id=participant_id,
            judge_id=judge_id,
            round_number=round_number,
            technique_score=technique_score,
            performance_score=performance_score,
            deduction=deduction,
            notes=data.get('notes', '').strip()
        )
        
        # 计算总分
        score.calculate_total()
        
        # 保存到数据库
        saved_score = db_manager.create_or_update_score(score)
        
        logger.info(f"裁判 {judge_id} 为参赛者 {participant_id} 提交评分: {score.total_score}")
        
        return jsonify({
            'success': True,
            'message': '评分提交成功',
            'score': saved_score.to_dict()
        })
        
    except ValueError:
        return jsonify({
            'success': False,
            'message': '分数格式不正确'
        }), 400
    except Exception as e:
        logger.error(f"提交评分失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '提交评分失败，请稍后重试'
        }), 500
