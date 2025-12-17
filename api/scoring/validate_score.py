from flask import request, jsonify, current_app

from utils.decorators import login_required, role_required, validate_json
from utils.helpers import format_score

from . import scoring_bp, logger


@scoring_bp.route('/validate', methods=['POST'])
@login_required
@role_required(['judge', 'admin', 'super_admin'])
@validate_json(['technique_score', 'performance_score'])
def validate_score():
    """验证评分数据"""
    data = request.get_json()
    
    try:
        scoring_config = current_app.config.get('SCORING_CONFIG', {})
        technique_max = scoring_config.get('technique_max', 10.0)
        performance_max = scoring_config.get('performance_max', 10.0)
        deduction_max = scoring_config.get('deduction_max', 5.0)
        
        technique_score = float(data['technique_score'])
        performance_score = float(data['performance_score'])
        deduction = float(data.get('deduction', 0.0))
        
        errors = []
        
        if not (0 <= technique_score <= technique_max):
            errors.append(f'技术分必须在0-{technique_max}之间')
        
        if not (0 <= performance_score <= performance_max):
            errors.append(f'表现分必须在0-{performance_max}之间')
        
        if not (0 <= deduction <= deduction_max):
            errors.append(f'扣分必须在0-{deduction_max}之间')
        
        total_score = technique_score + performance_score - deduction
        
        return jsonify({
            'success': len(errors) == 0,
            'errors': errors,
            'total_score': total_score,
            'formatted_total': format_score(total_score)
        })
        
    except ValueError:
        return jsonify({
            'success': False,
            'errors': ['分数格式不正确']
        }), 400
    except Exception as e:
        logger.error(f"验证评分失败: {str(e)}")
        return jsonify({
            'success': False,
            'errors': ['验证失败']
        }), 500
