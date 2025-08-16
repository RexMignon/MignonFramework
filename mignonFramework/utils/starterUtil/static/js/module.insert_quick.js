// module.insert_quick.js: 处理 InsertQuick 模块的 UI 和逻辑。

window.insertQuickModule = {
    /**
     * 初始化 InsertQuick 面板。
     * @param {HTMLElement} container - 动态模块的容器元素。
     */
    init(container) {
        // 创建主面板元素
        const panel = uiUtils.createDOMElement('div', 'dynamic-panel', `
            <div class="panel-header">
                <div style="display: flex; align-items: baseline;">
                    <h3 class="panel-title" style="font-size: 1.2rem;">InsertQuick 功能</h3>
                    <span class="panel-description">配置是否包含 InsertQuick 函数</span>
                </div>
            </div>

            <div class="item-list">
                <div class="item-row spider-feature-row">
                    <span>是否需要 InsertQuick 功能</span>
                    <select id="include-insert-quick" class="form-control">
                        <option value="yes">是</option>
                        <option value="no" selected>否</option>
                    </select>
                </div>
            </div>
        `);
        panel.id = 'insert-quick-generator-panel';
        container.appendChild(panel);

        // 确保面板可见
        // 延迟显示，以确保其他模块初始化完成并避免动画冲突
        setTimeout(() => panel.classList.add('visible'), 100); // 可以调整延迟时间
    },

    /**
     * 获取 InsertQuick 模块的当前状态。
     * @returns {boolean} 如果选中了 InsertQuick，则返回 true，否则返回 false。
     */
    getIncludeState() {
        const select = document.getElementById('include-insert-quick');
        return select ? select.value === 'yes' : false;
    }
};
