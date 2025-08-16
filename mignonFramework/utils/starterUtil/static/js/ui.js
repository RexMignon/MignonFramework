// ui.js: UI utility functions.

const uiUtils = {
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
        panel.appendChild(header);

        const body = this.createDOMElement('div', 'panel-body');
        panel.appendChild(body);

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

    // ****** 关键新增：补全这个缺失的核心功能函数 ******
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

    showNotification(message, type = 'success') {
        const notification = document.getElementById('notification');
        const notificationText = document.getElementById('notification-text');
        if (notification && notificationText) {
            notificationText.textContent = message;
            notification.className = `notification ${type}`; // Reset classes
            notification.classList.add('show');
            setTimeout(() => {
                notification.classList.remove('show');
            }, 3000);
        }
    }
};

window.uiUtils = uiUtils;
