// module.callback.js: Handles the QueueIter Callback panel UI and logic.

window.callbackModule = {
    init(container) {
        const panel = uiUtils.createDOMElement('div', 'dynamic-panel', `
            <div class="panel-header">
                <div style="display: flex; align-items: baseline;">
                    <h3 class="panel-title" style="font-size: 1.2rem;">Callback 回调</h3>
                    <span class="panel-description">为 QueueIter 实例绑定回调函数, 在迭代时触发</span>
                </div>
                 <button id="add-callback-row-btn" class="secondary-button" style="padding: 0.5rem 1rem;">新增 Callback</button>
            </div>
            <div class="item-header callback-row">
                <span>方法名</span>
                <span>关联的 QueueIter</span>
                <span>关联 Config</span>
                <span>Config (类名)</span>
                <span>字段</span>
                <span>赋值为</span>
                <span>操作</span>
            </div>
            <div class="item-list" id="callback-list"></div>
        `);
        panel.id = 'callback-panel';
        container.appendChild(panel);

        const callbackList = panel.querySelector('#callback-list');

        const createCallbackRow = () => {
            const rowHTML = `
                <div class="input-field-wrapper">
                    <input type="text" class="callback-method-name" placeholder="例如: on_next_page">
                    <div class="input-error-message">此项为必填</div>
                </div>
                <select class="callback-queue-select">
                    <option value="">选择 QueueIter</option>
                </select>
                <select class="callback-config-toggle">
                    <option value="yes">是</option>
                    <option value="no" selected>否</option>
                </select>
                <select class="callback-config-select" disabled>
                    <option value="">-</option>
                </select>
                <select class="callback-field-select" disabled>
                    <option value="">-</option>
                </select>
                <input type="text" class="callback-assign-value" value="que.current_index" disabled>
                <button type="button" class="secondary-button delete-row-btn">删除</button>
            `;
            callbackList.appendChild(uiUtils.createDOMElement('div', 'item-row callback-row', rowHTML));
            // --- FIX: Update dropdowns immediately after creating a new row ---
            if (window.updateAllDynamicSelects) {
                window.updateAllDynamicSelects();
            }
            this.validate(); // 新增行后立即验证
        };

        createCallbackRow();
        panel.querySelector('#add-callback-row-btn').addEventListener('click', createCallbackRow);

        callbackList.addEventListener('click', e => {
            if (e.target.classList.contains('delete-row-btn')) {
                e.target.closest('.item-row').remove();
                this.validate();
                // --- FIX: Trigger global update after deletion ---
                if (window.updateAllDynamicSelects) {
                    window.updateAllDynamicSelects();
                }
            }
        });

        callbackList.addEventListener('input', e => {
            if (e.target.classList.contains('callback-method-name')) {
                this.validate(e.target); // 只要输入变化就触发验证
                // --- FIX: Trigger global update after method name input to update state.callbacks ---
                if (window.updateAllDynamicSelects) {
                    window.updateAllDynamicSelects();
                }
            }
        });

        callbackList.addEventListener('change', e => {
            const target = e.target;
            if (target.classList.contains('callback-config-toggle')) {
                const row = target.closest('.item-row');
                const isConfigEnabled = target.value === 'yes';
                const selects = row.querySelectorAll('.callback-config-select, .callback-field-select');
                const input = row.querySelector('.callback-assign-value');

                selects.forEach(sel => sel.disabled = !isConfigEnabled);
                input.disabled = !isConfigEnabled;

                if (!isConfigEnabled) {
                    selects.forEach(sel => sel.innerHTML = '<option value="">-</option>');
                    input.value = '';
                } else {
                    input.value = 'que.current_index';
                    if (window.updateAllDynamicSelects) window.updateAllDynamicSelects();
                }
            }
            if (target.classList.contains('callback-queue-select')) {
                this.validate();
                // --- FIX: Trigger global update after queue select change to update state.callbacks ---
                if (window.updateAllDynamicSelects) {
                    window.updateAllDynamicSelects();
                }
            }
            if (target.classList.contains('callback-config-select')) {
                const row = target.closest('.item-row');
                const fieldSelect = row.querySelector('.callback-field-select');
                this.updateFieldSelect(target.value, fieldSelect); // target.value is the className
                // --- FIX: Trigger global update after config select change to update state.callbacks ---
                if (window.updateAllDynamicSelects) {
                    window.updateAllDynamicSelects();
                }
            }
        });

        setTimeout(() => panel.classList.add('visible'), 400);
    },

    updateFieldSelect(configName, fieldSelect) {
        if (!fieldSelect || fieldSelect.disabled) return;

        const state = window.getAppState ? window.getAppState() : { configs: {} };
        const fields = (state.configs && state.configs[configName]) ? state.configs[configName].fields : [];
        const currentVal = fieldSelect.value;

        fieldSelect.innerHTML = '<option value="">选择字段</option>';
        fields.forEach(field => {
            if (field.name) {
                fieldSelect.add(new Option(field.name, field.name));
            }
        });

        if (fields.some(f => f.name === currentVal)) {
            fieldSelect.value = currentVal;
        }
    },

    /**
     * 新增：更新所有 Callback 模块中 QueueIter 下拉菜单的方法。
     * 这个方法会被 window.updateAllDynamicSelects 调用。
     */
    updateAllQueueIterSelects() {
        const state = window.getAppState(); // 获取最新的状态
        const queueIterNames = Object.keys(state.queueIters);

        document.querySelectorAll('.callback-queue-select').forEach(select => {
            const currentVal = select.value;
            uiUtils.updateSelectOptions(select, queueIterNames, '选择 QueueIter');
            if (queueIterNames.includes(currentVal)) {
                select.value = currentVal;
            } else {
                // 如果之前选中的 QueueIter 不存在，则重置为默认值
                select.value = '';
            }
            // 保持 dispatchEvent，因为它可能触发 callbackModule 内部的验证或其他逻辑
            select.dispatchEvent(new Event('change'));
        });
    },

    /**
     * 验证 Callback 模块的输入。
     * @param {HTMLElement} [targetInput=null] - 触发验证的特定输入元素，用于精细控制。
     * @returns {boolean} 如果存在任何错误，则返回 true。
     */
    validate(targetInput = null) {
        let hasModuleError = false; // Track if this module has any errors

        const validateField = (inputElement, isEmptyAllowed = false, isDuplicateCheck = false, scope = document) => {
            const name = inputElement.value.trim();
            let hasError = false;
            const errorMessageElement = inputElement.nextElementSibling && inputElement.nextElementSibling.classList.contains('input-error-message')
                ? inputElement.nextElementSibling
                : null;

            // 1. Check for emptiness if not allowed
            if (!isEmptyAllowed && name === '') {
                hasError = true;
            }

            // 2. Check for duplicates if required and not already empty
            if (!hasError && isDuplicateCheck) {
                const allInputs = scope.querySelectorAll('.callback-method-name'); // 针对方法名
                const namesMap = new Map();
                allInputs.forEach(input => {
                    const value = input.value.trim();
                    if (value) {
                        namesMap.set(value, (namesMap.get(value) || 0) + 1);
                    }
                });

                if (name && namesMap.get(name) > 1) {
                    hasError = true;
                    uiUtils.showNotification(`Callback 方法名重复: "${name}"`, 'error');
                }
            }

            // Apply/remove error class
            if (hasError) {
                inputElement.classList.add('input-error');
                hasModuleError = true; // Mark module as having an error
            } else {
                inputElement.classList.remove('input-error');
            }

            // Show/hide error message div for emptiness
            if (errorMessageElement) {
                if (name === '' && !isEmptyAllowed) { // Only show if empty and not allowed to be empty
                    errorMessageElement.textContent = "此项为必填";
                    errorMessageElement.classList.add('show'); // Show immediately
                } else {
                    errorMessageElement.textContent = '';
                    errorMessageElement.classList.remove('show');
                }
            }
            return hasError;
        };

        // Validate Callback Method Names (cannot be empty, check duplicates globally)
        document.querySelectorAll('.callback-method-name').forEach(methodNameInput => {
            validateField(methodNameInput, false, true, document); // Scope is document for global method names
        });

        // Validate QueueIter selections for duplicates (still using notification as per previous logic)
        const checkDuplicatesSelect = (selector, errorMsg) => {
            const allSelects = document.querySelectorAll(selector);
            const values = new Map();
            allSelects.forEach(select => {
                const value = select.value.trim();
                if (value) {
                    values.set(value, (values.get(value) || 0) + 1);
                }
            });
            allSelects.forEach(select => {
                const value = select.value.trim();
                const wasInError = select.classList.contains('input-error');
                if (value && values.get(value) > 1) {
                    if (!wasInError) {
                        select.classList.add('input-error');
                        uiUtils.showNotification(`${errorMsg}: "${value}"`, 'error');
                        hasModuleError = true; // Mark module as having an error
                    }
                } else {
                    select.classList.remove('input-error');
                }
            });
        };
        checkDuplicatesSelect('.callback-queue-select', '关联的 QueueIter 重复');

        return hasModuleError; // Return overall module validation status
    }
};
