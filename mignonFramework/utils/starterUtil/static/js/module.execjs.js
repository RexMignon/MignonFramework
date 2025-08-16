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
        };

        createExecjsRow();
        panel.querySelector('#add-execjs-row-btn').addEventListener('click', createExecjsRow);

        execjsList.addEventListener('click', e => {
            if (e.target.classList.contains('delete-row-btn')) {
                e.target.closest('.item-row').remove();
                this.validate();
            }
            if (e.target.classList.contains('remove-tag')) {
                e.target.parentElement.remove();
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
                }
            }
        });

        execjsList.addEventListener('change', e => {
            if (e.target.classList.contains('execjs-config-select')) {
                const row = e.target.closest('.item-row');
                const pathContainer = row.querySelector('.execjs-path-container');
                const configName = e.target.value; // This is the className
                this.updatePathInput(configName, pathContainer);
            }
        });

        setTimeout(() => panel.classList.add('visible'), 200);
    },

    updatePathInput(configName, container) {
        container.innerHTML = ''; // Clear previous element
        if (!configName) {
            const input = uiUtils.createDOMElement('input', '', '');
            input.type = 'text';
            input.placeholder = '例如: crypto.js';
            container.appendChild(input);
        } else {
            const select = uiUtils.createDOMElement('select', '', '');
            const state = window.getAppState ? window.getAppState() : { configs: {} };
            const fields = (state.configs && state.configs[configName]) ? state.configs[configName].fields : [];
            select.add(new Option('选择字段作为路径', ''));
            fields.forEach(field => {
                if (field.name) select.add(new Option(field.name, field.name));
            });
            container.appendChild(select);
        }
    },

    /**
     * 验证 ExecJS 模块的输入。
     * @param {HTMLElement} [targetInput=null] - 触发验证的特定输入元素，用于精细控制。
     */
    validate(targetInput = null) {
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
    }
};
