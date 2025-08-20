// module.spider_generator.js: 处理请求字段映射模块的 UI 和逻辑。

window.spiderGeneratorModule = {
    /**
     * 初始化请求字段映射面板。
     * @param {HTMLElement} container - 动态模块的容器容器。
     */
    init(container) {
        // 创建主面板元素
        const panel = uiUtils.createDOMElement('div', 'dynamic-panel', `
            <div class="panel-header">
                <div style="display: flex; align-items: baseline;">
                    <h3 class="panel-title" style="font-size: 1.2rem;">请求字段映射</h3>
                    <span class="panel-description">从 cURL 提取字段并映射到 Config 类</span>
                </div>
            </div>

            <div class="field-sections-container" id="field-sections-container">
                // 字段子模块将在这里动态生成
            </div>
        `);
        panel.id = 'request-field-mapper-panel'; // 更改 ID 以反映新功能
        container.appendChild(panel);

        // 获取元素引用
        const fieldSectionsContainerEl = panel.querySelector('#field-sections-container'); // 获取新的容器元素

        // 委托事件处理，用于处理动态添加的行（新增字段按钮、删除/恢复按钮、Config/Field 下拉框联动）
        fieldSectionsContainerEl.addEventListener('click', e => {
            // 新增字段按钮
            if (e.target.classList.contains('add-field-btn')) {
                const fieldType = e.target.dataset.fieldType;
                const containerId = `${fieldType}-list`;
                const containerEl = document.getElementById(containerId);
                if (containerEl) {
                    this.createFieldRow(containerEl, { name: '', sourceType: fieldType }, true); // true for isCustom
                    window.updateAllDynamicSelects(); // 触发全局更新，填充 Config 下拉框
                }
            }
            // 删除/恢复按钮
            else if (e.target.classList.contains('delete-field-btn')) {
                const row = e.target.closest('.item-row');
                row.classList.add('deleted-row'); // 添加删除线样式
                e.target.textContent = '恢复';
                e.target.classList.remove('secondary-button');
                e.target.classList.add('action-button');
                e.target.classList.remove('delete-field-btn'); // 移除删除类
                e.target.classList.add('restore-field-btn'); // 添加恢复类
                uiUtils.showNotification('字段已标记为删除，点击“恢复”可撤销。');
            } else if (e.target.classList.contains('restore-field-btn')) {
                const row = e.target.closest('.item-row');
                row.classList.remove('deleted-row'); // 移除删除线样式
                e.target.textContent = '删除';
                e.target.classList.remove('action-button');
                e.target.classList.add('secondary-button');
                e.target.classList.remove('restore-field-btn'); // 移除恢复类
                e.target.classList.add('delete-field-btn'); // 添加删除类
                uiUtils.showNotification('字段已恢复。');
            }
        });

        // Config 和 Field 下拉框的联动
        fieldSectionsContainerEl.addEventListener('change', e => {
            const target = e.target;
            if (target.classList.contains('extracted-field-config-select')) {
                const row = target.closest('.item-row');
                const fieldSelect = row.querySelector('.extracted-field-config-field-select');
                this.updateConfigFieldSelect(target.value, fieldSelect);
            }
        });

        // --- NEW FIX: Call populateExtractedFieldsTable on init to ensure structure exists ---
        // This will create the empty sections and their "Add Field" buttons,
        // allowing updateAllExtractedFieldsConfigSelects to find the dropdowns.
        this.populateExtractedFieldsTable({}); // Pass an empty object to initialize empty sections

        // 确保面板可见
        setTimeout(() => panel.classList.add('visible'), 500); // 稍微延迟，避免与其他模块动画冲突
    },

    /**
     * 填充提取的字段表格。
     * @param {object} extractedData - 提取的字段数据 (来自后端)。
     */
    populateExtractedFieldsTable(extractedData) {
        const fieldSectionsContainerEl = document.getElementById('field-sections-container');
        fieldSectionsContainerEl.innerHTML = ''; // 清空所有子模块容器

        let hasAnyData = false; // 标记是否有任何数据被填充到任何子模块

        const fieldTypes = [
            { id: 'headers', title: 'Headers 头部', addBtnText: '新增 Header' },
            { id: 'cookies', title: 'Cookies', addBtnText: '新增 Cookie' },
            { id: 'params', title: 'Params 参数', addBtnText: '新增 Param' },
            { id: 'jsonData', title: 'JSON Data JSON 数据', addBtnText: '新增 JSON 字段' }
        ];

        fieldTypes.forEach(typeInfo => {
            const dataForType = extractedData[typeInfo.id] || {};
            const fieldNames = Object.keys(dataForType).sort();

            // Always create the section even if it has no initial data,
            // so the "Add Field" button and dropdowns are present for later updates.
            // Only set hasAnyData to true if there's actual data from cURL.
            if (fieldNames.length > 0 || Object.keys(extractedData).length === 0) { // Keep section if it has data OR if it's initial empty state
                if (fieldNames.length > 0) {
                    hasAnyData = true; // Only set this if there's actual cURL data
                }
                const sectionHtml = `
                    <div class="section-header">
                        <h4>${typeInfo.title}</h4>
                        <button class="secondary-button add-field-btn" data-field-type="${typeInfo.id}">${typeInfo.addBtnText}</button>
                    </div>
                    <div class="item-header extracted-field-row">
                        <span>字段名</span>
                        <span>关联的 Config (类名)</span>
                        <span>Config 字段名</span>
                        <span>操作</span>
                    </div>
                    <div class="item-list" id="${typeInfo.id}-list"></div>
                `;
                const fieldSectionEl = uiUtils.createDOMElement('div', 'field-section', sectionHtml);
                fieldSectionsContainerEl.appendChild(fieldSectionEl);

                // 修复：直接获取新创建的 fieldSectionEl 内部的 item-list 容器
                const listContainer = fieldSectionEl.querySelector(`#${typeInfo.id}-list`);
                fieldNames.forEach(name => {
                    this.createFieldRow(listContainer, { name: name, sourceType: typeInfo.id }, false);
                });
            }
        });

        // 根据是否有数据来显示或隐藏整个容器
        // Only make the container visible if it has actual cURL data, or if it's the initial empty state.
        if (hasAnyData || Object.keys(extractedData).length === 0) { // Show if there's data OR if it's initial empty call
            fieldSectionsContainerEl.classList.add('visible');
        } else {
            fieldSectionsContainerEl.classList.remove('visible');
        }
    },

    /**
     * 创建一个字段表格行。
     * @param {HTMLElement} container - 表格的容器容器 (例如 headers-list, cookies-list)。
     * @param {object} fieldData - 字段数据 {name, sourceType}。
     * @param {boolean} isCustom - 是否是用户新增的自定义字段。
     */
    createFieldRow(container, fieldData, isCustom = false) {
        const fieldNameHtml = isCustom ?
            `<input type="text" class="extracted-field-name-input" placeholder="字段名" value="${fieldData.name}">` :
            `<span class="extracted-field-name-display">${fieldData.name}</span><input type="hidden" class="extracted-field-name-input" value="${fieldData.name}">`;

        const rowHTML = `
            ${fieldNameHtml}
            <select class="extracted-field-config-select">
                <option value="">无</option>
            </select>
            <select class="extracted-field-config-field-select" disabled>
                <option value="">-</option>
            </select>
            <button type="button" class="secondary-button delete-field-btn">删除</button>
        `;
        const newRow = uiUtils.createDOMElement('div', 'item-row extracted-field-row', rowHTML);
        newRow.dataset.fieldName = fieldData.name; // 存储原始字段名
        newRow.dataset.sourceType = fieldData.sourceType || 'custom'; // 存储来源类型

        container.appendChild(newRow);

        // 立即更新 Config 下拉菜单
        const configSelect = newRow.querySelector('.extracted-field-config-select');
        const fieldSelect = newRow.querySelector('.extracted-field-config-field-select');
        this.updateConfigSelectsForRow(configSelect, fieldSelect);
    },

    /**
     * 更新单个行中的 Config 实例选择下拉菜单及其字段下拉菜单。
     * @param {HTMLElement} configSelectElement - Config 选择下拉菜单元素。
     * @param {HTMLElement} configFieldSelectElement - Config 字段选择下拉菜单元素。
     */
    updateConfigSelectsForRow(configSelectElement, configFieldSelectElement) {
        if (!configSelectElement) return;

        const currentConfigVal = configSelectElement.value;
        configSelectElement.innerHTML = '<option value="">无</option>'; // 清空并添加默认选项

        const state = window.getAppState ? window.getAppState() : { configs: {} };
        const configNames = Object.keys(state.configs);

        configNames.forEach(name => {
            const option = new Option(name, name); // name 是 Config 的 ClassName
            configSelectElement.add(option);
        });

        // 检查之前选中的 Config 是否仍然存在
        if (configNames.includes(currentConfigVal)) {
            configSelectElement.value = currentConfigVal;
        } else {
            // 如果之前选中的 Config 不存在，则重置为默认值
            configSelectElement.value = '';
        }

        // --- IMPORTANT FIX: Explicitly call updateConfigFieldSelect here ---
        // This ensures the field dropdown is updated immediately after the config select's value is set.
        this.updateConfigFieldSelect(configSelectElement.value, configFieldSelectElement);

        // 移除这一行，因为它现在是多余的，并且可能导致不必要的事件触发
        // configSelectElement.dispatchEvent(new Event('change'));
    },

    /**
     * 更新所有提取字段行中的 Config 下拉菜单。
     * 这个方法会被 window.updateAllDynamicSelects 调用。
     */
    updateAllExtractedFieldsConfigSelects() {
        document.querySelectorAll('.extracted-field-row').forEach(row => { // 选择所有 extracted-field-row
            const configSelect = row.querySelector('.extracted-field-config-select');
            const fieldSelect = row.querySelector('.extracted-field-config-field-select');
            this.updateConfigSelectsForRow(configSelect, fieldSelect);
        });
    },

    /**
     * 更新 Config 字段选择下拉菜单。
     * @param {string} configName - 选定的 Config 类名。
     * @param {HTMLElement} fieldSelectElement - 字段选择下拉菜单元素。
     */
    updateConfigFieldSelect(configName, fieldSelectElement) {
        if (!fieldSelectElement) return;

        const state = window.getAppState ? window.getAppState() : { configs: {} };
        const fields = (state.configs && state.configs[configName]) ? state.configs[configName].fields : [];
        const currentVal = fieldSelectElement.value;

        fieldSelectElement.innerHTML = '<option value="">-</option>'; // 清空并添加默认选项

        if (configName) { // 只有选择了 Config 类才启用并填充字段
            fieldSelectElement.disabled = false;
            fields.forEach(field => {
                if (field.name) {
                    fieldSelectElement.add(new Option(field.name, field.name));
                }
            });
            // 检查之前选中的字段是否仍然存在于当前 Config 中
            if (fields.some(f => f.name === currentVal)) {
                fieldSelectElement.value = currentVal;
            } else {
                // 如果之前选中的字段不存在，则重置为默认值
                fieldSelectElement.value = '';
            }
        } else {
            fieldSelectElement.disabled = true; // 未选择 Config 类时禁用
        }
    },
};
