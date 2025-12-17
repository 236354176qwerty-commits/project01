/* 武术赛事管理系统 - 签到功能JavaScript */

// ==================== 签到管理器 ====================

/**
 * 签到管理器
 */
class CheckinManager {
    constructor() {
        this.currentEvent = null;
        this.participants = [];
        this.filteredParticipants = [];
        this.selectedParticipants = [];
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadEvents();
    }
    
    bindEvents() {
        // 赛事选择事件
        $('#eventSelect').on('change', () => {
            this.loadParticipants();
        });
        
        // 搜索事件
        $('#searchParticipant').on('input', debounce(() => {
            this.searchParticipants();
        }, 300));
        
        // 全选事件
        $('#selectAll').on('change', () => {
            this.toggleSelectAll();
        });
        
        // 批量签到事件
        $('#batchCheckin').on('click', () => {
            this.showBatchCheckinModal();
        });
        
        // 状态筛选事件
        $('.status-filter').on('click', (e) => {
            const status = $(e.target).data('status');
            this.filterByStatus(status);
        });
    }
    
    loadEvents() {
        $.ajax({
            url: '/api/events/',
            method: 'GET',
            data: { status: 'published,ongoing' },
            success: (response) => {
                if (response.success) {
                    this.populateEventSelect(response.events);
                }
            },
            error: () => {
                showMessage('加载赛事列表失败', 'error');
            }
        });
    }
    
    populateEventSelect(events) {
        const select = $('#eventSelect');
        select.empty().append('<option value="">请选择赛事</option>');
        
        events.forEach(event => {
            select.append(`<option value="${event.event_id}">${event.name}</option>`);
        });
    }
    
    loadParticipants() {
        const eventId = $('#eventSelect').val();
        if (!eventId) {
            this.showNoParticipants();
            return;
        }
        
        this.currentEvent = eventId;
        this.showLoading();
        
        $.ajax({
            url: `/api/events/${eventId}/participants`,
            method: 'GET',
            success: (response) => {
                if (response.success) {
                    this.participants = response.participants;
                    this.filteredParticipants = [...this.participants];
                    this.displayParticipants();
                    this.updateStatistics();
                } else {
                    this.showNoParticipants();
                }
            },
            error: () => {
                showMessage('加载参赛者列表失败', 'error');
                this.showNoParticipants();
            },
            complete: () => {
                this.hideLoading();
            }
        });
    }
    
    displayParticipants() {
        if (this.filteredParticipants.length === 0) {
            this.showNoParticipants();
            return;
        }
        
        const tbody = $('#participants-tbody');
        tbody.empty();
        
        this.filteredParticipants.forEach(participant => {
            const row = this.createParticipantRow(participant);
            tbody.append(row);
        });
        
        $('#participants-table').show();
        $('#no-participants').hide();
        
        // 重新绑定复选框事件
        $('.participant-checkbox').on('change', () => {
            this.updateSelectedCount();
        });
    }
    
    createParticipantRow(participant) {
        const isCheckedIn = participant.status === 'checked_in';
        const statusColor = isCheckedIn ? 'success' : 'warning';
        const statusText = isCheckedIn ? '已签到' : '未签到';
        const checkinTime = participant.checked_in_at ? 
            formatDateTime(participant.checked_in_at) : '-';
        
        return `
            <tr data-participant-id="${participant.participant_id}">
                <td>
                    <input type="checkbox" class="form-check-input participant-checkbox" 
                           value="${participant.participant_id}">
                </td>
                <td><span class="badge bg-primary">${participant.registration_number}</span></td>
                <td>
                    <div>
                        <h6 class="mb-0">${participant.real_name || participant.username}</h6>
                        <small class="text-muted">${participant.username}</small>
                    </div>
                </td>
                <td>${participant.category || '-'}</td>
                <td>${participant.weight_class || '-'}</td>
                <td>
                    <span class="badge bg-${statusColor}">${statusText}</span>
                </td>
                <td>${checkinTime}</td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        ${!isCheckedIn ? `
                            <button class="btn btn-outline-success" onclick="checkinManager.checkinParticipant(${participant.participant_id})" 
                                    title="签到">
                                <i class="fas fa-check"></i>
                            </button>
                        ` : `
                            <button class="btn btn-outline-warning" onclick="checkinManager.cancelCheckin(${participant.participant_id})" 
                                    title="取消签到">
                                <i class="fas fa-undo"></i>
                            </button>
                        `}
                        <button class="btn btn-outline-info" onclick="checkinManager.viewCheckinDetail(${participant.participant_id})" 
                                title="查看详情">
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    updateStatistics() {
        const total = this.participants.length;
        const checkedIn = this.participants.filter(p => p.status === 'checked_in').length;
        
        $('#checkedInCount').text(checkedIn);
        $('#totalCount').text(total);
        
        const percentage = total > 0 ? (checkedIn / total * 100) : 0;
        $('#checkinProgress').css('width', `${percentage}%`);
    }
    
    searchParticipants() {
        const searchTerm = $('#searchParticipant').val().trim().toLowerCase();
        
        if (!searchTerm) {
            this.filteredParticipants = [...this.participants];
        } else {
            this.filteredParticipants = this.participants.filter(participant => {
                return participant.real_name.toLowerCase().includes(searchTerm) ||
                       participant.username.toLowerCase().includes(searchTerm) ||
                       participant.registration_number.toLowerCase().includes(searchTerm);
            });
        }
        
        this.displayParticipants();
    }
    
    filterByStatus(status) {
        if (status === 'all') {
            this.filteredParticipants = [...this.participants];
        } else {
            this.filteredParticipants = this.participants.filter(p => p.status === status);
        }
        
        this.displayParticipants();
    }
    
    toggleSelectAll() {
        const selectAll = $('#selectAll').is(':checked');
        $('.participant-checkbox').prop('checked', selectAll);
        this.updateSelectedCount();
    }
    
    updateSelectedCount() {
        this.selectedParticipants = $('.participant-checkbox:checked').map(function() {
            return parseInt($(this).val());
        }).get();
        
        // 更新全选复选框状态
        const totalCheckboxes = $('.participant-checkbox').length;
        const checkedCheckboxes = $('.participant-checkbox:checked').length;
        
        $('#selectAll').prop('indeterminate', checkedCheckboxes > 0 && checkedCheckboxes < totalCheckboxes);
        $('#selectAll').prop('checked', checkedCheckboxes === totalCheckboxes && totalCheckboxes > 0);
    }
    
    checkinParticipant(participantId) {
        if (!this.currentEvent) return;
        
        $.ajax({
            url: `/api/events/${this.currentEvent}/checkin/${participantId}`,
            method: 'POST',
            success: (response) => {
                if (response.success) {
                    showMessage('签到成功！', 'success');
                    this.loadParticipants();
                } else {
                    showMessage(response.message, 'error');
                }
            },
            error: (xhr) => {
                let message = '签到失败，请稍后重试';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    message = xhr.responseJSON.message;
                }
                showMessage(message, 'error');
            }
        });
    }
    
    cancelCheckin(participantId) {
        if (!confirm('确定要取消该参赛者的签到状态吗？')) {
            return;
        }
        
        // 这里应该调用取消签到的API
        showMessage('取消签到功能开发中...', 'info');
    }
    
    showBatchCheckinModal() {
        this.updateSelectedCount();
        
        if (this.selectedParticipants.length === 0) {
            showMessage('请先选择要签到的参赛者', 'warning');
            return;
        }
        
        $('#selectedCount').text(this.selectedParticipants.length);
        $('#batchCheckinModal').modal('show');
    }
    
    confirmBatchCheckin() {
        const notes = $('#batchNotes').val().trim();
        
        // 这里应该调用批量签到的API
        showMessage(`批量签到功能开发中... (选中${this.selectedParticipants.length}人)`, 'info');
        $('#batchCheckinModal').modal('hide');
    }
    
    viewCheckinDetail(participantId) {
        const participant = this.participants.find(p => p.participant_id === participantId);
        if (!participant) return;
        
        const isCheckedIn = participant.status === 'checked_in';
        const detailContent = `
            <div class="row">
                <div class="col-md-6">
                    <h6>参赛者信息</h6>
                    <table class="table table-sm">
                        <tr><td>参赛编号:</td><td><span class="badge bg-primary">${participant.registration_number}</span></td></tr>
                        <tr><td>姓名:</td><td>${participant.real_name || participant.username}</td></tr>
                        <tr><td>用户名:</td><td>${participant.username}</td></tr>
                        <tr><td>参赛项目:</td><td>${participant.category || '-'}</td></tr>
                        <tr><td>级别:</td><td>${participant.weight_class || '-'}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>签到状态</h6>
                    <table class="table table-sm">
                        <tr><td>当前状态:</td><td><span class="badge bg-${isCheckedIn ? 'success' : 'warning'}">${isCheckedIn ? '已签到' : '未签到'}</span></td></tr>
                        <tr><td>报名时间:</td><td>${formatDateTime(participant.registered_at)}</td></tr>
                        <tr><td>签到时间:</td><td>${participant.checked_in_at ? formatDateTime(participant.checked_in_at) : '-'}</td></tr>
                    </table>
                </div>
            </div>
            ${participant.notes ? `
                <div class="mt-3">
                    <h6>备注信息</h6>
                    <p class="text-muted">${participant.notes}</p>
                </div>
            ` : ''}
        `;
        
        $('#checkinDetailContent').html(detailContent);
        
        // 生成操作按钮
        let actions = '';
        if (!isCheckedIn) {
            actions += `<button class="btn btn-success me-2" onclick="checkinManager.checkinParticipant(${participantId})">
                <i class="fas fa-check me-1"></i>签到
            </button>`;
        } else {
            actions += `<button class="btn btn-warning me-2" onclick="checkinManager.cancelCheckin(${participantId})">
                <i class="fas fa-undo me-1"></i>取消签到
            </button>`;
        }
        
        $('#checkinDetailActions').html(actions);
        $('#checkinDetailModal').modal('show');
    }
    
    showLoading() {
        $('#loading-participants').show();
        $('#participants-table, #no-participants').hide();
    }
    
    hideLoading() {
        $('#loading-participants').hide();
    }
    
    showNoParticipants() {
        $('#no-participants').show();
        $('#participants-table').hide();
        this.updateStatistics();
    }
    
    refresh() {
        showMessage('正在刷新签到信息...', 'info');
        if (this.currentEvent) {
            this.loadParticipants();
        }
    }
}

// ==================== 签到统计图表 ====================

/**
 * 签到统计图表
 */
class CheckinChart {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.chart = null;
        this.init();
    }
    
    init() {
        if (!this.container) return;
        
        // 创建图表容器
        this.container.innerHTML = '<canvas id="checkinChart"></canvas>';
        this.canvas = document.getElementById('checkinChart');
        
        // 初始化图表（这里使用Chart.js的示例，实际需要引入Chart.js库）
        this.initChart();
    }
    
    initChart() {
        // 如果有Chart.js库，可以创建图表
        if (typeof Chart !== 'undefined') {
            const ctx = this.canvas.getContext('2d');
            this.chart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['已签到', '未签到'],
                    datasets: [{
                        data: [0, 0],
                        backgroundColor: ['#28a745', '#ffc107'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
    }
    
    updateData(checkedIn, total) {
        if (this.chart) {
            const unchecked = total - checkedIn;
            this.chart.data.datasets[0].data = [checkedIn, unchecked];
            this.chart.update();
        }
    }
}

// ==================== 二维码签到 ====================

/**
 * 二维码签到管理器
 */
class QRCheckinManager {
    constructor() {
        this.scanner = null;
        this.isScanning = false;
    }
    
    startScan() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            showMessage('您的浏览器不支持摄像头功能', 'error');
            return;
        }
        
        // 这里需要引入二维码扫描库，如 qr-scanner
        showMessage('二维码扫描功能需要额外的库支持', 'info');
    }
    
    stopScan() {
        if (this.scanner) {
            this.scanner.stop();
            this.isScanning = false;
        }
    }
    
    onScanSuccess(result) {
        // 解析二维码结果
        try {
            const data = JSON.parse(result);
            if (data.type === 'participant' && data.id) {
                this.checkinByQR(data.id);
            } else {
                showMessage('无效的二维码', 'error');
            }
        } catch (e) {
            showMessage('二维码格式错误', 'error');
        }
    }
    
    checkinByQR(participantId) {
        // 调用签到API
        if (window.checkinManager) {
            window.checkinManager.checkinParticipant(participantId);
        }
    }
}

// ==================== 初始化 ====================
$(document).ready(function() {
    // 初始化签到管理器
    window.checkinManager = new CheckinManager();
    
    // 初始化二维码签到
    window.qrCheckinManager = new QRCheckinManager();
    
    // 绑定全局函数
    window.refreshCheckin = function() {
        window.checkinManager.refresh();
    };
    
    window.batchCheckin = function() {
        window.checkinManager.showBatchCheckinModal();
    };
    
    window.confirmBatchCheckin = function() {
        window.checkinManager.confirmBatchCheckin();
    };
    
    window.filterByStatus = function(status) {
        window.checkinManager.filterByStatus(status);
    };
});

// 导出到全局
window.CheckinManager = CheckinManager;
window.CheckinChart = CheckinChart;
window.QRCheckinManager = QRCheckinManager;
