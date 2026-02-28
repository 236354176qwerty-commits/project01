/**
 * 公共工具函数库 - 从模板中提取的高频复用函数
 * 所有模板通过 base.html 统一引入，避免重复定义
 */

// ==================== 日期格式化 ====================

function formatDate(dateString) {
    if (!dateString) return '待定';
    var d = new Date(dateString);
    if (isNaN(d.getTime())) return '-';
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
}

function formatDateTime(dateString) {
    if (!dateString) return '待定';
    var d = new Date(dateString);
    if (isNaN(d.getTime())) return '-';
    return d.toLocaleString('zh-CN');
}

function formatDateTimeShort(dateString) {
    if (!dateString) return '待定';
    var d = new Date(dateString);
    if (isNaN(d.getTime())) return '-';
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    var h = String(d.getHours()).padStart(2, '0');
    var min = String(d.getMinutes()).padStart(2, '0');
    return m + '月' + day + '日 ' + h + ':' + min;
}

function formatDateTimeForInput(dateString) {
    if (!dateString) return '';
    var d = new Date(dateString);
    if (isNaN(d.getTime())) return '';
    return d.toISOString().slice(0, 16);
}

// ==================== 身份证工具 ====================

function extractGenderFromIdCard(idCard) {
    if (!idCard || idCard.length < 17) return '';
    var genderDigit = parseInt(idCard.charAt(16));
    if (isNaN(genderDigit)) return '';
    return genderDigit % 2 === 1 ? '男' : '女';
}

function calculateAgeFromIdCard(idCard) {
    if (!idCard || idCard.length < 14) return '';
    var year = parseInt(idCard.substring(6, 10));
    var month = parseInt(idCard.substring(10, 12)) - 1;
    var day = parseInt(idCard.substring(12, 14));
    if (isNaN(year) || isNaN(month) || isNaN(day)) return '';
    var birth = new Date(year, month, day);
    var today = new Date();
    var age = today.getFullYear() - birth.getFullYear();
    var mDiff = today.getMonth() - birth.getMonth();
    if (mDiff < 0 || (mDiff === 0 && today.getDate() < birth.getDate())) age--;
    return age;
}

function maskIdCard(idCard) {
    if (!idCard || idCard.length < 8) return idCard || '-';
    return idCard.substring(0, 6) + '****' + idCard.substring(idCard.length - 4);
}

// ==================== 文本工具 ====================

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// ==================== 赛事状态 ====================

function getStatusText(status) {
    var m = {
        'draft': '报名未开始',
        'published': '已发布',
        'registration': '报名中',
        'ongoing': '进行中',
        'completed': '已结束',
        'cancelled': '已取消'
    };
    return m[status] || status || '-';
}

function getStatusBadgeClass(status) {
    var m = {
        'draft': 'bg-secondary',
        'published': 'bg-info',
        'registration': 'bg-primary',
        'ongoing': 'bg-success',
        'completed': 'bg-dark',
        'cancelled': 'bg-danger'
    };
    return m[status] || 'bg-secondary';
}

// ==================== 全局导出 ====================

window.formatDate = formatDate;
window.formatDateTime = formatDateTime;
window.formatDateTimeShort = formatDateTimeShort;
window.formatDateTimeForInput = formatDateTimeForInput;
window.extractGenderFromIdCard = extractGenderFromIdCard;
window.calculateAgeFromIdCard = calculateAgeFromIdCard;
window.maskIdCard = maskIdCard;
window.truncateText = truncateText;
window.getStatusText = getStatusText;
window.getStatusBadgeClass = getStatusBadgeClass;
