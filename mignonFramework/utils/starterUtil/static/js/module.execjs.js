// module.execjs.js: Handles the ExecJS panel UI and logic.

window.execjsModule = {
    init(container) {
        // ****** 关键修复：在您原有的模板字符串中为 item-list 添加 id="execjs-list" ******
        const panel = uiUtils.createDOMElement('div', 'dynamic-panel', `
            <div class="panel-header">
                <div style="display: flex; align-items: baseline;">
                    <h3 class="panel-title" style="font-size: 1.2rem;">ExecJS 支持</h3>
                    <span class="panel-description">将Python调用代理到JS方法, 并自动传递参数</span>
                </div>
                <button id="add-execjs-row-btn" class="secondary-button" style="padding: 0.5rem 1rem;">新增方法</button>
            </div>
            <div class="item-header execjs-row">
                <span>JS 方法名</span>
                <span>关联 Config (类名)</span>
                <span>参数 (回车添加)</span>
                <div class="path-label-container">
                    <span>JS 文件路径</span>
                    <span class="path-label-hint">(生成时自动添加 ./resources/js/ 前缀)</span>
                </div>
                <span>操作</span>
            </div>
            <div class="item-list" id="execjs-list"></div>
        `);
        panel.id = 'execjs-panel';
        container.appendChild(panel);

        const execjsList = panel.querySelector('#execjs-list');

        const createExecjsRow = () => {
            const rowHTML = `
                <div class="input-field-wrapper">
                    <input type="text" class="execjs-method-name" placeholder="例如: get_sign">
                    <div class="input-error-message">此项为必填</div>
                </div>
                <select class="execjs-config-select">
                    <option value="">无</option>
                </select>
                <div class="tag-input-container">
                    <input type="text" class="tag-input" placeholder="输入参数名...">
                </div>
                <div class="execjs-path-container">
                    <input type="text" placeholder="例如: crypto.js">
                </div>
                <button type="button" class="secondary-button delete-row-btn">删除</button>`;
            execjsList.appendChild(uiUtils.createDOMElement('div', 'item-row execjs-row', rowHTML));
            this.validate(); // Validate after adding new row
            // 新增行后立即更新下拉框
            this.updateAllConfigSelects();
        };

        createExecjsRow();
        panel.querySelector('#add-execjs-row-btn').addEventListener('click', createExecjsRow);

        execjsList.addEventListener('click', e => {
            if (e.target.classList.contains('delete-row-btn')) {
                e.target.closest('.item-row').remove();
                this.validate();
                // 删除行后更新下拉框
                this.updateAllConfigSelects();
            }
            if (e.target.classList.contains('remove-tag')) {
                e.target.parentElement.remove();
                this.validate(); // 参数删除后重新验证
            }
        });

        execjsList.addEventListener('input', e => {
            if (e.target.classList.contains('execjs-method-name')) {
                this.validate(e.target); // Pass target to validate only that input
            }
        });

        execjsList.addEventListener('keydown', e => {
            if (e.key === 'Enter' && e.target.classList.contains('tag-input')) {
                e.preventDefault();
                const value = e.target.value.trim();
                if (value) {
                    const tag = uiUtils.createDOMElement('span', 'tag', `${value}<button type="button" class="remove-tag">&times;</button>`);
                    e.target.parentNode.insertBefore(tag, e.target);
                    e.target.value = '';
                    this.validate(); // 参数添加后重新验证
                }
            }
        });

        // 核心改动：使用 change 事件监听，当用户手动更改选项时触发
        execjsList.addEventListener('change', e => {
            if (e.target.classList.contains('execjs-config-select')) {
                const row = e.target.closest('.item-row');
                const pathContainer = row.querySelector('.execjs-path-container');
                const configName = e.target.value; // This is the className
                // 在这里直接调用 updatePathInput，确保获取最新的 state
                this.updatePathInput(configName, pathContainer);
            }
        });

        setTimeout(() => panel.classList.add('visible'), 200);
    },

    /**
     * 更新 ExecJS 模块中的 JS 文件路径输入框或下拉框。
     * 此函数现在会尝试保留旧值。
     * @param {string} configName - 选定的 Config 类名。
     * @param {HTMLElement} container - 路径输入框/下拉框的容器元素。
     */
    updatePathInput(configName, container) {
        // 尝试获取当前路径输入框/下拉框的旧值
        let currentPathValue = '';
        const existingInput = container.querySelector('input[type="text"]');
        const existingSelect = container.querySelector('select');

        if (existingInput) {
            currentPathValue = existingInput.value;
        } else if (existingSelect) {
            currentPathValue = existingSelect.value;
        }

        container.innerHTML = ''; // 清空旧元素

        if (!configName) {
            // 如果没有选择 Config 类，则显示文本输入框
            const input = uiUtils.createDOMElement('input', '', '');
            input.type = 'text';
            input.placeholder = '例如: crypto.js';
            input.value = currentPathValue; // 恢复旧值
            container.appendChild(input);
        } else {
            // 如果选择了 Config 类，则显示字段选择下拉框
            const select = uiUtils.createDOMElement('select', '', '');
            const state = window.getAppState ? window.getAppState() : { configs: {} };
            const fields = (state.configs && state.configs[configName]) ? state.configs[configName].fields : [];

            select.add(new Option('选择字段作为路径', '')); // 默认选项
            fields.forEach(field => {
                if (field.name) {
                    select.add(new Option(field.name, field.name));
                }
            });

            // 尝试恢复旧值，但要确保旧值在新的选项列表中存在
            if (fields.some(f => f.name === currentPathValue)) {
                select.value = currentPathValue;
            } else {
                select.value = ''; // 如果旧值不存在于新列表中，则重置
            }

            container.appendChild(select);
        }
    },

    // 新增：用于在其他模块修改Config时，自动更新此模块下拉框的公共方法
    updateAllConfigSelects() {
        const state = window.getAppState(); // Get the latest state once
        const configNames = Object.keys(state.configs);

        document.querySelectorAll('.execjs-row').forEach(row => { // Iterate through each execjs row
            const configSelectElement = row.querySelector('.execjs-config-select');
            const pathContainer = row.querySelector('.execjs-path-container');

            if (!configSelectElement || !pathContainer) return;

            const currentVal = configSelectElement.value;
            uiUtils.updateSelectOptions(configSelectElement, configNames, '无');
            if (configNames.includes(currentVal)) {
                configSelectElement.value = currentVal;
            } else {
                configSelectElement.value = ''; // 如果之前选中的Config不存在，则重置
            }

            // 关键：直接调用 updatePathInput，确保路径字段的下拉菜单得到更新
            this.updatePathInput(configSelectElement.value, pathContainer);
        });
    },

    /**
     * 验证 ExecJS 模块的输入。
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
                const allInputs = scope.querySelectorAll('.execjs-method-name'); // Targeting method names
                const namesMap = new Map();
                allInputs.forEach(input => {
                    const val = input.value.trim();
                    if (val) namesMap.set(val, (namesMap.get(val) || 0) + 1);
                });

                if (name && namesMap.get(name) > 1) {
                    hasError = true;
                    uiUtils.showNotification(`JS 方法名重复: "${name}"`, 'error');
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

        // Validate JS Method Names (cannot be empty, check duplicates globally)
        document.querySelectorAll('.execjs-method-name').forEach(methodNameInput => {
            validateField(methodNameInput, false, true, document); // Scope is document for global method names
        });

        // ====== 新增：验证每个方法内的参数名是否重复 ======
        document.querySelectorAll('.execjs-row').forEach(row => {
            const tagsContainer = row.querySelector('.tag-input-container');
            if (!tagsContainer) return;

            const tags = tagsContainer.querySelectorAll('.tag');
            const paramNames = new Set();
            let hasDuplicateParam = false;

            tags.forEach(tag => {
                // 移除标签中的删除按钮文本，只保留参数名
                const paramName = tag.textContent.slice(0, -1).trim();
                if (paramNames.has(paramName)) {
                    hasDuplicateParam = true;
                    uiUtils.showNotification(`JS 方法参数名重复: "${paramName}"`, 'error');
                }
                paramNames.add(paramName);
            });

            // 如果有重复参数，给整个标签输入容器添加错误样式
            if (hasDuplicateParam) {
                tagsContainer.classList.add('input-error');
                hasModuleError = true; // Mark module as having an error
            } else {
                tagsContainer.classList.remove('input-error');
            }
        });
        // ===================================================
        return hasModuleError; // Return overall module validation status
    }
};
