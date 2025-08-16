// state.js: 应用程序的简单共享状态。

window.appState = {
    configs: {},
    execjs: [],
    queueIters: {},
    callbacks: {},
    curlDetails: {
        url: '',
        method: 'post',
        extracted_headers: {},
        extracted_cookies: {},
        extracted_params: {},
        extracted_json_data: {}
    },
    extractedFields: {
        headers: [],
        cookies: [],
        params: [],
        jsonData: []
    },
    preCheckRequestEnabled: false,
    insertQuickEnabled: false,
    mainRequest: {
        mappings: []
    }
};

/**
 * 从 DOM 读取当前状态并更新全局 appState 对象。
 * @returns {object} 当前应用程序状态。
 */
window.getAppState = function() {
    // 获取 Configs 状态
    const configBlocks = {};
    document.querySelectorAll('.config-block').forEach(block => {
        const managerNameInput = block.querySelector('.config-manager-name');
        const classNameInput = block.querySelector('.config-class-name');
        const managerIniPathInput = block.querySelector('.config-manager-ini-path-input');

        if (!managerNameInput || !classNameInput || !managerIniPathInput) return;

        const className = classNameInput.value.trim() || 'UnnamedConfig';
        const managerName = managerNameInput.value.trim() || 'unnamed_config';
        const managerIniPath = managerIniPathInput.value.trim();
        const fields = [];
        block.querySelectorAll('.item-row.config-row').forEach(row => {
            const nameInput = row.querySelector('.config-field-name');
            const defaultValueInput = row.querySelector('.config-field-default-value');
            const typeSelect = row.querySelector('.config-field-type-select');

            if (nameInput && nameInput.value.trim() && typeSelect) {
                fields.push({
                    name: nameInput.value.trim(),
                    type: typeSelect.value,
                    default: defaultValueInput ? defaultValueInput.value : ''
                });
            }
        });
        configBlocks[className] = {
            managerName: managerName,
            managerIniPath: managerIniPath,
            fields: fields
        };
    });
    window.appState.configs = configBlocks;

    // 获取 ExecJS 状态
    const execjsConfigs = [];
    document.querySelectorAll('#execjs-list .item-row.execjs-row').forEach(row => {
        const methodNameInput = row.querySelector('.execjs-method-name');
        if (!methodNameInput || !methodNameInput.value.trim()) return;

        const configSelect = row.querySelector('.execjs-config-select');
        const pathContainer = row.querySelector('.execjs-path-container');
        if (!pathContainer || !configSelect) return;

        const pathInput = pathContainer.querySelector('input[type="text"]');
        const pathSelect = pathContainer.querySelector('select');
        const tags = Array.from(row.querySelectorAll('.tag-input-container .tag')).map(tag => tag.textContent.slice(0, -1).trim());

        execjsConfigs.push({
            methodName: methodNameInput.value.trim(),
            params: tags,
            configClassName: configSelect.value,
            staticPath: pathInput ? pathInput.value.trim() : '',
            pathFromConfigField: pathSelect ? pathSelect.value : ''
        });
    });
    window.appState.execjs = execjsConfigs;

    // 获取 QueueIters 状态
    const queueIters = {};
    document.querySelectorAll('.queue-block').forEach(block => {
        const instanceNameInput = block.querySelector('.queue-instance-name');
        if (!instanceNameInput) return;
        const instanceName = instanceNameInput.value.trim() || 'UnnamedQueue';

        const targets = [];
        block.querySelectorAll('.item-row.queue-target-row').forEach(row => {
            const isTargetEnabledSelect = row.querySelector('.queue-target-select');
            const configSelect = row.querySelector('.queue-config-select');
            const fieldSelect = row.querySelector('.queue-field-select');
            const defaultValueInput = row.querySelector('.queue-default-value');

            if (!isTargetEnabledSelect || !configSelect || !fieldSelect || !defaultValueInput) return;

            const isTargetEnabled = isTargetEnabledSelect.value === 'yes';
            const configFieldName = fieldSelect.value.trim();

            if (isTargetEnabled && configSelect.value && configFieldName) {
                targets.push({
                    enabled: isTargetEnabled,
                    configClassName: configSelect.value,
                    targetName: configFieldName,
                    configFieldName: configFieldName,
                    defaultValue: defaultValueInput.value.trim()
                });
            }
        });
        queueIters[instanceName] = { targets: targets };
    });
    window.appState.queueIters = queueIters;

    // 获取 Callbacks 状态
    const callbacks = {};
    document.querySelectorAll('#callback-list .item-row.callback-row').forEach(row => {
        const methodNameInput = row.querySelector('.callback-method-name');
        const queueSelect = row.querySelector('.callback-queue-select');
        if (!methodNameInput || !queueSelect) return;

        const methodName = methodNameInput.value.trim();
        const queueIterName = queueSelect.value.trim();
        if (methodName && queueIterName) {
            const configToggle = row.querySelector('.callback-config-toggle');
            const configSelect = row.querySelector('.callback-config-select');
            const fieldSelect = row.querySelector('.callback-field-select');
            const assignValueInput = row.querySelector('.callback-assign-value');

            if (!callbacks[queueIterName]) {
                callbacks[queueIterName] = [];
            }
            callbacks[queueIterName].push({
                methodName: methodName,
                isConfigEnabled: configToggle ? configToggle.value === 'yes' : false,
                configClassName: configSelect ? configSelect.value : '',
                configFieldName: fieldSelect ? fieldSelect.value : '',
                assignValue: assignValueInput ? assignValueInput.value : ''
            });
        }
    });
    window.appState.callbacks = callbacks;

    // 获取请求字段映射的状态
    const extractedFieldsByType = {
        headers: [],
        cookies: [],
        params: [],
        jsonData: []
    };
    document.querySelectorAll('.field-sections-container .item-row.extracted-field-row').forEach(row => {
        const fieldNameInput = row.querySelector('.extracted-field-name-input');
        const sourceType = row.dataset.sourceType;
        if (!fieldNameInput || !sourceType || !extractedFieldsByType[sourceType]) return;

        const fieldName = fieldNameInput.value.trim();
        if (fieldName) {
            const configSelect = row.querySelector('.extracted-field-config-select');
            const configFieldSelect = row.querySelector('.extracted-field-config-field-select');

            extractedFieldsByType[sourceType].push({
                fieldName: fieldName,
                configClassName: configSelect ? configSelect.value.trim() : '',
                configFieldName: configFieldSelect ? configFieldSelect.value.trim() : '',
                isDeleted: row.classList.contains('deleted-row'),
                sourceType: sourceType
            });
        }
    });
    window.appState.extractedFields = extractedFieldsByType;

    // 获取 Pre-Check Request 状态
    const preCheckSelect = document.getElementById('include-pre-check-request');
    if (preCheckSelect) {
        window.appState.preCheckRequestEnabled = preCheckSelect.value === 'yes';
    }

    // 获取 InsertQuick 状态
    const insertQuickSelect = document.getElementById('include-insert-quick');
    if (insertQuickSelect) {
        window.appState.insertQuickEnabled = insertQuickSelect.value === 'yes';
    }

    // FIX: 直接从 DOM 获取 Main Request 状态，这是最可靠的方式
    const mainRequestMappings = [];
    // 使用更精确的选择器 '#main-request-queue-list .item-row.main-request-row' 来避免选中表头
    document.querySelectorAll('#main-request-queue-list .item-row.main-request-row').forEach(row => {
        const queueSelect = row.querySelector('.main-request-queue-select');
        // 修正 #1: 正确的 class 是 'main-request-trigger-callback-select'
        const callbackSelect = row.querySelector('.main-request-trigger-callback-select');
        // 修正 #2: 正确的 class 是 'main-request-param-sort'
        const sortInput = row.querySelector('.main-request-param-sort');

        if (queueSelect && callbackSelect && sortInput && queueSelect.value) {
            mainRequestMappings.push({
                queueIterName: queueSelect.value,
                triggerCallback: callbackSelect.value === 'yes',
                sort: sortInput.value.trim() || '0'
            });
        }
    });
    window.appState.mainRequest.mappings = mainRequestMappings;


    return window.appState;
};


window.updateAllDynamicSelects = function() {
    const state = window.getAppState();
    const configNames = Object.keys(state.configs);
    const queueIterNames = Object.keys(state.queueIters);

    // 更新 ExecJS Config Selects
    document.querySelectorAll('.execjs-config-select').forEach(select => {
        const currentVal = select.value;
        uiUtils.updateSelectOptions(select, configNames, '无');
        if (configNames.includes(currentVal)) {
            select.value = currentVal;
        }
        select.dispatchEvent(new Event('change'));
    });

    // 更新 QueueIter 的内部 Config Selects
    document.querySelectorAll('.queue-config-select').forEach(select => {
        if (select.disabled) return;
        const currentVal = select.value;
        uiUtils.updateSelectOptions(select, configNames, '选择 Config');
        if (configNames.includes(currentVal)) {
            select.value = currentVal;
        }
        select.dispatchEvent(new Event('change'));
    });

    // 更新 Callback 的 QueueIter Selects
    document.querySelectorAll('.callback-queue-select').forEach(select => {
        const currentVal = select.value;
        uiUtils.updateSelectOptions(select, queueIterNames, '选择 QueueIter');
        if (queueIterNames.includes(currentVal)) {
            select.value = currentVal;
        }
        select.dispatchEvent(new Event('change'));
    });

    // 更新 Callback 的 Config Selects
    document.querySelectorAll('.callback-config-select').forEach(select => {
        if (select.disabled) return;
        const currentVal = select.value;
        uiUtils.updateSelectOptions(select, configNames, '选择 Config');
        if (configNames.includes(currentVal)) {
            select.value = currentVal;
        }
        select.dispatchEvent(new Event('change'));
    });

    // 更新 Main Request 的 QueueIter Selects
    if (window.mainRequestGeneratorModule && window.mainRequestGeneratorModule.updateAllQueueIterSelects) {
        setTimeout(() => {
            window.mainRequestGeneratorModule.updateAllQueueIterSelects();
        }, 50);
    }

    // 更新 Spider Generator (请求字段映射) 的提取字段 Config Selects
    if (window.spiderGeneratorModule && window.spiderGeneratorModule.updateAllExtractedFieldsConfigSelects) {
        window.spiderGeneratorModule.updateAllExtractedFieldsConfigSelects();
    }
};
