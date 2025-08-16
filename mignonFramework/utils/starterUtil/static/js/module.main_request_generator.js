// module.main_request_generator.js: 处理主请求模块的 UI 和逻辑。

window.mainRequestGeneratorModule = {
    /**
     * 初始化主请求面板。
     * @param {HTMLElement} container - 动态模块的容器元素。
     */
    init(container) {
        // 创建主面板元素
        const panel = uiUtils.createDOMElement('div', 'dynamic-panel', `
            <div class="panel-header">
                <div style="display: flex; align-items: baseline;">
                    <h3 class="panel-title" style="font-size: 1.2rem;">主请求 (Main Request)</h3>
                    <span class="panel-description">配置主请求函数 (requestTo) 与 QueueIter 的交互</span>
                </div>
                <button id="add-main-request-queue-btn" class="secondary-button" style="padding: 0.5rem 1rem;">新增 QueueIter 映射</button>
            </div>

            <div class="item-list">
                <div class="item-header main-request-row">
                    <span>关联 QueueIter</span>
                    <span>是否触发回调</span>
                    <span>排序</span>
                    <span>操作</span>
                </div>
                <div class="item-list" id="main-request-queue-list">
                    
                </div>
            </div>
        `);
        panel.id = 'main-request-generator-panel';
        container.appendChild(panel);

        // 获取元素引用
        const addQueueBtn = panel.querySelector('#add-main-request-queue-btn');
        const queueList = panel.querySelector('#main-request-queue-list');

        // 绑定事件监听器
        addQueueBtn.addEventListener('click', () => this.addQueueConfigRow(queueList));

        // 委托事件处理，用于处理动态添加的行
        queueList.addEventListener('change', e => {
            const target = e.target;
            if (target.classList.contains('main-request-queue-select')) {
                // 当 QueueIter 选择改变时，更新其关联的回调触发状态
                const row = target.closest('.item-row');
                const triggerSelect = row.querySelector('.main-request-trigger-callback-select');
                // 在这里直接调用 updateCallbackTriggerState，确保获取最新的 state
                this.updateCallbackTriggerState(target.value, triggerSelect);
                this.validate(); // 验证重复选择
            }
        });
        queueList.addEventListener('click', e => {
            if (e.target.classList.contains('delete-row-btn')) {
                e.target.closest('.item-row').remove();
                this.validate(); // 删除行后验证
            }
        });

        // 确保面板可见
        setTimeout(() => panel.classList.add('visible'), 600); // 稍微延迟，避免与其他模块动画冲突

        // 首次加载时，添加一个默认的 QueueIter 映射行
        this.addQueueConfigRow(queueList);
        // 首次加载后，updateAllDynamicSelects 会在 app.js 中调用，它会反过来调用此模块的 updateAllQueueIterSelects
    },

    /**
     * 添加一个新的 QueueIter 配置行到列表中。
     * @param {HTMLElement} container - 列表的容器元素。
     */
    addQueueConfigRow(container) {
        const rowHTML = `
            <select class="main-request-queue-select">
                <option value="">选择 QueueIter</option>
            </select>
            <select class="main-request-trigger-callback-select">
                <option value="">-</option> {# 初始显示为 - #}
            </select>
            <input type="number" class="main-request-param-sort" value="0" min="0">
            <button type="button" class="secondary-button delete-row-btn">删除</button>
        `;
        const newRow = uiUtils.createDOMElement('div', 'item-row main-request-row', rowHTML);
        container.appendChild(newRow);

        // 新增行后，立即更新其 QueueIter 下拉菜单，并设置回调触发状态
        const queueSelect = newRow.querySelector('.main-request-queue-select');
        const triggerSelect = newRow.querySelector('.main-request-trigger-callback-select');
        this.updateQueueIterSelectForRow(queueSelect);
        // 初始状态下，回调触发下拉框应被禁用
        triggerSelect.disabled = true;
        this.validate(); // 新增行后验证
    },

    /**
     * 更新单个行中的 QueueIter 实例选择下拉菜单。
     * @param {HTMLElement} selectElement - 当前行的 QueueIter 选择下拉菜单元素。
     */
    updateQueueIterSelectForRow(selectElement) {
        if (!selectElement) return;

        const currentVal = selectElement.value;
        selectElement.innerHTML = '<option value="">选择 QueueIter</option>'; // 清空并添加默认选项

        const state = window.getAppState ? window.getAppState() : { queueIters: {} };
        const queueIterNames = Object.keys(state.queueIters);

        queueIterNames.forEach(name => {
            const option = new Option(name, name);
            selectElement.add(option);
        });

        // 恢复之前的选择（如果存在且有效）
        if (queueIterNames.includes(currentVal)) {
            selectElement.value = currentVal;
        }
        // 注意：这里不再触发 change 事件，因为 updateAllQueueIterSelects 会统一处理回调状态更新
    },

    /**
     * 更新所有 QueueIter 实例选择下拉菜单。
     * 这个方法会被 window.updateAllDynamicSelects 调用。
     */
    updateAllQueueIterSelects() {
        document.querySelectorAll('.main-request-queue-select').forEach(selectElement => {
            this.updateQueueIterSelectForRow(selectElement);
            // 确保在更新完 QueueIter 选项后，也更新对应的回调触发状态
            const row = selectElement.closest('.item-row');
            const triggerSelect = row.querySelector('.main-request-trigger-callback-select');
            this.updateCallbackTriggerState(selectElement.value, triggerSelect);
        });
    },

    /**
     * 根据选定的 QueueIter 实例更新“是否触发回调”下拉框的状态。
     * @param {string} selectedQueueIterName - 选定的 QueueIter 实例名称。
     * @param {HTMLElement} triggerSelect - “是否触发回调”的下拉框元素。
     */
    updateCallbackTriggerState(selectedQueueIterName, triggerSelect) {
        if (!triggerSelect) return;

        // 每次调用时都重新获取最新的 appState
        const state = window.getAppState();
        // 检查是否有与 selectedQueueIterName 关联的回调方法
        const hasAssociatedCallbackMethod = state.callbacks[selectedQueueIterName] && state.callbacks[selectedQueueIterName].length > 0;

        if (hasAssociatedCallbackMethod) {
            triggerSelect.disabled = false;
            const currentVal = triggerSelect.value; // 保存当前值
            triggerSelect.innerHTML = `
                <option value="yes">是</option>
                <option value="no">否</option>
            `;
            // 恢复之前的选择，如果之前是 'yes' 或 'no'
            if (currentVal === 'yes' || currentVal === 'no') {
                triggerSelect.value = currentVal;
            } else {
                triggerSelect.value = 'no'; // 默认选择“否”
            }
        } else {
            triggerSelect.disabled = true;
            triggerSelect.innerHTML = '<option value="">-</option>'; // 没有回调时显示 -
        }
    },

    /**
     * 验证主请求模块的输入。
     */
    validate() {
        const checkDuplicates = (selector, errorMsg, scope = document) => {
            const allInputs = scope.querySelectorAll(selector);
            const names = new Map();
            allInputs.forEach(input => {
                const name = input.value.trim();
                // 只有当输入有值时才进行重复检查
                if (name) names.set(name, (names.get(name) || 0) + 1);
            });
            allInputs.forEach(input => {
                const name = input.value.trim();
                const wasInError = input.classList.contains('input-error');
                if (name && names.get(name) > 1) {
                    if (!wasInError) {
                        input.classList.add('input-error');
                        uiUtils.showNotification(`${errorMsg}: "${name}"`, 'error');
                    }
                } else {
                    input.classList.remove('input-error');
                }
            });
        };

        // 验证 QueueIter 实例选择是否有重复
        const queueList = document.getElementById('main-request-queue-list');
        if (queueList) {
            checkDuplicates('.main-request-queue-select', '主请求中关联的 QueueIter 实例重复', queueList);
        }
    }
};
