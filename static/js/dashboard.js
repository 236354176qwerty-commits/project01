/* 武术赛事管理系统 - 仪表板JavaScript */

// ==================== 仪表板数据管理 ====================

/**
 * 初始化仪表板
 */
function initDashboard() {
    // 显示当前日期
    updateCurrentDate();
    
    // 加载统计数据
    loadStatistics();
    
    // 加载最近活动
    loadRecentActivities();
    
    // 加载我的赛事
    loadMyEvents();
    
    // 加载通知
    loadNotifications();
    
    // 检查用户权限并显示相应功能
    updateUIBasedOnRole();
}

/**
 * 更新当前日期显示
 */
function updateCurrentDate() {
    const now = new Date();
    const options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        weekday: 'long'
    };
    const dateString = now.toLocaleDateString('zh-CN', options);
    
    const dateElement = document.getElementById('currentDate');
    if (dateElement) {
        dateElement.textContent = dateString;
    }
}

/**
 * 加载统计数据
 */
function loadStatistics() {
    fetch('/api/dashboard/statistics')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateStatistics(data.statistics);
            }
        })
        .catch(error => {
            console.error('加载统计数据失败:', error);
            // 使用默认数据
            updateStatistics({
                my_events: 0,
                my_participations: 0,
                my_scores: 0,
                notifications: 0
            });
        });
}

/**
 * 更新统计数据显示
 * @param {Object} stats - 统计数据
 */
function updateStatistics(stats) {
    // 动画效果更新数字
    animateNumber('my-events-count', stats.my_events || 0);
    animateNumber('my-participations-count', stats.my_participations || 0);
    animateNumber('my-scores-count', stats.my_scores || 0);
    animateNumber('notifications-count', stats.notifications || 0);
}

/**
 * 数字动画效果
 * @param {string} elementId - 元素ID
 * @param {number} targetValue - 目标值
 */
function animateNumber(elementId, targetValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const startValue = 0;
    const duration = 1000; // 1秒
    const startTime = performance.now();
    
    function updateNumber(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // 使用缓动函数
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const currentValue = Math.round(startValue + (targetValue - startValue) * easeOutQuart);
        
        element.textContent = currentValue;
        
        if (progress < 1) {
            requestAnimationFrame(updateNumber);
        }
    }
    
    requestAnimationFrame(updateNumber);
}

/**
 * 加载最近活动
 */
function loadRecentActivities() {
    const activitiesContainer = document.getElementById('recent-activities');
    if (!activitiesContainer) return;
    
    // 模拟活动数据
    const activities = [
        {
            icon: 'fas fa-user-plus',
            iconColor: 'text-success',
            title: '新用户注册',
            description: '用户 "张三" 成功注册并加入了系统',
            time: '2分钟前'
        },
        {
            icon: 'fas fa-calendar-plus',
            iconColor: 'text-primary',
            title: '赛事创建',
            description: '2024年春季武术锦标赛已创建并发布',
            time: '15分钟前'
        },
        {
            icon: 'fas fa-star',
            iconColor: 'text-warning',
            title: '评分完成',
            description: '裁判李四完成了长拳项目的评分',
            time: '1小时前'
        },
        {
            icon: 'fas fa-trophy',
            iconColor: 'text-info',
            title: '成绩发布',
            description: '传统武术大赛成绩已公布',
            time: '2小时前'
        }
    ];
    
    let activitiesHtml = '';
    activities.forEach(activity => {
        activitiesHtml += `
            <div class="activity-item d-flex align-items-start">
                <div class="activity-icon ${activity.iconColor} me-3">
                    <i class="${activity.icon}"></i>
                </div>
                <div class="flex-grow-1">
                    <h6 class="mb-1">${activity.title}</h6>
                    <p class="text-muted mb-1 small">${activity.description}</p>
                    <small class="text-muted">${activity.time}</small>
                </div>
            </div>
        `;
    });
    
    activitiesContainer.innerHTML = activitiesHtml;
}

/**
 * 加载我的赛事
 */
function loadMyEvents() {
    fetch('/api/events/')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayMyEvents(data.events);
            }
        })
        .catch(error => {
            console.error('加载赛事数据失败:', error);
            displayMyEvents([]);
        });
}

/**
 * 显示我的赛事
 * @param {Array} events - 赛事数组
 */
function displayMyEvents(events) {
    const eventsContainer = document.getElementById('my-events');
    if (!eventsContainer) return;
    
    if (events.length === 0) {
        eventsContainer.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-calendar-times fa-3x text-muted mb-3"></i>
                <h6 class="text-muted">暂无赛事</h6>
                <p class="text-muted small">您还没有创建或参与任何赛事</p>
            </div>
        `;
        return;
    }
    
    let eventsHtml = '';
    events.slice(0, 3).forEach(event => {
        const statusColor = getEventStatusColor(event.status);
        const startDate = new Date(event.start_date).toLocaleDateString('zh-CN');
        
        eventsHtml += `
            <div class="event-item border-bottom pb-3 mb-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">${event.name}</h6>
                        <p class="text-muted mb-1 small">
                            <i class="fas fa-map-marker-alt me-1"></i>${event.location}
                        </p>
                        <p class="text-muted mb-0 small">
                            <i class="fas fa-calendar me-1"></i>${startDate}
                        </p>
                    </div>
                    <span class="badge bg-${statusColor}">${getEventStatusText(event.status)}</span>
                </div>
            </div>
        `;
    });
    
    eventsContainer.innerHTML = eventsHtml;
}

/**
 * 获取赛事状态颜色
 * @param {string} status - 状态
 * @returns {string} 颜色类名
 */
function getEventStatusColor(status) {
    const colors = {
        'draft': 'secondary',
        'published': 'primary',
        'ongoing': 'success',
        'completed': 'info',
        'cancelled': 'danger'
    };
    return colors[status] || 'secondary';
}

/**
 * 获取赛事状态文本
 * @param {string} status - 状态
 * @returns {string} 状态文本
 */
function getEventStatusText(status) {
    const texts = {
        'draft': '报名未开始',
        'published': '已发布',
        'ongoing': '进行中',
        'completed': '已完成',
        'cancelled': '已取消'
    };
    return texts[status] || '未知';
}

/**
 * 加载通知
 */
function loadNotifications() {
    const notificationsContainer = document.getElementById('notifications');
    if (!notificationsContainer) return;
    
    // 模拟通知数据
    const notifications = [
        {
            type: 'info',
            title: '系统维护通知',
            message: '系统将于本周末进行维护升级',
            time: '1小时前'
        },
        {
            type: 'success',
            title: '评分完成',
            message: '您的评分任务已完成',
            time: '3小时前'
        },
        {
            type: 'warning',
            title: '赛事提醒',
            message: '春季锦标赛将于明天开始',
            time: '1天前'
        }
    ];
    
    let notificationsHtml = '';
    notifications.forEach(notification => {
        const iconClass = getNotificationIcon(notification.type);
        const colorClass = getNotificationColor(notification.type);
        
        notificationsHtml += `
            <div class="notification-item">
                <div class="d-flex align-items-start">
                    <div class="notification-icon ${colorClass} me-3">
                        <i class="${iconClass}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <h6 class="mb-1">${notification.title}</h6>
                        <p class="text-muted mb-1 small">${notification.message}</p>
                        <small class="text-muted">${notification.time}</small>
                    </div>
                </div>
            </div>
        `;
    });
    
    notificationsContainer.innerHTML = notificationsHtml;
}

/**
 * 获取通知图标
 * @param {string} type - 通知类型
 * @returns {string} 图标类名
 */
function getNotificationIcon(type) {
    const icons = {
        'info': 'fas fa-info-circle',
        'success': 'fas fa-check-circle',
        'warning': 'fas fa-exclamation-triangle',
        'error': 'fas fa-times-circle'
    };
    return icons[type] || icons.info;
}

/**
 * 获取通知颜色
 * @param {string} type - 通知类型
 * @returns {string} 颜色类名
 */
function getNotificationColor(type) {
    const colors = {
        'info': 'text-info',
        'success': 'text-success',
        'warning': 'text-warning',
        'error': 'text-danger'
    };
    return colors[type] || colors.info;
}

/**
 * 根据用户角色更新UI
 */
function updateUIBasedOnRole() {
    const user = getCurrentUser();
    if (!user) return;
    
    // 根据角色显示/隐藏功能
    const roleBasedElements = document.querySelectorAll('[data-role]');
    roleBasedElements.forEach(element => {
        const requiredRole = element.getAttribute('data-role');
        if (!hasPermission(requiredRole)) {
            element.style.display = 'none';
        }
    });
}

/**
 * 刷新仪表板数据
 */
function refreshDashboard() {
    showMessage('正在刷新数据...', 'info');
    
    // 重新加载所有数据
    loadStatistics();
    loadRecentActivities();
    loadMyEvents();
    loadNotifications();
    
    setTimeout(() => {
        showMessage('数据刷新完成', 'success');
    }, 1000);
}

/**
 * 显示快速操作菜单
 */
function showQuickActions() {
    const user = getCurrentUser();
    if (!user) return;
    
    let actions = [];
    
    // 根据用户角色添加不同的快速操作
    if (hasPermission('admin')) {
        actions.push(
            { icon: 'fas fa-calendar-plus', text: '创建赛事', action: 'createEvent()' },
            { icon: 'fas fa-user-plus', text: '添加参赛者', action: 'addParticipant()' }
        );
    }
    
    if (hasPermission('judge')) {
        actions.push(
            { icon: 'fas fa-star', text: '开始评分', action: 'startScoring()' }
        );
    }
    
    actions.push(
        { icon: 'fas fa-trophy', text: '查看成绩', action: 'viewResults()' },
        { icon: 'fas fa-user-edit', text: '编辑资料', action: 'editProfile()' }
    );
    
    // 创建快速操作菜单HTML
    let actionsHtml = '';
    actions.forEach(action => {
        actionsHtml += `
            <button class="btn btn-outline-primary btn-sm me-2 mb-2" onclick="${action.action}">
                <i class="${action.icon} me-1"></i>${action.text}
            </button>
        `;
    });
    
    // 显示在模态框中
    const modalHtml = `
        <div class="modal fade" id="quickActionsModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-bolt me-2"></i>快速操作
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        ${actionsHtml}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除现有模态框
    const existingModal = document.getElementById('quickActionsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 添加新模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('quickActionsModal'));
    modal.show();
}

// ==================== 快速操作函数 ====================

function createEvent() {
    window.location.href = '/events';
}

function addParticipant() {
    window.location.href = '/participants';
}

function startScoring() {
    window.location.href = '/scoring';
}

function viewResults() {
    window.location.href = '/results';
}

function editProfile() {
    showProfile();
}

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', function() {
    // 检查登录状态
    const user = getCurrentUser();
    if (!user) {
        window.location.href = '/login';
        return;
    }
    
    // 初始化仪表板
    initDashboard();
});

// 导出函数供全局使用
window.refreshDashboard = refreshDashboard;
window.showQuickActions = showQuickActions;
window.loadRecentActivities = loadRecentActivities;
