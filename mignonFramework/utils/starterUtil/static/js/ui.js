// ui.js: UI utility functions.

const uiUtils = {
    _notificationQueue: [],
    _activeNotificationCount: 0, // 跟踪当前显示的通知数量

    createDOMElement(tag, className, innerHTML = '') {
        const element = document.createElement(tag);
        if (className) {
            // Allows for multiple classes separated by space
            className.split(' ').forEach(cls => element.classList.add(cls));
        }
        if (innerHTML) {
            element.innerHTML = innerHTML;
        }
        return element;
    },

    createPanel(title, description = '') {
        const panel = this.createDOMElement('div', 'dynamic-panel');
        const header = this.createDOMElement('div', 'panel-header');
        const titleContainer = this.createDOMElement('div', 'panel-title-container');
        const titleEl = this.createDOMElement('h3', 'panel-title', title);

        titleContainer.appendChild(titleEl);

        if (description) {
            const descEl = this.createDOMElement('span', 'panel-description', description);
            titleContainer.appendChild(descEl);
        }

        header.appendChild(titleContainer);
        panel.appendChild(body); // corrected: append body here

        setTimeout(() => panel.classList.add('visible'), 100);

        return { element: panel, header, body };
    },

    createItemRow(options = {}) {
        const { className = '', gridTemplateColumns = '' } = options;
        const row = this.createDOMElement('div', `item-row ${className}`);
        if (gridTemplateColumns) {
            row.style.gridTemplateColumns = gridTemplateColumns;
        }
        return row;
    },

    createInput(type, className, placeholder) {
        const input = this.createDOMElement('input', className);
        input.type = type;
        input.placeholder = placeholder;
        return input;
    },

    createSecondaryButton(text, onClick) {
        const button = this.createDOMElement('button', 'secondary-button', text);
        if (onClick) {
            button.addEventListener('click', onClick);
        }
        return button;
    },

    createDeleteButton(onClick, text = '删除') {
        const button = this.createDOMElement('button', 'secondary-button delete-row-btn', text);
        if (onClick) {
            button.addEventListener('click', onClick);
        }
        return button;
    },

    updateSelectOptions(selectElement, optionsArray, defaultOptionText = '') {
        if (!selectElement) return;
        selectElement.innerHTML = ''; // 清空现有选项
        if (defaultOptionText) {
            selectElement.add(new Option(defaultOptionText, ''));
        }
        optionsArray.forEach(optionValue => {
            if (optionValue && optionValue !== 'UnnamedConfig') { // 确保不添加无效选项
                selectElement.add(new Option(optionValue, optionValue));
            }
        });
    },

    /**
     * 隐藏指定的通知元素。
     * @param {HTMLElement} notificationElement - 要隐藏的通知DOM元素。
     */
    hideNotification(notificationElement) {
        if (!notificationElement) return;

        // 清除该通知的自动隐藏定时器
        clearTimeout(notificationElement._hideTimeout);

        // 触发渐隐和滑出过渡
        notificationElement.classList.remove('show');
        notificationElement.classList.add('hide');

        // 等待渐隐动画完成 (0.25s)
        setTimeout(() => {
            // 触发收缩动画
            notificationElement.classList.remove('hide');
            notificationElement.classList.add('collapsing');

            // 设置初始高度，以便CSS动画可以从这个高度开始收缩
            notificationElement.style.setProperty('--notification-initial-height', `${notificationElement.scrollHeight}px`);

            // 等待收缩动画完成 (0.3s)
            notificationElement.addEventListener('animationend', function handler() {
                notificationElement.removeEventListener('animationend', handler);
                notificationElement.remove(); // 从DOM中移除
                uiUtils._activeNotificationCount--; // 减少活跃通知计数
                uiUtils._processNotificationQueue(); // 继续处理队列中的下一个通知
            }, { once: true }); // 确保事件监听器只触发一次
        }, 250); // 匹配 CSS 中的 hide 动画时间
    },

    /**
     * 处理通知队列，显示下一个通知。
     * @private
     */
    _processNotificationQueue() {
        // 如果队列为空，则不执行任何操作
        if (uiUtils._notificationQueue.length === 0) {
            return;
        }

        const { message, type, id } = uiUtils._notificationQueue.shift(); // 从队列中取出第一个通知

        // 获取通知堆栈容器
        let notificationStack = document.getElementById('notification-stack');
        if (!notificationStack) {
            notificationStack = uiUtils.createDOMElement('div', '');
            notificationStack.id = 'notification-stack';
            document.body.appendChild(notificationStack);
        }

        // 创建新的通知元素
        const notification = uiUtils.createDOMElement('div', 'notification');
        notification.id = `notification-${id}`; // 赋予唯一 ID
        notification.innerHTML = `<span class="notification-text">${message}</span>`; // 使用 class 而非 id

        // 将新通知添加到堆栈底部 (因为 flex-direction: column-reverse)
        notificationStack.appendChild(notification);
        uiUtils._activeNotificationCount++; // 增加活跃通知计数

        // 强制浏览器重绘，确保初始状态被应用，以便过渡动画能正确触发
        void notification.offsetWidth;

        // 应用类型和显示类
        notification.classList.add(type); // 应用类型类 (success/error)
        notification.classList.add('show'); // 触发进入动画

        // 设置自动隐藏的定时器
        notification._hideTimeout = setTimeout(() => {
            uiUtils.hideNotification(notification); // 将当前通知元素传递给隐藏函数
        }, 2500); // 通知显示 2.5 秒后开始渐隐
    },

    /**
     * 显示一个通知。
     * @param {string} message - 要显示的消息。
     * @param {'success' | 'error'} type - 通知类型，决定颜色。
     */
    showNotification(message, type = 'success') {
        // 生成一个唯一 ID
        const id = Date.now() + Math.random().toString(36).substring(2, 9);
        // 将新通知添加到队列
        uiUtils._notificationQueue.push({ message, type, id });
        // 立即尝试处理队列，新通知会立即出现（如果当前活跃通知数允许）
        uiUtils._processNotificationQueue();
    }
};

window.uiUtils = uiUtils;
