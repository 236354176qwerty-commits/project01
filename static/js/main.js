/* 武术赛事管理系统 - 主JavaScript文件 */

// ==================== 全局变量 ====================
window.WushuSystem = {
    version: '1.0.0',
    debug: true,
    apiBase: '/api',
    currentUser: null,
    userRole: null,
    isLoggedIn: false
};

// ==================== 工具函数 ====================

/**
 * 显示消息提示 - 统一弹窗逻辑
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型 (success, error, warning, info)
 * @param {number} duration - 显示时长(毫秒)
 */
function showMessage(message, type = 'info', duration = 3000) {
    console.log('调用统一showMessage:', message, type);
    
    // 移除现有的弹窗
    const existingAlerts = document.querySelectorAll('.unified-message-alert');
    existingAlerts.forEach(alert => alert.remove());
    
    // 创建弹窗元素
    const alertDiv = document.createElement('div');
    alertDiv.className = 'unified-message-alert';
    
    // 设置图标和颜色
    let iconClass = 'fas fa-info-circle';
    let bgColor = 'rgba(23, 162, 184, 0.9)';
    
    if (type === 'success') {
        iconClass = 'fas fa-check-circle';
        bgColor = 'rgba(40, 167, 69, 0.9)';
    } else if (type === 'error') {
        iconClass = 'fas fa-exclamation-circle';
        bgColor = 'rgba(220, 53, 69, 0.9)';
    } else if (type === 'warning') {
        iconClass = 'fas fa-exclamation-triangle';
        bgColor = 'rgba(255, 193, 7, 0.9)';
    }
    
    // 设置HTML内容
    alertDiv.innerHTML = `
        <i class="${iconClass}" style="margin-right: 8px;"></i>
        <span class="unified-message-text">${message}</span>
        <button type="button" onclick="this.parentElement.remove()" style="
            background: none; 
            border: none; 
            color: white; 
            font-size: 18px; 
            margin-left: 15px; 
            cursor: pointer;
            opacity: 0.7;
        ">×</button>
    `;
    
    // 设置样式（页面中间偏下显示 - 直接设置避免闪烁）
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '65%';
    alertDiv.style.left = '50%';
    alertDiv.style.transform = 'translate(-50%, -50%)';
    alertDiv.style.background = bgColor;
    alertDiv.style.color = 'white';
    alertDiv.style.padding = '15px 20px';
    alertDiv.style.zIndex = '99999';
    alertDiv.style.borderRadius = '8px';
    alertDiv.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.2)';
    alertDiv.style.fontWeight = '500';
    alertDiv.style.minWidth = '300px';
    alertDiv.style.maxWidth = '500px';
    alertDiv.style.textAlign = 'center';
    alertDiv.style.fontFamily = "'Microsoft YaHei', sans-serif";
    
    // 添加到body
    document.body.appendChild(alertDiv);
    
    // 自动隐藏
    if (duration > 0) {
        setTimeout(() => {
            if (alertDiv && alertDiv.parentNode) {
                // 添加淡出动画
                alertDiv.style.animation = 'fadeOutScale 0.3s ease-in';
                setTimeout(() => {
                    if (alertDiv && alertDiv.parentNode) {
                        alertDiv.remove();
                    }
                }, 300);
            }
        }, duration);
    }

    return alertDiv;
}

/**
 * 获取消息图标
 * @param {string} type - 消息类型
 * @returns {string} 图标类名
 */
function getMessageIcon(type) {
    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };
    return icons[type] || icons.info;
}

/**
 * 格式化日期时间
 * @param {string|Date} date - 日期
 * @param {string} format - 格式类型
 * @returns {string} 格式化后的日期
 */
function formatDateTime(date, format = 'datetime') {
    if (!date) return '-';
    
    const d = new Date(date);
    if (isNaN(d.getTime())) return '-';
    
    const options = {
        date: { year: 'numeric', month: '2-digit', day: '2-digit' },
        time: { hour: '2-digit', minute: '2-digit' },
        datetime: { 
            year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit'
        }
    };
    
    return d.toLocaleString('zh-CN', options[format] || options.datetime);
}

/**
 * 防抖函数
 * @param {Function} func - 要防抖的函数
 * @param {number} wait - 等待时间
 * @returns {Function} 防抖后的函数
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 节流函数
 * @param {Function} func - 要节流的函数
 * @param {number} limit - 时间限制
 * @returns {Function} 节流后的函数
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * 深拷贝对象
 * @param {any} obj - 要拷贝的对象
 * @returns {any} 拷贝后的对象
 */
function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj.getTime());
    if (obj instanceof Array) return obj.map(item => deepClone(item));
    if (typeof obj === 'object') {
        const clonedObj = {};
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                clonedObj[key] = deepClone(obj[key]);
            }
        }
        return clonedObj;
    }
}

/**
 * 生成UUID
 * @returns {string} UUID字符串
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * 验证邮箱格式
 * @param {string} email - 邮箱地址
 * @returns {boolean} 是否有效
 */
function validateEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

/**
 * 验证手机号格式
 * @param {string} phone - 手机号
 * @returns {boolean} 是否有效
 */
function validatePhone(phone) {
    const regex = /^1[3-9]\d{9}$/;
    return regex.test(phone);
}

/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的大小
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ==================== AJAX 封装 ====================

/**
 * AJAX请求封装
 * @param {Object} options - 请求选项
 * @returns {Promise} Promise对象
 */
function ajaxRequest(options) {
    const defaults = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        timeout: 30000
    };
    
    const config = Object.assign({}, defaults, options);
    
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        // 设置超时
        xhr.timeout = config.timeout;
        
        // 打开连接
        xhr.open(config.method, config.url, true);
        
        // 设置请求头
        for (const header in config.headers) {
            xhr.setRequestHeader(header, config.headers[header]);
        }
        
        // 处理响应
        xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    resolve(response);
                } catch (e) {
                    resolve(xhr.responseText);
                }
            } else {
                reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
            }
        };
        
        // 处理错误
        xhr.onerror = function() {
            reject(new Error('Network Error'));
        };
        
        xhr.ontimeout = function() {
            reject(new Error('Request Timeout'));
        };
        
        // 发送请求
        if (config.data) {
            if (typeof config.data === 'object') {
                xhr.send(JSON.stringify(config.data));
            } else {
                xhr.send(config.data);
            }
        } else {
            xhr.send();
        }
    });
}

// ==================== 用户认证相关 ====================

/**
 * 登出用户 - 此函数已移至base.html中，使用自定义模态框
 * 保留此处以避免引用错误，但实际功能在base.html中实现
 */
// function logout() {
//     // 此函数已在base.html中重新实现，使用自定义模态框
// }

/**
 * 显示个人资料模态框
 */
function showProfile() {
    // 模拟加载用户信息
    const username = sessionStorage.getItem('username') || '用户';
    
    // 模拟用户数据
    const mockUser = {
        real_name: username,
        email: username.toLowerCase() + '@example.com',
        phone: '13800138000'
    };
    
    $('#realName').val(mockUser.real_name);
    $('#email').val(mockUser.email);
    $('#phone').val(mockUser.phone || '');
    $('#profileModal').modal('show');
}

/**
 * 更新个人资料
 */
function updateProfile() {
    const formData = {
        real_name: $('#realName').val().trim(),
        email: $('#email').val().trim(),
        phone: $('#phone').val().trim()
    };
    
    // 验证数据
    if (!formData.real_name) {
        showMessage('请输入真实姓名', 'warning');
        return;
    }
    
    if (!validateEmail(formData.email)) {
        showMessage('请输入有效的邮箱地址', 'warning');
        return;
    }
    
    if (formData.phone && !validatePhone(formData.phone)) {
        showMessage('请输入有效的手机号', 'warning');
        return;
    }
    
    // 模拟更新操作
    setTimeout(function() {
        showMessage('个人资料更新成功', 'success');
        $('#profileModal').modal('hide');
    }, 800);
}

/**
 * 显示修改密码模态框
 */
function changePassword() {
    $('#passwordForm')[0].reset();
    $('#passwordModal').modal('show');
}

/**
 * 更新密码
 */
function updatePassword() {
    const oldPassword = $('#oldPassword').val();
    const newPassword = $('#newPassword').val();
    const confirmPassword = $('#confirmPassword').val();
    
    // 验证数据
    if (!oldPassword) {
        showMessage('请输入原密码', 'warning');
        return;
    }
    
    if (!newPassword) {
        showMessage('请输入新密码', 'warning');
        return;
    }
    
    if (newPassword.length < 6 || newPassword.length > 20) {
        showMessage('新密码必须为6-20个字符', 'warning');
        return;
    }
    
    // 检查是否包含数字
    if (!/\d/.test(newPassword)) {
        showMessage('新密码必须包含数字', 'warning');
        return;
    }
    
    // 检查是否包含小写字母
    if (!/[a-z]/.test(newPassword)) {
        showMessage('新密码必须包含小写字母', 'warning');
        return;
    }
    
    // 检查是否包含汉字
    if (/[\u4e00-\u9fa5]/.test(newPassword)) {
        showMessage('新密码不能包含汉字', 'warning');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showMessage('两次输入的密码不一致', 'warning');
        return;
    }
    
    // 发送AJAX请求到后端API
    $.ajax({
        url: '/api/change_password',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            currentPassword: oldPassword,
            newPassword: newPassword,
            confirmNewPassword: confirmPassword
        }),
        success: function(response) {
            if (response.success) {
                showMessage(response.message, 'success');
                $('#profileModal').modal('hide');
                // 清空密码输入框
                $('#oldPassword').val('');
                $('#newPassword').val('');
                $('#confirmPassword').val('');
            } else {
                showMessage(response.message, 'error');
            }
        },
        error: function() {
            showMessage('网络错误，请重试', 'error');
        }
    });
}

// ==================== 表单验证 ====================

/**
 * 表单验证器
 */
class FormValidator {
    constructor(form) {
        this.form = form;
        this.rules = {};
        this.messages = {};
    }
    
    /**
     * 添加验证规则
     * @param {string} field - 字段名
     * @param {Array} rules - 规则数组
     * @param {string} message - 错误消息
     */
    addRule(field, rules, message) {
        this.rules[field] = rules;
        this.messages[field] = message;
    }
    
    /**
     * 验证表单
     * @returns {boolean} 验证结果
     */
    validate() {
        let isValid = true;
        
        for (const field in this.rules) {
            const input = this.form.querySelector(`[name="${field}"]`);
            if (!input) continue;
            
            const value = input.value.trim();
            const rules = this.rules[field];
            
            // 清除之前的错误状态
            input.classList.remove('is-invalid');
            const feedback = input.parentNode.querySelector('.invalid-feedback');
            if (feedback) feedback.remove();
            
            // 验证规则
            for (const rule of rules) {
                if (!this.validateRule(value, rule)) {
                    this.showFieldError(input, this.messages[field]);
                    isValid = false;
                    break;
                }
            }
        }
        
        return isValid;
    }
    
    /**
     * 验证单个规则
     * @param {string} value - 值
     * @param {string} rule - 规则
     * @returns {boolean} 验证结果
     */
    validateRule(value, rule) {
        switch (rule) {
            case 'required':
                return value.length > 0;
            case 'email':
                return validateEmail(value);
            case 'phone':
                return validatePhone(value);
            case 'min:6':
                return value.length >= 6;
            default:
                return true;
        }
    }
    
    /**
     * 显示字段错误
     * @param {Element} input - 输入框
     * @param {string} message - 错误消息
     */
    showFieldError(input, message) {
        input.classList.add('is-invalid');
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = message;
        input.parentNode.appendChild(feedback);
    }
}

// ==================== 数据表格 ====================

/**
 * 数据表格类
 */
class DataTable {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            pageSize: 10,
            sortable: true,
            searchable: true,
            ...options
        };
        this.data = [];
        this.filteredData = [];
        this.currentPage = 1;
        this.sortColumn = null;
        this.sortDirection = 'asc';
        this.searchTerm = '';
    }
    
    /**
     * 设置数据
     * @param {Array} data - 数据数组
     */
    setData(data) {
        this.data = data;
        this.filteredData = [...data];
        this.render();
    }
    
    /**
     * 搜索数据
     * @param {string} term - 搜索词
     */
    search(term) {
        this.searchTerm = term.toLowerCase();
        this.filteredData = this.data.filter(item => {
            return Object.values(item).some(value => 
                String(value).toLowerCase().includes(this.searchTerm)
            );
        });
        this.currentPage = 1;
        this.render();
    }
    
    /**
     * 排序数据
     * @param {string} column - 列名
     */
    sort(column) {
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }
        
        this.filteredData.sort((a, b) => {
            const aVal = a[column];
            const bVal = b[column];
            
            if (this.sortDirection === 'asc') {
                return aVal > bVal ? 1 : -1;
            } else {
                return aVal < bVal ? 1 : -1;
            }
        });
        
        this.render();
    }
    
    /**
     * 渲染表格
     */
    render() {
        // 实现表格渲染逻辑
        console.log('Rendering table with', this.filteredData.length, 'items');
    }
}

// ==================== 文件上传 ====================

/**
 * 文件上传器
 */
class FileUploader {
    constructor(input, options = {}) {
        this.input = input;
        this.options = {
            maxSize: 10 * 1024 * 1024, // 10MB
            allowedTypes: ['image/jpeg', 'image/png', 'image/gif'],
            multiple: false,
            ...options
        };
        this.init();
    }
    
    /**
     * 初始化
     */
    init() {
        this.input.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });
    }
    
    /**
     * 处理文件
     * @param {FileList} files - 文件列表
     */
    handleFiles(files) {
        for (const file of files) {
            if (this.validateFile(file)) {
                this.uploadFile(file);
            }
        }
    }
    
    /**
     * 验证文件
     * @param {File} file - 文件对象
     * @returns {boolean} 验证结果
     */
    validateFile(file) {
        // 检查文件大小
        if (file.size > this.options.maxSize) {
            showMessage(`文件 ${file.name} 太大，最大允许 ${formatFileSize(this.options.maxSize)}`, 'error');
            return false;
        }
        
        // 检查文件类型
        if (!this.options.allowedTypes.includes(file.type)) {
            showMessage(`文件 ${file.name} 类型不支持`, 'error');
            return false;
        }
        
        return true;
    }
    
    /**
     * 上传文件
     * @param {File} file - 文件对象
     */
    uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        // 创建进度条
        const progressId = 'upload-' + Date.now();
        this.showProgress(progressId, file.name);
        
        $.ajax({
            url: '/api/upload',
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            xhr: () => {
                const xhr = new XMLHttpRequest();
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        this.updateProgress(progressId, percentComplete);
                    }
                });
                return xhr;
            },
            success: (response) => {
                this.hideProgress(progressId);
                if (response.success) {
                    showMessage(`文件 ${file.name} 上传成功`, 'success');
                    if (this.options.onSuccess) {
                        this.options.onSuccess(response.data);
                    }
                } else {
                    showMessage(`文件 ${file.name} 上传失败: ${response.message}`, 'error');
                }
            },
            error: () => {
                this.hideProgress(progressId);
                showMessage(`文件 ${file.name} 上传失败`, 'error');
            }
        });
    }
    
    /**
     * 显示进度条
     * @param {string} id - 进度条ID
     * @param {string} filename - 文件名
     */
    showProgress(id, filename) {
        const progressHtml = `
            <div id="${id}" class="upload-progress mb-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <small class="text-muted">${filename}</small>
                    <small class="text-muted">0%</small>
                </div>
                <div class="progress" style="height: 4px;">
                    <div class="progress-bar" role="progressbar" style="width: 0%"></div>
                </div>
            </div>
        `;
        
        let container = document.getElementById('upload-progress-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'upload-progress-container';
            this.input.parentNode.appendChild(container);
        }
        
        container.insertAdjacentHTML('beforeend', progressHtml);
    }
    
    /**
     * 更新进度
     * @param {string} id - 进度条ID
     * @param {number} percent - 进度百分比
     */
    updateProgress(id, percent) {
        const progressElement = document.getElementById(id);
        if (progressElement) {
            const progressBar = progressElement.querySelector('.progress-bar');
            const percentText = progressElement.querySelector('.text-muted:last-child');
            
            progressBar.style.width = percent + '%';
            percentText.textContent = Math.round(percent) + '%';
        }
    }
    
    /**
     * 隐藏进度条
     * @param {string} id - 进度条ID
     */
    hideProgress(id) {
        const progressElement = document.getElementById(id);
        if (progressElement) {
            setTimeout(() => {
                progressElement.remove();
            }, 1000);
        }
    }
}

// ==================== 初始化 ====================

$(document).ready(function() {
    // 初始化工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 初始化弹出框
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // 自动隐藏警告框
    $('.alert').each(function() {
        const alert = this;
        setTimeout(() => {
            $(alert).fadeOut();
        }, 5000);
    });
    
    // 表单验证增强
    $('form').on('submit', function(e) {
        const form = this;
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                input.classList.add('is-invalid');
                e.preventDefault();
            } else {
                input.classList.remove('is-invalid');
            }
        });
    });
    
    // 数字输入框增强
    $('input[type="number"]').on('input', function() {
        const min = parseFloat(this.min);
        const max = parseFloat(this.max);
        const value = parseFloat(this.value);
        
        if (!isNaN(min) && value < min) {
            this.value = min;
        }
        if (!isNaN(max) && value > max) {
            this.value = max;
        }
    });
    
    // 搜索框防抖
    $('input[type="search"], .search-input').on('input', debounce(function() {
        const searchTerm = this.value.trim();
        if (typeof window.handleSearch === 'function') {
            window.handleSearch(searchTerm);
        }
    }, 300));
    
    // 返回顶部按钮
    const backToTop = $('<button class="btn btn-primary btn-floating position-fixed" id="back-to-top" style="bottom: 20px; right: 20px; display: none; z-index: 1000;"><i class="fas fa-arrow-up"></i></button>');
    $('body').append(backToTop);
    
    $(window).scroll(throttle(function() {
        if ($(this).scrollTop() > 300) {
            $('#back-to-top').fadeIn();
        } else {
            $('#back-to-top').fadeOut();
        }
    }, 100));
    
    $('#back-to-top').click(function() {
        $('html, body').animate({scrollTop: 0}, 500);
    });
});

// ==================== 导出到全局 ====================
window.showMessage = showMessage;
window.formatDateTime = formatDateTime;
window.debounce = debounce;
window.throttle = throttle;
window.validateEmail = validateEmail;
window.validatePhone = validatePhone;
// window.logout = logout; // 已移至base.html中实现
window.showProfile = showProfile;
window.updateProfile = updateProfile;
window.changePassword = changePassword;
window.updatePassword = updatePassword;
window.FormValidator = FormValidator;
window.DataTable = DataTable;
window.FileUploader = FileUploader;
