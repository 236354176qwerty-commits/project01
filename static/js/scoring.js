/* 武术赛事管理系统 - 评分功能JavaScript */

// ==================== 评分相关函数 ====================

/**
 * 评分计算器
 */
class ScoringCalculator {
    constructor() {
        this.config = {
            techniqueMax: 10.0,
            performanceMax: 10.0,
            deductionMax: 5.0,
            decimalPlaces: 2
        };
    }
    
    /**
     * 计算总分
     * @param {number} technique - 技术分
     * @param {number} performance - 表现分
     * @param {number} deduction - 扣分
     * @returns {number} 总分
     */
    calculateTotal(technique, performance, deduction) {
        const total = technique + performance - deduction;
        return Math.round(total * Math.pow(10, this.config.decimalPlaces)) / Math.pow(10, this.config.decimalPlaces);
    }
    
    /**
     * 验证分数
     * @param {number} technique - 技术分
     * @param {number} performance - 表现分
     * @param {number} deduction - 扣分
     * @returns {Object} 验证结果
     */
    validateScores(technique, performance, deduction) {
        const errors = [];
        
        if (technique < 0 || technique > this.config.techniqueMax) {
            errors.push(`技术分必须在0-${this.config.techniqueMax}之间`);
        }
        
        if (performance < 0 || performance > this.config.performanceMax) {
            errors.push(`表现分必须在0-${this.config.performanceMax}之间`);
        }
        
        if (deduction < 0 || deduction > this.config.deductionMax) {
            errors.push(`扣分必须在0-${this.config.deductionMax}之间`);
        }
        
        return {
            valid: errors.length === 0,
            errors: errors
        };
    }
}

/**
 * 评分表单管理器
 */
class ScoringFormManager {
    constructor() {
        this.calculator = new ScoringCalculator();
        this.currentParticipant = null;
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadScoringConfig();
    }
    
    bindEvents() {
        // 分数输入事件
        $('#techniqueScore, #performanceScore, #deduction').on('input', () => {
            this.calculateTotal();
        });
        
        // 表单提交事件
        $('#scoringForm').on('submit', (e) => {
            e.preventDefault();
            this.submitScore();
        });
        
        // 重置按钮事件
        $('#resetScoring').on('click', () => {
            this.resetForm();
        });
    }
    
    calculateTotal() {
        const technique = parseFloat($('#techniqueScore').val()) || 0;
        const performance = parseFloat($('#performanceScore').val()) || 0;
        const deduction = parseFloat($('#deduction').val()) || 0;
        
        const total = this.calculator.calculateTotal(technique, performance, deduction);
        $('#totalScoreDisplay').text(total.toFixed(2) + ' 分');
        
        // 实时验证
        const validation = this.calculator.validateScores(technique, performance, deduction);
        this.showValidationResult(validation);
    }
    
    showValidationResult(validation) {
        const container = $('#validationResult');
        container.empty();
        
        if (!validation.valid) {
            validation.errors.forEach(error => {
                container.append(`<div class="text-danger small">${error}</div>`);
            });
        }
    }
    
    submitScore() {
        const technique = parseFloat($('#techniqueScore').val()) || 0;
        const performance = parseFloat($('#performanceScore').val()) || 0;
        const deduction = parseFloat($('#deduction').val()) || 0;
        
        const validation = this.calculator.validateScores(technique, performance, deduction);
        if (!validation.valid) {
            showMessage(validation.errors.join('<br>'), 'error');
            return;
        }
        
        const scoreData = {
            technique_score: technique,
            performance_score: performance,
            deduction: deduction,
            round_number: parseInt($('#roundNumber').val()) || 1,
            notes: $('#scoreNotes').val().trim()
        };
        
        this.saveScore(scoreData);
    }
    
    saveScore(scoreData) {
        if (!this.currentParticipant) {
            showMessage('请先选择参赛者', 'warning');
            return;
        }
        
        $.ajax({
            url: `/api/scoring/participant/${this.currentParticipant}`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(scoreData),
            success: (response) => {
                if (response.success) {
                    showMessage('评分提交成功！', 'success');
                    this.resetForm();
                    this.loadParticipantScores();
                } else {
                    showMessage(response.message, 'error');
                }
            },
            error: (xhr) => {
                let message = '评分提交失败，请稍后重试';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    message = xhr.responseJSON.message;
                }
                showMessage(message, 'error');
            }
        });
    }
    
    resetForm() {
        $('#scoringForm')[0].reset();
        $('#totalScoreDisplay').text('0.0 分');
        $('#validationResult').empty();
    }
    
    loadScoringConfig() {
        $.ajax({
            url: '/api/scoring/config',
            method: 'GET',
            success: (response) => {
                if (response.success) {
                    this.calculator.config = { ...this.calculator.config, ...response.config };
                    this.updateFormLimits();
                }
            }
        });
    }
    
    updateFormLimits() {
        $('#techniqueScore').attr('max', this.calculator.config.techniqueMax);
        $('#performanceScore').attr('max', this.calculator.config.performanceMax);
        $('#deduction').attr('max', this.calculator.config.deductionMax);
    }
    
    setCurrentParticipant(participantId) {
        this.currentParticipant = participantId;
        this.loadParticipantScores();
    }
    
    loadParticipantScores() {
        if (!this.currentParticipant) return;
        
        $.ajax({
            url: `/api/scoring/participant/${this.currentParticipant}`,
            method: 'GET',
            success: (response) => {
                if (response.success) {
                    this.displayHistoricalScores(response.scores, response.average_score);
                }
            }
        });
    }
    
    displayHistoricalScores(scores, averageScore) {
        const container = $('#historical-scores');
        
        if (scores.length === 0) {
            container.html(`
                <div class="text-center py-3">
                    <i class="fas fa-chart-line fa-2x text-muted mb-2"></i>
                    <p class="text-muted small mb-0">暂无评分记录</p>
                </div>
            `);
            return;
        }
        
        let html = `
            <div class="mb-3 text-center">
                <h5 class="text-primary mb-0">${averageScore}</h5>
                <small class="text-muted">平均分</small>
            </div>
            <div class="scores-list">
        `;
        
        scores.forEach(score => {
            html += `
                <div class="score-item border-bottom pb-2 mb-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${score.judge_name || '裁判'}</strong>
                            <small class="text-muted">第${score.round_number}轮</small>
                        </div>
                        <span class="badge bg-success">${score.total_score}</span>
                    </div>
                    <div class="small text-muted">
                        技术: ${score.technique_score} | 表现: ${score.performance_score} | 扣分: ${score.deduction}
                    </div>
                    ${score.notes ? `<div class="small text-muted mt-1">${score.notes}</div>` : ''}
                </div>
            `;
        });
        
        html += '</div>';
        container.html(html);
    }
}

// ==================== 初始化 ====================
$(document).ready(function() {
    window.scoringManager = new ScoringFormManager();
});

// 导出到全局
window.ScoringCalculator = ScoringCalculator;
window.ScoringFormManager = ScoringFormManager;
