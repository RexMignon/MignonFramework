// module.pre_check_generator.js: 处理预检请求模块的 UI 和逻辑。

window.preCheckGeneratorModule = {
    /**
     * 初始化预检请求面板。
     * @param {HTMLElement} container - 动态模块的容器元素。
     */
    init(container) {
        // 创建主面板元素
        const panel = uiUtils.createDOMElement('div', 'dynamic-panel', `
            <div class="panel-header">
                <div style="display: flex; align-items: baseline;">
                    <h3 class="panel-title" style="font-size: 1.2rem;">预检请求 (Pre-Check Request)</h3>
                    <span class="panel-description">配置是否包含预检请求函数 (preCheckRequest) 用于获取总数(用于分页爬取的场景)</span>
                </div>
            </div>

            <div class="item-list">
                <div class="item-row spider-feature-row">
                    <span>预检请求</span>
                    <select id="include-pre-check-request" class="form-control">
                        <option value="yes">是</option>
                        <option value="no" selected>否</option>
                    </select>
                </div>
            </div>
        `);
        panel.id = 'pre-check-generator-panel';
        container.appendChild(panel);

        // 确保面板可见
        // 延迟显示，以确保其他模块初始化完成并避免动画冲突
        setTimeout(() => panel.classList.add('visible'), 100);
    },

    /**
     * 获取预检请求模块的当前状态。
     * @returns {boolean} 如果选中了预检请求，则返回 true，否则返回 false。
     */
    getIncludeState() {
        const select = document.getElementById('include-pre-check-request');
        return select ? select.value === 'yes' : false;
    }
};
