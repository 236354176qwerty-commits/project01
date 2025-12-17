/**
 * 武术赛事管理系统 - 比赛项目分类加载器
 * 统一管理项目分类数据，供多个页面使用
 */

// 全局项目分类数据缓存
let competitionCategoriesData = null;

/**
 * 从API加载项目分类数据
 * @returns {Promise<Object>} 分类数据
 */
async function loadCompetitionCategories() {
    if (competitionCategoriesData) {
        return competitionCategoriesData;
    }
    
    try {
        const response = await fetch('/api/categories/competition');
        const data = await response.json();
        
        if (data.success) {
            competitionCategoriesData = data;
            return data;
        } else {
            throw new Error(data.message || '加载项目分类失败');
        }
    } catch (error) {
        console.error('加载项目分类失败:', error);
        throw error;
    }
}

/**
 * 渲染项目分类到指定容器
 * @param {string} containerId - 容器ID
 * @param {Object} options - 配置选项
 */
async function renderCompetitionCategories(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`容器 #${containerId} 不存在`);
        return;
    }
    
    // 默认选项
    const config = {
        mode: 'event_selection', // 或 'add_player'
        enableSelection: true,
        enableToggle: true,
        ...options
    };
    
    try {
        const data = await loadCompetitionCategories();
        
        if (!data.categories || data.categories.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">暂无项目分类</p>';
            return;
        }
        
        let html = '';
        
        data.categories.forEach(category => {
            html += renderMainCategory(category, config);
        });
        
        container.innerHTML = html;
        
        // 绑定事件
        if (config.enableToggle) {
            bindToggleEvents(container);
        }
        
        console.log('项目分类渲染完成');
        
    } catch (error) {
        console.error('渲染项目分类失败:', error);
        container.innerHTML = '<p class="text-danger text-center">加载项目分类失败，请刷新页面重试</p>';
    }
}

/**
 * 渲染主分类（第一层）
 */
function renderMainCategory(category, config) {
    let html = '<div class="category-level-1">';
    html += `<div class="category-item category-main" onclick="toggleCategory(this)">`;
    html += `<i class="fas fa-chevron-down category-icon"></i>`;
    html += `<h6><i class="fas ${category.icon}"></i>${category.name}</h6>`;
    html += `</div>`;
    html += `<div class="category-level-2" style="display: none;">`;
    
    if (category.subcategories && category.subcategories.length > 0) {
        category.subcategories.forEach(subcategory => {
            html += renderSubCategory(category.id, subcategory, config);
        });
    }
    
    html += `</div></div>`;
    return html;
}

/**
 * 渲染子分类（第二层）
 */
function renderSubCategory(mainCategoryId, subcategory, config) {
    let html = `<div class="category-item category-sub" onclick="toggleCategory(this)">`;
    html += `<i class="fas fa-chevron-right category-icon"></i>`;
    html += `<span>${subcategory.name}</span>`;
    html += `</div>`;
    html += `<div class="category-level-3" style="display: none;">`;
    
    if (subcategory.items && subcategory.items.length > 0) {
        subcategory.items.forEach((item, index) => {
            const itemId = `category-${mainCategoryId}-${subcategory.id.split('-')[1]}-${index + 1}`;
            html += renderCategoryItem(itemId, item);
        });
    }
    
    // 渲染"其他"选项
    if (subcategory.has_other) {
        if (subcategory.other_options) {
            // 多个"其他"选项（器械类）
            subcategory.other_options.forEach(otherOption => {
                const otherId = `category-${mainCategoryId}-${subcategory.id.split('-')[1]}-${otherOption.key}`;
                const inputId = `input-${mainCategoryId}-${subcategory.id.split('-')[1]}-${otherOption.key}`;
                html += renderOtherCategoryItem(otherId, inputId, otherOption.label);
            });
        } else {
            // 单个"其他"选项（拳术类）
            const otherId = `category-${mainCategoryId}-${subcategory.id.split('-')[1]}-other`;
            const inputId = `input-${mainCategoryId}-${subcategory.id.split('-')[1]}-other`;
            html += renderOtherCategoryItem(otherId, inputId, subcategory.other_label);
        }
    }
    
    html += `</div>`;
    return html;
}

/**
 * 渲染具体项目（第三层）
 */
function renderCategoryItem(itemId, itemName) {
    return `
        <div class="category-item category-detail">
            <input type="checkbox" id="${itemId}">
            <label for="${itemId}">${itemName}</label>
        </div>
    `;
}

/**
 * 渲染"其他"项目（带输入框）
 */
function renderOtherCategoryItem(otherId, inputId, label) {
    return `
        <div class="category-item category-detail" style="display: flex; align-items: center; gap: 10px;">
            <div>
                <input type="checkbox" id="${otherId}">
                <label for="${otherId}">${label}</label>
            </div>
            <input type="text" id="${inputId}" placeholder="请填写套路名称" 
                   style="flex: 1; padding: 5px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;">
        </div>
    `;
}

/**
 * 绑定展开/折叠事件
 */
function bindToggleEvents(container) {
    // 事件已通过 onclick 属性绑定
    console.log('项目分类事件绑定完成');
}

/**
 * 展开/折叠分类（全局函数）
 */
function toggleCategory(element) {
    const icon = element.querySelector('.category-icon');
    const nextSibling = element.nextElementSibling;
    
    if (nextSibling && nextSibling.classList.contains('category-level-2') || 
        nextSibling.classList.contains('category-level-3')) {
        
        if (nextSibling.style.display === 'none') {
            nextSibling.style.display = 'block';
            icon.classList.remove('fa-chevron-right');
            icon.classList.add('fa-chevron-down');
        } else {
            nextSibling.style.display = 'none';
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-right');
        }
    }
}

/**
 * 本地版本的toggle（兼容旧代码）
 */
function toggleCategoryLocal(element) {
    toggleCategory(element);
}

/**
 * 获取所有选中的项目
 * @returns {Array<string>} 选中的项目名称列表
 */
function getSelectedCategories() {
    const selected = [];
    const checkedBoxes = document.querySelectorAll('input[type="checkbox"][id^="category-"]:checked');
    
    checkedBoxes.forEach(checkbox => {
        const label = document.querySelector(`label[for="${checkbox.id}"]`);
        if (label) {
            let itemName = label.textContent.trim();
            
            // 如果是"其他"选项，检查是否有填写内容
            if (checkbox.id.includes('-other')) {
                const inputId = checkbox.id.replace('category-', 'input-');
                const input = document.getElementById(inputId);
                if (input && input.value.trim()) {
                    itemName += '：' + input.value.trim();
                }
            }
            
            selected.push(itemName);
        }
    });
    
    return selected;
}

/**
 * 验证是否至少选择了一个项目
 * @returns {boolean}
 */
function validateCategorySelection() {
    const selected = getSelectedCategories();
    return selected.length > 0;
}

/**
 * 搜索项目分类
 * @param {string} containerId - 容器ID
 * @param {string} searchInputId - 搜索输入框ID
 * @param {string} resultInfoId - 结果信息显示区域ID（可选）
 * @param {string} clearBtnId - 清除按钮ID（可选）
 */
function searchCompetitionCategories(containerId, searchInputId, resultInfoId, clearBtnId) {
    const searchInput = document.getElementById(searchInputId);
    const searchTerm = searchInput ? searchInput.value.trim().toLowerCase() : '';
    const clearBtn = clearBtnId ? document.getElementById(clearBtnId) : null;
    const resultInfo = resultInfoId ? document.getElementById(resultInfoId) : null;
    
    // 显示/隐藏清除按钮
    if (clearBtn) {
        clearBtn.style.display = searchTerm ? 'block' : 'none';
    }
    
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // 获取所有分类项
    const allCategories = container.querySelectorAll('.category-item');
    const allDetailItems = container.querySelectorAll('.category-item.category-detail');
    
    let matchCount = 0;
    
    if (!searchTerm) {
        // 如果搜索为空，恢复所有项目
        allCategories.forEach(item => {
            item.style.display = '';
            item.classList.remove('search-highlight');
            // 移除高亮
            const labels = item.querySelectorAll('label');
            labels.forEach(label => {
                if (label.innerHTML.includes('<mark>')) {
                    label.innerHTML = label.textContent;
                }
            });
        });
        
        // 隐藏所有二级三级分类
        container.querySelectorAll('.category-level-2, .category-level-3').forEach(level => {
            level.style.display = 'none';
        });
        
        // 隐藏搜索结果信息
        if (resultInfo) {
            resultInfo.style.display = 'none';
        }
        return;
    }
    
    // 首先隐藏所有详细项
    allDetailItems.forEach(item => {
        const label = item.querySelector('label');
        if (label) {
            const text = label.textContent.toLowerCase();
            
            if (text.includes(searchTerm)) {
                // 匹配的项目
                item.style.display = '';
                item.classList.add('search-highlight');
                matchCount++;
                
                // 高亮匹配文本
                const originalText = label.textContent;
                const regex = new RegExp(`(${escapeRegExp(searchTerm)})`, 'gi');
                label.innerHTML = originalText.replace(regex, '<mark style="background: #ffeb3b; padding: 2px 4px; border-radius: 3px; font-weight: 600;">$1</mark>');
                
                // 展开包含此项的所有父级分类
                let parent = item.parentElement;
                while (parent && parent !== container) {
                    if (parent.classList && (parent.classList.contains('category-level-2') || parent.classList.contains('category-level-3'))) {
                        parent.style.display = 'block';
                        
                        // 激活对应的标题
                        const prevSibling = parent.previousElementSibling;
                        if (prevSibling && prevSibling.classList.contains('category-item')) {
                            prevSibling.classList.add('active');
                            // 更新图标
                            const icon = prevSibling.querySelector('.category-icon');
                            if (icon) {
                                icon.classList.remove('fa-chevron-right');
                                icon.classList.add('fa-chevron-down');
                            }
                        }
                    }
                    parent = parent.parentElement;
                }
            } else {
                // 不匹配的项目
                item.style.display = 'none';
                item.classList.remove('search-highlight');
                // 移除高亮
                if (label.innerHTML.includes('<mark>')) {
                    label.innerHTML = label.textContent;
                }
            }
        }
    });
    
    // 处理分类标题的显示
    container.querySelectorAll('.category-sub').forEach(sub => {
        const parent = sub.nextElementSibling;
        if (parent) {
            const visibleItems = parent.querySelectorAll('.category-item.category-detail:not([style*="display: none"])');
            if (visibleItems.length > 0) {
                sub.style.display = '';
            } else {
                sub.style.display = 'none';
            }
        }
    });
    
    // 显示搜索结果信息
    if (resultInfo) {
        if (matchCount === 0) {
            resultInfo.innerHTML = '<i class="fas fa-exclamation-circle me-1"></i>未找到匹配的项目，请尝试其他关键词';
            resultInfo.style.background = '#fff3cd';
            resultInfo.style.color = '#856404';
        } else {
            resultInfo.innerHTML = `<i class="fas fa-check-circle me-1"></i>找到 <strong>${matchCount}</strong> 个匹配项目`;
            resultInfo.style.background = '#e3f2fd';
            resultInfo.style.color = '#1976d2';
        }
        resultInfo.style.display = 'block';
    }
}

/**
 * 清除搜索
 * @param {string} containerId - 容器ID
 * @param {string} searchInputId - 搜索输入框ID
 * @param {string} resultInfoId - 结果信息显示区域ID（可选）
 * @param {string} clearBtnId - 清除按钮ID（可选）
 */
function clearCompetitionSearch(containerId, searchInputId, resultInfoId, clearBtnId) {
    const searchInput = document.getElementById(searchInputId);
    if (searchInput) {
        searchInput.value = '';
        searchCompetitionCategories(containerId, searchInputId, resultInfoId, clearBtnId);
        searchInput.focus();
    }
}

/**
 * 转义正则表达式特殊字符
 */
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// 导出为全局函数供HTML页面使用
if (typeof window !== 'undefined') {
    window.loadCompetitionCategories = loadCompetitionCategories;
    window.renderCompetitionCategories = renderCompetitionCategories;
    window.getSelectedCategories = getSelectedCategories;
    window.validateCategorySelection = validateCategorySelection;
    window.toggleCategory = toggleCategory;
    window.toggleCategoryLocal = toggleCategoryLocal;
    window.searchCompetitionCategories = searchCompetitionCategories;
    window.clearCompetitionSearch = clearCompetitionSearch;
}
