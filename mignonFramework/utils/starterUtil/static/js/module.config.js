// module.config.js: Handles the ConfigManager panel UI and logic.

window.configModule = {
    init(container) {
        const panel = uiUtils.createDOMElement('div', 'dynamic-panel', `
            <div class="panel-header">
                <div style="display: flex; align-items: baseline;">
                    <h3 class="panel-title" style="font-size: 1.2rem;">Config 类 (ConfigManager)</h3>
                    <span class="panel-description">配置 ConfigManager 注入的类</span>
                </div>
                <button id="add-config-block-btn" class="secondary-button" style="padding: 0.5rem 1rem;">新增 Config 类</button>
            </div>
            <div id="config-blocks-container"></div>
        `);
        panel.id = 'config-panel';
        container.appendChild(panel);

        const configBlocksContainer = panel.querySelector('#config-blocks-container');
        panel.querySelector('#add-config-block-btn').addEventListener('click', () => this.createConfigBlock(configBlocksContainer, true)); // Pass true for isNew

        // 委托事件处理，用于处理动态添加的 Config 块内部的事件
        configBlocksContainer.addEventListener('click', e => {
            if (e.target.classList.contains('add-config-row-btn')) {
                const configBlock = e.target.closest('.config-block');
                this.addConfigFieldRow(configBlock.querySelector('.config-fields-list'));
                window.updateAllDynamicSelects(); // 字段新增后更新所有下拉菜单
            } else if (e.target.classList.contains('delete-row-btn')) { // 统一使用 delete-row-btn
                e.target.closest('.item-row').remove();
                this.validate();
                window.updateAllDynamicSelects(); // 字段删除后更新所有下拉菜单
            } else if (e.target.classList.contains('delete-config-block-btn')) {
                // 删除整个 Config 块
                e.target.closest('.config-block').remove();
                this.validate();
                window.updateAllDynamicSelects(); // Config 块删除后更新所有下拉菜单
            }
        });

        // 委托事件处理，用于处理动态添加的 Config 块内部的输入变化 (实时视觉反馈)
        configBlocksContainer.addEventListener('input', e => {
            if (e.target.classList.contains('config-class-name') || e.target.classList.contains('config-manager-name') || e.target.classList.contains('config-field-name') || e.target.classList.contains('config-manager-ini-path-input')) {
                // 只要输入变化就触发验证，现在空值也会立即显示提示
                this.validate(e.target);
            }
        });

        // 委托事件处理，用于处理动态添加的 Config 块内部的 select 变化
        configBlocksContainer.addEventListener('change', e => {
            if (e.target.classList.contains('config-field-type-select')) {
                window.updateAllDynamicSelects(); // 字段类型变化后更新所有下拉菜单
            }
        });

        this.createConfigBlock(configBlocksContainer, false); // 默认创建一个 Config 块，非新增
        setTimeout(() => panel.classList.add('visible'), 100);
    },

    /**
     * 创建一个新的 Config 块。
     * @param {HTMLElement} container - Config 块的容器元素。
     * @param {boolean} isNew - 是否是用户点击“新增 Config 类”按钮创建的。
     */
    createConfigBlock(container, isNew = false) {
        const managerNameValue = isNew ? "" : "config";
        const classNameValue = isNew ? "" : "Data";
        const managerIniPathValue = isNew ? "" : ""; // Default empty for new, or pre-fill if needed

        const blockHTML = `
            <div class="config-block">
                <div class="config-block-header">
                    <div class="input-field-wrapper">
                        <label>Manager Name:</label>
                        <input type="text" class="config-manager-name" value="${managerNameValue}" placeholder="Manager Name">
                        <div class="input-error-message">此项为必填</div>
                    </div>
                    <div class="input-field-wrapper">
                        <label>Class Name:</label>
                        <input type="text" class="config-class-name" value="${classNameValue}" placeholder="Class Name">
                        <div class="input-error-message">此项为必填</div>
                    </div>
                    <button type="button" class="delete-config-block-btn delete-button-red">删除</button>
                </div>
                <div class="config-block-extra-settings">
                    <div class="input-field-wrapper">
                        <label>Manager INI Path:</label>
                        <div class="path-input-group">
                            <span class="path-prefix">./resources/config/</span>
                            <input type="text" class="config-manager-ini-path-input" value="${managerIniPathValue}" placeholder="your_config_file_name">
                            <span class="path-suffix">.ini</span>
                        </div>
                        <div class="input-error-message"></div>
                    </div>
                </div>
                <div class="item-header config-row">
                    <span>字段名</span>
                    <span>类型</span>
                    <span>默认值</span>
                    <span>操作</span>
                </div>
                <div class="item-list config-fields-list"></div>
                <button type="button" class="secondary-button add-config-row-btn" style="margin-top: 1rem;">新增字段</button>
            </div>
        `;
        const newBlock = uiUtils.createDOMElement('div', '', blockHTML);
        container.appendChild(newBlock);

        // 根据 isNew 参数决定是否添加默认字段
        if (!isNew) {
            // 默认添加 pageSize 和 pageNo 字段
            this.addConfigFieldRow(newBlock.querySelector('.config-fields-list'), { name: 'pageSize', type: 'int', default: '0' });
            this.addConfigFieldRow(newBlock.querySelector('.config-fields-list'), { name: 'pageNo', type: 'int', default: '0' });
        } else {
            // 用户新增时，只添加一个空字段
            this.addConfigFieldRow(newBlock.querySelector('.config-fields-list'));
        }

        this.validate(); // 新增块后验证
        window.updateAllDynamicSelects(); // 新增 Config 块后更新所有下拉菜单
    },

    /**
     * 添加一个新的 Config 字段行。
     * @param {HTMLElement} container - 字段列表的容器元素。
     * @param {object} [fieldData={}] - 包含字段数据的对象，例如 { name: 'field', type: 'str', default: 'value' }。
     */
    addConfigFieldRow(container, fieldData = {}) {
        const nameValue = fieldData.name || '';
        const typeValue = fieldData.type || 'str';
        const defaultValue = fieldData.default || '';

        const rowHTML = `
            <div class="input-field-wrapper">
                <input type="text" class="config-field-name" placeholder="字段名" value="${nameValue}">
                <div class="input-error-message">此项为必填</div>
            </div>
            <select class="config-field-type-select">
                <option value="str" ${typeValue === 'str' ? 'selected' : ''}>str</option>
                <option value="int" ${typeValue === 'int' ? 'selected' : ''}>int</option>
                <option value="float" ${typeValue === 'float' ? 'selected' : ''}>float</option>
                <option value="bool" ${typeValue === 'bool' ? 'selected' : ''}>bool</option>
                <option value="list" ${typeValue === 'list' ? 'selected' : ''}>list</option>
                <option value="dict" ${typeValue === 'dict' ? 'selected' : ''}>dict</option>
            </select>
            <input type="text" class="config-field-default-value" placeholder="默认值" value="${defaultValue}">
            <button type="button" class="delete-row-btn delete-button-red-small">删除</button>
        `;
        container.appendChild(uiUtils.createDOMElement('div', 'item-row config-row', rowHTML));
        this.validate(); // 新增行后验证
    },

    /**
     * 验证 Config 模块的输入。
     * @param {HTMLElement} [targetInput=null] - 触发验证的特定输入元素，用于精细控制通知。
     */
    validate(targetInput = null) {
        const validateField = (inputElement, isEmptyAllowed = false, isDuplicateCheck = false, scope = document) => {
            const name = inputElement.value.trim();
            let hasError = false;
            // 错误消息元素现在是 inputElement 的下一个兄弟元素
            const errorMessageElement = inputElement.nextElementSibling && inputElement.nextElementSibling.classList.contains('input-error-message')
                ? inputElement.nextElementSibling
                : null;

            // 1. Check for emptiness if not allowed
            if (!isEmptyAllowed && name === '') {
                hasError = true;
            }

            // 2. Check for duplicates if required and not already empty
            if (!hasError && isDuplicateCheck) {
                let selector;
                if (inputElement.classList.contains('config-class-name')) {
                    selector = '.config-class-name';
                } else if (inputElement.classList.contains('config-manager-name')) {
                    selector = '.config-manager-name';
                } else if (inputElement.classList.contains('config-manager-ini-path-input')) {
                    selector = '.config-manager-ini-path-input';
                }
                else { // Default for field names
                    selector = '.config-field-name';
                }

                const allInputs = scope.querySelectorAll(selector);
                const namesMap = new Map();
                allInputs.forEach(input => {
                    const val = input.value.trim();
                    if (val) namesMap.set(val, (namesMap.get(val) || 0) + 1);
                });

                if (name && namesMap.get(name) > 1) {
                    hasError = true;
                    // 对于重复项，我们仍然使用通知，因为这是更严重的全局问题
                    uiUtils.showNotification(`重复项: "${name}"`, 'error'); // 保持通知
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
            return hasError; // Return true if there's an error
        };

        // Validate Manager Name and Class Name (cannot be empty, check duplicates globally)
        document.querySelectorAll('.config-block').forEach(block => {
            const managerNameInput = block.querySelector('.config-manager-name');
            const classNameInput = block.querySelector('.config-class-name');
            const managerIniPathInput = block.querySelector('.config-manager-ini-path-input');

            // Validate Manager Name (required, global duplicate check)
            validateField(managerNameInput, false, true, document.getElementById('config-panel'));
            // Validate Class Name (required, global duplicate check)
            validateField(classNameInput, false, true, document.getElementById('config-panel'));

            // Validate Manager INI Path (optional, but cannot be simultaneously empty or conflict with other names)
            let iniPathHasError = false;
            if (managerIniPathInput) {
                const iniPathValue = managerIniPathInput.value.trim();
                // For INI Path, the error message element is a sibling of the .path-input-group div
                const pathInputGroup = managerIniPathInput.closest('.path-input-group');
                const errorMessageElement = pathInputGroup ? pathInputGroup.nextElementSibling : null;


                // Scenario 1: Multiple empty INI paths
                if (iniPathValue === '') {
                    const emptyIniPathsCount = Array.from(document.querySelectorAll('.config-manager-ini-path-input'))
                        .filter(input => input.value.trim() === '').length;
                    if (emptyIniPathsCount > 1) {
                        iniPathHasError = true;
                        if (errorMessageElement) {
                            errorMessageElement.textContent = "不能同时使用默认位置";
                            errorMessageElement.classList.add('show');
                        }
                    }
                }
                // Scenario 2: Non-empty INI path conflicts with other names
                else {
                    // Collect all relevant names for conflict check
                    const allRelevantNames = new Set();
                    document.querySelectorAll('.config-manager-name').forEach(input => {
                        if (input.value.trim()) allRelevantNames.add(input.value.trim());
                    });
                    document.querySelectorAll('.config-class-name').forEach(input => {
                        if (input.value.trim()) allRelevantNames.add(input.value.trim());
                    });
                    // Add other non-empty INI paths (excluding current one)
                    Array.from(document.querySelectorAll('.config-manager-ini-path-input')).forEach(input => {
                        if (input.value.trim() && input !== managerIniPathInput) {
                            allRelevantNames.add(input.value.trim());
                        }
                    });

                    if (allRelevantNames.has(iniPathValue)) {
                        iniPathHasError = true;
                        if (errorMessageElement) {
                            errorMessageElement.textContent = "路径重复或冲突";
                            errorMessageElement.classList.add('show');
                        }
                    }
                }

                // Apply/remove input-error class for the INI path input
                if (iniPathHasError) {
                    managerIniPathInput.classList.add('input-error');
                } else {
                    managerIniPathInput.classList.remove('input-error');
                }

                // Ensure error message element visibility is consistent
                if (!iniPathHasError && errorMessageElement) {
                    errorMessageElement.textContent = ''; // Clear text
                    errorMessageElement.classList.remove('show');
                }
            }

            // Validate fields within this config block (cannot be empty, check duplicates within block)
            block.querySelectorAll('.config-field-name').forEach(fieldInput => {
                validateField(fieldInput, false, true, block);
            });
        });
    }
};
