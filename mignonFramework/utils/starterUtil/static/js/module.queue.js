// module.queue.js: Handles the QueueIter panel UI and logic.

window.queueModule = {
    init(container) {
        const panel = uiUtils.createDOMElement('div', 'dynamic-panel', `
            <div class="panel-header">
                <div style="display: flex; align-items: baseline;">
                    <h3 class="panel-title" style="font-size: 1.2rem;">QueueIter 队列</h3>
                    <span class="panel-description">配置爬虫任务队列, 支持爬取结束后回调修改Config</span>
                </div>
                 <button id="add-queue-btn" class="secondary-button" style="padding: 0.5rem 1rem;">新增队列实例</button>
            </div>
            <div id="queue-blocks"></div>
        `);
        panel.id = 'queue-panel';
        container.appendChild(panel);

        const queueBlocks = panel.querySelector('#queue-blocks');

        const createTargetRow = (container) => {
            // --- MODIFIED: Removed the "字段名" (queue-field-name) input and its wrapper ---
            const rowHTML = `
                <select class="queue-target-select">
                    <option value="yes">是</option>
                    <option value="no" selected>否</option>
                </select>
                <select class="queue-config-select" disabled>
                    <option value="">-</option>
                </select>
                <select class="queue-field-select" disabled>
                    <option value="">-</option>
                </select>
                <input type="text" class="queue-default-value" placeholder="例如: lambda x: x + 1" disabled>
                <button type="button" class="secondary-button delete-row-btn">删除</button>
            `;
            // --- MODIFIED: Adjusted grid template to account for the removed column ---
            const rowElement = uiUtils.createDOMElement('div', 'item-row queue-target-row', rowHTML);
            rowElement.style.gridTemplateColumns = "1fr 1.5fr 1.5fr 2fr auto"; // Adjusted grid
            container.appendChild(rowElement);
        };

        const createQueueBlock = (name = 'que') => {
            const blockId = `queue-block-${Date.now()}`;
            // --- MODIFIED: Removed "字段名" from the header ---
            const blockHTML = `
                <div class="queue-block-header">
                    <label for="queue-name-${blockId}">QueueIter 实例名:</label>
                    <div class="input-field-wrapper">
                        <input type="text" id="queue-name-${blockId}" value="${name}" class="queue-instance-name">
                        <div class="input-error-message">此项为必填</div>
                    </div>
                    <button type="button" class="secondary-button add-queue-target-btn" data-target="${blockId}-list">新增 @target 任务</button>
                </div>
                <div class="item-header queue-target-row" style="margin-top: 1rem;">
                    <span>启用 @target</span>
                    <span>Config (类名)</span>
                    <span>字段</span>
                    <span>默认值 (支持lambda)</span>
                    <span>操作</span>
                </div>
                <div class="item-list" id="${blockId}-list"></div>
            `;
            const block = uiUtils.createDOMElement('div', 'queue-block', blockHTML);
            // --- MODIFIED: Adjust header grid to match new layout ---
            const header = block.querySelector('.item-header.queue-target-row');
            header.style.gridTemplateColumns = "1fr 1.5fr 1.5fr 2fr auto"; // Adjusted grid for header
            queueBlocks.appendChild(block);
            createTargetRow(block.querySelector(`#${blockId}-list`)); // Add one default target row
            this.validate(); // Validate after creating new block
        };

        createQueueBlock(); // Add one default instance

        panel.querySelector('#add-queue-btn').addEventListener('click', () => {
            const state = window.getAppState ? window.getAppState() : { queueIters: {} };
            const existingNames = Object.keys(state.queueIters);
            let newName = 'que';
            let counter = 2;
            while (existingNames.includes(newName)) {
                newName = `que${counter}`;
                counter++;
            }
            createQueueBlock(newName);
        });

        queueBlocks.addEventListener('click', e => {
            if (e.target.classList.contains('add-queue-target-btn')) {
                const targetId = e.target.dataset.target;
                const targetContainer = document.getElementById(targetId);
                if (targetContainer) createTargetRow(targetContainer);
            }
            if (e.target.classList.contains('delete-row-btn')) {
                e.target.closest('.item-row').remove();
                this.validate();
            }
        });

        queueBlocks.addEventListener('input', e => {
            // --- MODIFIED: Removed queue-field-name from validation trigger ---
            if (e.target.classList.contains('queue-instance-name')) {
                this.validate(e.target);
                if (window.updateAllDynamicSelects) window.updateAllDynamicSelects();
            }
        });

        queueBlocks.addEventListener('change', e => {
            const target = e.target;
            if (target.classList.contains('queue-target-select')) {
                const row = target.closest('.item-row');
                const isTargetEnabled = target.value === 'yes';
                const configSelect = row.querySelector('.queue-config-select');
                const fieldSelect = row.querySelector('.queue-field-select');
                const input = row.querySelector('.queue-default-value');

                configSelect.disabled = !isTargetEnabled;
                fieldSelect.disabled = !isTargetEnabled;
                input.disabled = !isTargetEnabled;

                if (!isTargetEnabled) {
                    configSelect.innerHTML = '<option value="">-</option>';
                    fieldSelect.innerHTML = '<option value="">-</option>';
                    input.value = '';
                } else {
                    this.updateConfigSelect(configSelect);
                }
            }

            if (target.classList.contains('queue-config-select')) {
                const row = target.closest('.item-row');
                const fieldSelect = row.querySelector('.queue-field-select');
                this.updateFieldSelect(target.value, fieldSelect);
            }

            if (target.matches('.queue-target-select, .queue-config-select, .queue-field-select')) {
                this.validate();
            }
        });

        setTimeout(() => panel.classList.add('visible'), 300);
    },

    updateConfigSelect(configSelect) {
        if (!configSelect || configSelect.disabled) return;
        const state = window.getAppState ? window.getAppState() : { configs: {} };
        const configNames = Object.keys(state.configs || {});
        const currentVal = configSelect.value;

        uiUtils.updateSelectOptions(configSelect, configNames, '选择Config');

        if (configNames.includes(currentVal)) {
            configSelect.value = currentVal;
        }
        configSelect.dispatchEvent(new Event('change'));
    },

    updateFieldSelect(configName, fieldSelect) {
        if (!fieldSelect || fieldSelect.disabled) return;

        const state = window.getAppState ? window.getAppState() : { configs: {} };
        const fields = (state.configs && state.configs[configName]) ? state.configs[configName].fields : [];
        const currentVal = fieldSelect.value;
        const fieldNames = fields.map(f => f.name);

        uiUtils.updateSelectOptions(fieldSelect, fieldNames, '选择字段');

        if (fieldNames.includes(currentVal)) {
            fieldSelect.value = currentVal;
        }
    },

    validate(targetInput = null) {
        const validateField = (inputElement, isEmptyAllowed = false, isDuplicateCheck = false, scope = document) => {
            const name = inputElement.value.trim();
            let hasError = false;
            const errorMessageElement = inputElement.nextElementSibling && inputElement.nextElementSibling.classList.contains('input-error-message')
                ? inputElement.nextElementSibling
                : null;
            if (!isEmptyAllowed && name === '') {
                hasError = true;
            }
            if (!hasError && isDuplicateCheck) {
                let selector;
                if (inputElement.classList.contains('queue-instance-name')) {
                    selector = '.queue-instance-name';
                } else {
                    // This part is no longer needed as there's no field name to check for duplicates
                    return false;
                }
                const allInputs = scope.querySelectorAll(selector);
                const namesMap = new Map();
                allInputs.forEach(input => {
                    const val = input.value.trim();
                    if (val) namesMap.set(val, (namesMap.get(val) || 0) + 1);
                });
                if (name && namesMap.get(name) > 1) {
                    hasError = true;
                    uiUtils.showNotification(`重复项: "${name}"`, 'error');
                }
            }
            if (hasError) {
                inputElement.classList.add('input-error');
            } else {
                inputElement.classList.remove('input-error');
            }
            if (errorMessageElement) {
                if (name === '' && !isEmptyAllowed) {
                    errorMessageElement.textContent = "此项为必填";
                    errorMessageElement.classList.add('show');
                } else {
                    errorMessageElement.textContent = '';
                    errorMessageElement.classList.remove('show');
                }
            }
            return hasError;
        };
        document.querySelectorAll('.queue-block').forEach(block => {
            const instanceNameInput = block.querySelector('.queue-instance-name');
            validateField(instanceNameInput, false, true, document.getElementById('queue-panel'));
            // No longer need to validate field names within the block
        });
    }
};