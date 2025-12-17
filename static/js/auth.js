/* 武术赛事管理系统 - 认证相关JavaScript */

// ==================== 注册验证规则 ====================

/**
 * 验证账号格式
 * @param {string} username - 账号
 * @returns {Object} 验证结果
 */
function validateUsername(username) {
    if (!username || username.length < 6) {
        return { valid: false, message: '账号必须至少6个字符' };
    }
    return { valid: true, message: '' };
}

/**
 * 验证密码格式
 * @param {string} password - 密码
 * @returns {Object} 验证结果
 */
function validatePassword(password) {
    if (!password) {
        return { valid: false, message: '密码不能为空' };
    }
    
    if (password.length < 6 || password.length > 20) {
        return { valid: false, message: '密码长度必须在6-20个字符之间' };
    }
    
    // 检查是否包含汉字
    const chineseRegex = /[\u4e00-\u9fa5]/;
    if (chineseRegex.test(password)) {
        return { valid: false, message: '密码不能包含汉字' };
    }
    
    // 检查是否同时包含数字和小写字母
    const hasNumber = /\d/.test(password);
    const hasLowercase = /[a-z]/.test(password);
    
    if (!hasNumber || !hasLowercase) {
        return { valid: false, message: '密码必须同时包含数字和小写英文字母' };
    }
    
    return { valid: true, message: '密码格式正确' };
}

/**
 * 验证运动队名称
 * @param {string} teamName - 运动队名称
 * @returns {Object} 验证结果
 */
function validateTeamName(teamName) {
    if (!teamName || teamName.length < 10) {
        return { valid: false, message: '运动队名称必须至少10个字符' };
    }
    
    // 敏感词列表
    const sensitiveWords = [
        '政治', '反动', '暴力', '色情', '赌博', '毒品', 
        '法轮功', '台独', '藏独', '疆独', '港独',
        '习近平', '毛泽东', '邓小平', '江泽民', '胡锦涛',
        '共产党', '国民党', '民进党', '自由党',
        '六四', '天安门', '文革', '大跃进'
    ];
    
    for (const word of sensitiveWords) {
        if (teamName.includes(word)) {
            return { valid: false, message: '运动队名称包含敏感词汇，请重新输入' };
        }
    }
    
    return { valid: true, message: '运动队名称格式正确' };
}

/**
 * 验证邮箱格式
 * @param {string} email - 邮箱
 * @returns {Object} 验证结果
 */
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRegex.test(email)) {
        return { valid: false, message: '请输入有效的邮箱地址' };
    }
    return { valid: true, message: '邮箱格式正确' };
}

/**
 * 验证手机号格式
 * @param {string} phone - 手机号
 * @returns {Object} 验证结果
 */
function validatePhone(phone) {
    const phoneRegex = /^1[3-9]\d{9}$/;
    if (!phone || !phoneRegex.test(phone)) {
        return { valid: false, message: '手机号必须是11位数字，且以1开头' };
    }
    return { valid: true, message: '手机号格式正确' };
}

/**
 * 验证确认密码
 * @param {string} password - 原密码
 * @param {string} confirmPassword - 确认密码
 * @returns {Object} 验证结果
 */
function validateConfirmPassword(password, confirmPassword) {
    if (password !== confirmPassword) {
        return { valid: false, message: '两次输入的密码不一致' };
    }
    return { valid: true, message: '密码确认正确' };
}

// ==================== 实时验证功能 ====================

/**
 * 显示验证结果
 * @param {string} fieldId - 字段ID
 * @param {Object} result - 验证结果
 */
function showValidationResult(fieldId, result) {
    const field = document.getElementById(fieldId);
    const feedback = document.getElementById(fieldId + 'Feedback');
    
    if (!field || !feedback) return;
    
    // 清除之前的样式
    field.classList.remove('is-valid', 'is-invalid');
    
    if (result.valid) {
        field.classList.add('is-valid');
        feedback.className = 'valid-feedback';
        feedback.textContent = result.message;
        feedback.style.display = 'block';
    } else {
        field.classList.add('is-invalid');
        feedback.className = 'invalid-feedback';
        feedback.textContent = result.message;
        feedback.style.display = 'block';
    }
}

/**
 * 绑定实时验证事件
 */
function bindValidationEvents() {
    // 账号验证
    const usernameField = document.getElementById('username');
    if (usernameField) {
        usernameField.addEventListener('blur', function() {
            const result = validateUsername(this.value);
            showValidationResult('username', result);
        });
    }
    
    // 密码验证
    const passwordField = document.getElementById('password');
    if (passwordField) {
        passwordField.addEventListener('blur', function() {
            const result = validatePassword(this.value);
            showValidationResult('password', result);
            
            // 同时验证确认密码
            const confirmPasswordField = document.getElementById('confirmPassword');
            if (confirmPasswordField && confirmPasswordField.value) {
                const confirmResult = validateConfirmPassword(this.value, confirmPasswordField.value);
                showValidationResult('confirmPassword', confirmResult);
            }
        });
    }
    
    // 确认密码验证
    const confirmPasswordField = document.getElementById('confirmPassword');
    if (confirmPasswordField) {
        confirmPasswordField.addEventListener('blur', function() {
            const passwordValue = passwordField ? passwordField.value : '';
            const result = validateConfirmPassword(passwordValue, this.value);
            showValidationResult('confirmPassword', result);
        });
    }
    
    // 运动队名称验证
    const teamNameField = document.getElementById('teamName');
    if (teamNameField) {
        teamNameField.addEventListener('blur', function() {
            const result = validateTeamName(this.value);
            showValidationResult('teamName', result);
        });
    }
    
    // 邮箱验证
    const emailField = document.getElementById('email');
    if (emailField) {
        emailField.addEventListener('blur', function() {
            const result = validateEmail(this.value);
            showValidationResult('email', result);
        });
    }
    
    // 手机号验证
    const phoneField = document.getElementById('phone');
    if (phoneField) {
        phoneField.addEventListener('blur', function() {
            const result = validatePhone(this.value);
            showValidationResult('phone', result);
        });
    }
}

// ==================== 注册表单提交 ====================

/**
 * 处理注册表单提交
 * @param {Event} event - 表单提交事件
 */
function handleRegisterSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    // 获取表单数据
    const username = formData.get('username');
    const password = formData.get('password');
    const confirmPassword = formData.get('confirmPassword');
    const teamName = formData.get('teamName');
    const email = formData.get('email');
    const phone = formData.get('phone');
    const captcha = formData.get('captcha');
    
    // 验证所有字段
    const validations = [
        validateUsername(username),
        validatePassword(password),
        validateConfirmPassword(password, confirmPassword),
        validateTeamName(teamName),
        validateEmail(email),
        validatePhone(phone)
    ];
    
    // 验证码验证
    if (!captcha) {
        showMessage('请输入验证码', 'error');
        return;
    }
    
    // 检查是否有验证失败的字段
    const hasErrors = validations.some(v => !v.valid);
    
    if (hasErrors) {
        showMessage('请检查并修正表单中的错误', 'error');
        return;
    }
    
    // 显示加载状态
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>注册中...';
    
    // 发送注册请求到后端API
    fetch('/api/auth/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            password: password,
            nickname: teamName,
            email: email,
            phone: phone,
            captcha: captcha
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
            
            // 重置表单
            form.reset();
            
            // 清除验证状态
            const fields = form.querySelectorAll('.form-control');
            fields.forEach(field => {
                field.classList.remove('is-valid', 'is-invalid');
            });
            
            const feedbacks = form.querySelectorAll('.valid-feedback, .invalid-feedback');
            feedbacks.forEach(feedback => {
                feedback.style.display = 'none';
            });
            
            // 关闭注册模态框
            const registerModal = bootstrap.Modal.getInstance(document.getElementById('registerModal'));
            if (registerModal) {
                registerModal.hide();
            }
            
            // 3秒后提示登录
            setTimeout(() => {
                showMessage('请使用新账号登录', 'info');
            }, 2000);
        } else {
            showMessage(data.message, 'error');
            // 如果是验证码错误或注册未成功，刷新验证码
            if (data.message.includes('验证码') || !data.success) {
                refreshCaptcha();
            }
        }
    })
    .catch(error => {
        console.error('注册错误:', error);
        showMessage('注册失败，请稍后重试', 'error');
        // 注册失败时刷新验证码
        refreshCaptcha();
    })
    .finally(() => {
        // 恢复按钮状态
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    });
}

// ==================== 登录功能 ====================

/**
 * 处理登录表单提交
 * @param {Event} event - 表单提交事件
 */
function handleLoginSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    const username = formData.get('username');
    const password = formData.get('password');
    
    if (!username || !password) {
        showMessage('请输入账号和密码', 'warning');
        return;
    }
    
    // 显示加载状态
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>登录中...';
    
    // 发送登录请求到后端API
    fetch('/api/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            password: password
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 保存用户信息到sessionStorage
            sessionStorage.setItem('currentUser', JSON.stringify(data.user));
            
            showMessage(data.message, 'success');
            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('登录错误:', error);
        showMessage('登录失败，请稍后重试', 'error');
    })
    .finally(() => {
        // 恢复按钮状态
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    });
}

// ==================== 权限管理 ====================

/**
 * 获取当前用户信息
 * @returns {Object|null} 用户信息
 */
function getCurrentUser() {
    const userStr = sessionStorage.getItem('currentUser');
    return userStr ? JSON.parse(userStr) : null;
}

/**
 * 检查用户权限
 * @param {string} requiredRole - 需要的角色
 * @returns {boolean} 是否有权限
 */
function hasPermission(requiredRole) {
    const user = getCurrentUser();
    if (!user) return false;
    
    const roleHierarchy = {
        'super_admin': 4,
        'admin': 3,
        'judge': 2,
        'user': 1
    };
    
    const userLevel = roleHierarchy[user.role] || 0;
    const requiredLevel = roleHierarchy[requiredRole] || 0;
    
    return userLevel >= requiredLevel;
}

/**
 * 更新页面用户信息显示
 */
function updateUserDisplay() {
    const user = getCurrentUser();
    
    // 更新导航栏用户信息
    const userInfo = document.getElementById('userInfo');
    if (userInfo && user) {
        userInfo.innerHTML = `
            <span class="me-2">当前身份：${user.roleName}</span>
            <span class="badge bg-primary">${user.username}</span>
        `;
    }
    
    // 根据权限显示/隐藏功能
    const roleBasedElements = document.querySelectorAll('[data-role]');
    roleBasedElements.forEach(element => {
        const requiredRole = element.getAttribute('data-role');
        if (!hasPermission(requiredRole)) {
            element.style.display = 'none';
        }
    });
}

// ==================== 消息提示功能 ====================

/**
 * 显示消息提示
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型
 */
function showMessage(message, type = 'info') {
    // 移除现有消息
    const existingMessages = document.querySelectorAll('.alert-message');
    existingMessages.forEach(msg => msg.remove());
    
    // 创建消息元素
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show alert-message`;
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '60%';
    alertDiv.style.left = '50%';
    alertDiv.style.transform = 'translate(-50%, -50%)';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    alertDiv.style.textAlign = 'center';
    
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // 自动消失
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', function() {
    // 绑定验证事件
    bindValidationEvents();
    
    // 绑定注册表单提交事件
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegisterSubmit);
    }
    
    // 绑定登录表单提交事件
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLoginSubmit);
    }
    
    // 更新用户信息显示
    updateUserDisplay();
});

// 刷新验证码函数
function refreshCaptcha() {
    // 刷新验证码图片
    const captchaImage = document.getElementById('captchaImage');
    if (captchaImage) {
        const timestamp = new Date().getTime();
        captchaImage.src = '/api/auth/captcha?t=' + timestamp;
    }
}

// 导出函数供全局使用
window.validateUsername = validateUsername;
window.validatePassword = validatePassword;
window.validateTeamName = validateTeamName;
window.validateEmail = validateEmail;
window.validatePhone = validatePhone;
window.getCurrentUser = getCurrentUser;
window.hasPermission = hasPermission;
window.showMessage = showMessage;
window.refreshCaptcha = refreshCaptcha;
