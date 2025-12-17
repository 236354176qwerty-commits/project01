/**
 * 共用的创建赛事模态框JavaScript
 */

// 模态框状态
let eventModalMode = 'create'; // 'create' 或 'edit'
let currentEventId = null;

/**
 * 验证报名时间
 * @returns {boolean} 是否验证通过
 */
function validateRegistrationTimes() {
    const startDate = $('#registrationStartDate').val();
    const endDate = $('#registrationDeadline').val();
    
    if (startDate && endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);
        
        if (start > end) {
            // 显示错误提示
            if (!$('#registrationTimeError').length) {
                $('<div id="registrationTimeError" class="text-danger small mt-1">报名开始时间不能晚于结束时间</div>')
                    .insertAfter('#registrationDeadline');
            }
            return false;
        }
    }
    
    // 验证通过，移除错误提示
    $('#registrationTimeError').remove();
    return true;
}

/**
 * 验证比赛时间
 * @returns {boolean} 是否验证通过
 */
function validateEventTimes() {
    const startDate = $('#startDate').val();
    const endDate = $('#endDate').val();
    const registrationEndDate = $('#registrationDeadline').val();
    let isValid = true;
    
    // 验证比赛开始和结束时间
    if (startDate && endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);
        
        if (start > end) {
            // 显示错误提示
            if (!$('#eventTimeError').length) {
                $('<div id="eventTimeError" class="text-danger small mt-1">比赛开始时间不能晚于结束时间</div>')
                    .insertAfter('#endDate');
            }
            isValid = false;
        } else {
            $('#eventTimeError').remove();
        }
    }
    
    // 验证比赛开始时间是否晚于报名结束时间
    if (startDate && registrationEndDate) {
        const eventStart = new Date(startDate);
        const regEnd = new Date(registrationEndDate);
        
        if (eventStart <= regEnd) {
            // 显示错误提示在比赛开始时间输入框下方
            if (!$('#registrationEndTimeError').length) {
                $('<div id="registrationEndTimeError" class="text-danger small mt-1">比赛开始时间必须晚于报名结束时间</div>')
                    .insertAfter('#startDate');
            }
            isValid = false;
        } else {
            $('#registrationEndTimeError').remove();
        }
    }
    
    return isValid;
}

/**
 * 显示创建赛事模态框
 */
function showCreateEventModal() {
    eventModalMode = 'create';
    currentEventId = null;
    
    // 重置表单
    $('#eventForm')[0].reset();
    $('#eventId').val('');
    
    // 设置标题和按钮
    $('#eventModalTitle').html('<i class="fas fa-plus me-2"></i>创建赛事');
    $('#eventModalSubmitBtn').html('<i class="fas fa-save me-2"></i>创建');
    
    // 添加实时验证
    // 当报名时间变化时，需要同时验证报名时间和比赛时间
    $('#registrationStartDate, #registrationDeadline').on('change input', function() {
        validateRegistrationTimes();
        validateEventTimes(); // 因为比赛开始时间需要和报名结束时间比较
    });
    
    // 当比赛时间变化时，验证比赛时间
    $('#startDate, #endDate').on('change input', validateEventTimes);
    
    // 显示模态框
    $('#eventModal').modal('show');
}

/**
 * 显示编辑赛事模态框
 */
function showEditEventModal(event) {
    if (!event) return;
    
    eventModalMode = 'edit';
    currentEventId = event.event_id;
    
    // 填充表单数据
    $('#eventModalTitle').html('<i class="fas fa-edit me-2"></i>编辑赛事');
    $('#eventId').val(event.event_id);
    $('#eventName').val(event.name);
    $('#eventLocation').val(event.location);
    $('#eventDescription').val(event.description);
    $('#maxParticipants').val(event.max_participants);
    $('#startDate').val(formatDateTimeForInput(event.start_date));
    $('#endDate').val(formatDateTimeForInput(event.end_date));
    $('#registrationStartDate').val(formatDateTimeForInput(event.registration_start_time));
    $('#registrationDeadline').val(formatDateTimeForInput(event.registration_deadline));
    $('#eventStatus').val(event.status);
    $('#contactPhone').val(event.contact_phone || '');
    $('#organizer').val(event.organizer || '');
    $('#coOrganizer').val(event.co_organizer || '');
    
    const fees = {
        individual_fee: (event.individual_fee !== undefined ? event.individual_fee : undefined),
        pair_practice_fee: (event.pair_practice_fee !== undefined ? event.pair_practice_fee : undefined),
        team_competition_fee: (event.team_competition_fee !== undefined ? event.team_competition_fee : undefined)
    };
    const fallbackFees = getEventFees(event.event_id);
    $('#individualFee').val(fees.individual_fee || '');
    $('#pairPracticeFee').val(fees.pair_practice_fee || '');
    $('#teamCompetitionFee').val(fees.team_competition_fee || '');

    if (!$('#individualFee').val() && !$('#pairPracticeFee').val() && !$('#teamCompetitionFee').val()) {
        $('#individualFee').val(fallbackFees.individual_fee || '');
        $('#pairPracticeFee').val(fallbackFees.pair_practice_fee || '');
        $('#teamCompetitionFee').val(fallbackFees.team_competition_fee || '');
    }
    
    // 设置按钮
    $('#eventModalSubmitBtn').html('<i class="fas fa-save me-2"></i>保存');
    
    // 更新状态预览
    updateAutoStatusPreview();
    
    // 添加实时验证
    $('#registrationStartDate, #registrationDeadline').off('change input').on('change input', function() {
        validateRegistrationTimes();
        validateEventTimes(); // 因为比赛开始时间需要和报名结束时间比较
    });
    
    // 当比赛时间变化时，验证比赛时间
    $('#startDate, #endDate').off('change input').on('change input', validateEventTimes);
    
    // 显示模态框
    $('#eventModal').modal('show');
}

/**
 * 提交表单（统一处理创建和编辑）
 */
function submitEventForm() {
    const form = $('#eventForm')[0];
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    // 验证报名时间
    if (!validateRegistrationTimes() || !validateEventTimes()) {
        return;
    }
    
    const eventData = {
        name: $('#eventName').val().trim(),
        location: $('#eventLocation').val().trim(),
        registration_start_date: $('#registrationStartDate').val() || null,
        registration_deadline: $('#registrationDeadline').val() || null,
        start_date: $('#startDate').val(),
        end_date: $('#endDate').val(),
        description: $('#eventDescription').val().trim(),
        max_participants: parseInt($('#maxParticipants').val()) || 100,
        status: $('#eventStatus').val(),
        contact_phone: $('#contactPhone').val().trim(),
        organizer: $('#organizer').val().trim(),
        co_organizer: $('#coOrganizer').val().trim(),
        individual_fee: parseFloat($('#individualFee').val()) || 0,
        pair_practice_fee: parseFloat($('#pairPracticeFee').val()) || 0,
        team_competition_fee: parseFloat($('#teamCompetitionFee').val()) || 0
    };
    
    // 保存费用数据到localStorage（兼容旧逻辑，真实数据以数据库为准）
    const feeData = {
        individual_fee: parseFloat($('#individualFee').val()) || 0,
        pair_practice_fee: parseFloat($('#pairPracticeFee').val()) || 0,
        team_competition_fee: parseFloat($('#teamCompetitionFee').val()) || 0
    };
    
    // 根据模式选择API端点和方法
    let url = '/api/events/';
    let method = 'POST';
    
    if (eventModalMode === 'edit' && currentEventId) {
        url = `/api/events/${currentEventId}`;
        method = 'PUT';
    }
    
    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(eventData),
        success: function(response) {
            if (response.success) {
                // 保存费用数据到localStorage
                const eventId = response.event.event_id;
                saveEventFees(eventId, feeData);
                
                $('#eventModal').modal('hide');
                
                const action = eventModalMode === 'create' ? '创建' : '更新';
                showMessage(`赛事${action}成功！`, 'success');
                
                // 刷新相关数据
                if (typeof loadEvents === 'function') {
                    loadEvents(); // 赛事列表页面
                }
                if (typeof loadMyEvents === 'function') {
                    loadMyEvents(); // 仪表板页面
                }
                if (typeof loadDashboardData === 'function') {
                    loadDashboardData(); // 仪表板数据
                }
                if (typeof loadLatestEvents === 'function') {
                    loadLatestEvents(); // 首页最新赛事
                }
                
                // 重置表单
                $('#eventForm')[0].reset();
            } else {
                showMessage(response.message, 'error');
            }
        },
        error: function(xhr) {
            let message = '操作失败，请稍后重试';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                message = xhr.responseJSON.message;
            }
            showMessage(message, 'error');
        }
    });
}

/**
 * 格式化日期时间为输入框格式
 */
function formatDateTimeForInput(dateTimeStr) {
    if (!dateTimeStr) return '';
    
    try {
        const date = new Date(dateTimeStr);
        if (isNaN(date.getTime())) return '';
        
        // 转换为本地时间的ISO字符串（去掉秒和毫秒）
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${year}-${month}-${day}T${hours}:${minutes}`;
    } catch (e) {
        return '';
    }
}

/**
 * 显示消息提示（如果页面没有定义showMessage函数）
 */
if (typeof showMessage !== 'function') {
    function showMessage(message, type) {
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'error' ? 'alert-danger' : 'alert-info';
        
        const alertHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // 尝试找到合适的容器显示消息
        let container = $('#message-container');
        if (container.length === 0) {
            container = $('.container').first();
        }
        if (container.length === 0) {
            container = $('body');
        }
        
        container.prepend(alertHtml);
        
        // 3秒后自动隐藏
        setTimeout(() => {
            $('.alert').fadeOut();
        }, 3000);
    }
}

/**
 * 更新自动状态预览
 */
function updateAutoStatusPreview() {
    const startDate = $('#startDate').val();
    const endDate = $('#endDate').val();
    const currentStatus = $('#eventStatus').val();
    
    if (!startDate || !endDate) {
        $('#autoStatusPreview').removeClass().addClass('badge bg-secondary').text('未开始');
        return;
    }
    
    const now = new Date();
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    let autoStatus, displayText, colorClass;
    
    if (now < start) {
        autoStatus = currentStatus === 'draft' ? 'draft' : 'published';
        displayText = '未开始';
        colorClass = currentStatus === 'draft' ? 'bg-secondary' : 'bg-info';
    } else if (now >= start && now <= end) {
        autoStatus = 'ongoing';
        displayText = '进行中';
        colorClass = 'bg-warning';
    } else {
        autoStatus = currentStatus === 'cancelled' ? 'cancelled' : 'completed';
        displayText = '已结束';
        colorClass = currentStatus === 'cancelled' ? 'bg-danger' : 'bg-success';
    }
    
    $('#autoStatusPreview').removeClass().addClass(`badge ${colorClass}`).text(displayText);
}

/**
 * 初始化模态框事件监听
 */
$(document).ready(function() {
    // 监听时间字段变化，更新状态预览
    $('#startDate, #endDate, #eventStatus').on('change', function() {
        updateAutoStatusPreview();
    });
    
    // 模态框显示时初始化状态预览
    $('#eventModal').on('shown.bs.modal', function() {
        updateAutoStatusPreview();
    });
    
    // 创建模态框时设置默认状态
    $('#eventModal').on('show.bs.modal', function() {
        if (eventModalMode === 'create') {
            $('#eventStatus').val('draft');
            updateAutoStatusPreview();
        }
    });
});

/**
 * 保存赛事费用数据到localStorage
 * @param {number} eventId - 赛事ID
 * @param {object} feeData - 费用数据对象
 */
function saveEventFees(eventId, feeData) {
    try {
        // 获取现有的费用数据
        const eventFees = JSON.parse(localStorage.getItem('eventFees') || '{}');
        
        // 更新指定赛事的费用
        eventFees[eventId] = {
            individual_fee: feeData.individual_fee || 0,
            pair_practice_fee: feeData.pair_practice_fee || 0,
            team_competition_fee: feeData.team_competition_fee || 0
        };
        
        // 保存回localStorage
        localStorage.setItem('eventFees', JSON.stringify(eventFees));
        
        console.log(`已保存赛事 ${eventId} 的费用数据:`, eventFees[eventId]);
    } catch (error) {
        console.error('保存赛事费用失败:', error);
    }
}

/**
 * 从localStorage获取赛事费用数据
 * @param {number} eventId - 赛事ID
 * @returns {object} 费用数据对象
 */
function getEventFees(eventId) {
    try {
        const eventFees = JSON.parse(localStorage.getItem('eventFees') || '{}');
        return eventFees[eventId] || {
            individual_fee: 0,
            pair_practice_fee: 0,
            team_competition_fee: 0
        };
    } catch (error) {
        console.error('读取赛事费用失败:', error);
        return {
            individual_fee: 0,
            pair_practice_fee: 0,
            team_competition_fee: 0
        };
    }
}
