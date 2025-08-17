// app.js: 主应用程序控制器。

window.generateFinalCode = async function() {
    const ui = window.uiUtils;
    ui.showNotification('正在校验所有模块的配置...', 'success');
    const appState = window.getAppState();

    let hasValidationError = false; // 全局错误标志

    // Config 模块校验
    if (window.configModule && window.configModule.validate) {
        // configModule.validate() 会返回 true 如果有错误
        if (window.configModule.validate()) {
            hasValidationError = true;
            ui.showNotification('错误: Config 模块存在未填写的必填项或重复项！', 'error');
        }
    }

    // ExecJS 模块校验
    if (window.execjsModule && window.execjsModule.validate) {
        if (window.execjsModule.validate()) {
            hasValidationError = true;
            ui.showNotification('错误: ExecJS 模块存在未填写的必填项或重复项！', 'error');
        }
    }

    // QueueIter 模块校验
    if (window.queueModule && window.queueModule.validate) {
        if (window.queueModule.validate()) {
            hasValidationError = true;
            ui.showNotification('错误: QueueIter 模块存在未填写的必填项或重复项！', 'error');
        }
    }

    // Callback 模块校验
    if (window.callbackModule && window.callbackModule.validate) {
        if (window.callbackModule.validate()) {
            hasValidationError = true;
            ui.showNotification('错误: Callback 模块存在未填写的必填项或重复项！', 'error');
        }
    }

    // Main Request 模块校验
    if (window.mainRequestGeneratorModule && window.mainRequestGeneratorModule.validate) {
        if (window.mainRequestGeneratorModule.validate()) {
            hasValidationError = true;
            ui.showNotification('错误: Main Request 模块存在重复的 QueueIter 映射！', 'error');
        }
    }

    // Spider Generator 模块校验 (如果需要，目前没有独立的 validate 方法，但可以添加)
    // if (window.spiderGeneratorModule && window.spiderGeneratorModule.validate) {
    //     if (window.spiderGeneratorModule.validate()) {
    //         hasValidationError = true;
    //         ui.showNotification('错误: 请求字段映射模块存在未填写的必填项或重复项！', 'error');
    //     }
    // }

    // 如果存在任何校验错误，则停止生成代码
    if (hasValidationError) {
        console.error('Validation failed. Stopping code generation.');
        return; // 停止函数执行
    }


    // --- 原始的校验逻辑 (保留，如果模块内部没有 validate 方法，或者需要额外的全局校验) ---
    // Config 模块的额外校验（如果模块的validate方法不够详细）
    if (appState.configs && Object.keys(appState.configs).length > 0) {
        for (const className in appState.configs) {
            const configData = appState.configs[className];
            if (!configData.managerName) {
                ui.showNotification(`错误: Config 类 "${className}" 缺少 "Manager Name"！`, 'error');
                hasValidationError = true;
            }
            if (!className || className === 'UnnamedConfig') {
                ui.showNotification(`错误: 存在未命名的 "Class Name"！`, 'error');
                hasValidationError = true;
            }
            if (!configData.fields || configData.fields.length === 0) {
                ui.showNotification(`错误: Config 类 "${className}" 至少需要一个字段！`, 'error');
                hasValidationError = true;
            }
            for (const field of configData.fields) {
                if (!field.name) {
                    ui.showNotification(`错误: Config 类 "${className}" 中存在未命名的字段！`, 'error');
                    hasValidationError = true;
                }
            }
        }
    }
    // ExecJS 模块的额外校验
    if (appState.execjs && appState.execjs.length > 0) {
        for (const [index, execjsData] of appState.execjs.entries()) {
            if (!execjsData.methodName) {
                ui.showNotification(`错误: ExecJS配置第 ${index + 1} 行缺少 "JS 方法名"！`, 'error');
                hasValidationError = true;
            }
            if (execjsData.configClassName) {
                if (!execjsData.pathFromConfigField) {
                    ui.showNotification(`错误: ExecJS方法 "${execjsData.methodName}" 已关联Config类，但未选择字段作为JS文件路径！`, 'error');
                    hasValidationError = true;
                }
            } else {
                if (!execjsData.staticPath) {
                    ui.showNotification(`错误: ExecJS方法 "${execjsData.methodName}" 缺少 "JS 文件路径"！`, 'error');
                    hasValidationError = true;
                }
            }
        }
    }
    // QueueIter 模块的额外校验
    if (appState.queueIters && Object.keys(appState.queueIters).length > 0) {
        for (const instanceName in appState.queueIters) {
            if (instanceName === 'UnnamedQueue') {
                ui.showNotification('错误: 存在未命名的 "QueueIter 实例名"！', 'error');
                hasValidationError = true;
            }
            const queueData = appState.queueIters[instanceName];
            if (queueData.targets && queueData.targets.length > 0) {
                for (const [index, target] of queueData.targets.entries()) {
                    if (!target.targetName) {
                        ui.showNotification(`错误: 队列实例 "${instanceName}" 的第 ${index + 1} 个 @target 任务未选择要更新的"字段"！`, 'error');
                        hasValidationError = true;
                    }
                }
            }
        }
    }

    // 如果在额外的校验中也发现了错误，则停止生成代码
    if (hasValidationError) {
        console.error('Additional validation failed. Stopping code generation.');
        return; // 停止函数执行
    }
    // --- 原始校验逻辑结束 ---


    ui.showNotification('校验通过，正在请求后端生成ZIP包...', 'success');

    try {
        const response = await fetch('/generate_final_code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(appState)
        });

        if (!response.ok) {
            const result = await response.json().catch(() => ({ error: '无法解析的后端错误' }));
            throw new Error(result.error || `HTTP 错误! 状态: ${response.status}`);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = 'mignon_scraper.zip';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        ui.showNotification('代码已开始下载, Enjoy Request', 'success');

    } catch (error) {
        ui.showNotification(`代码生成失败: ${error.message}`, 'error');
        console.error('Final code generation failed:', error);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('transition-overlay');
    if (overlay) {
        requestAnimationFrame(() => {
            overlay.classList.add('hidden');
        });
    }

    const elements = {
        curlInput: document.getElementById('curl-input'),
        generateBtn: document.getElementById('generate-btn'),
        viewCodeBtn: document.getElementById('view-code-btn'),
        btnText: document.querySelector('#generate-btn .btn-text'),
        generatedCodeEl: document.getElementById('generated-code'),
        statusLight: document.getElementById('status-light'),
        codeLoader: document.getElementById('code-loader'),
        codeModalOverlay: document.getElementById('code-modal-overlay'),
        closeModalBtn: document.getElementById('close-modal-btn'),
        copyBtn: document.getElementById('copy-button'), // 获取复制按钮
        dynamicModulesContainer: document.getElementById('dynamic-modules-container')
    };

    async function convertAndRun() {
        const curlCommand = elements.curlInput.value.trim();
        if (!curlCommand) {
            uiUtils.showNotification('请输入cURL命令！', 'error');
            return;
        }

        elements.statusLight.className = 'status-light loading';
        elements.codeLoader.style.display = 'block';
        elements.btnText.textContent = '生成中';
        elements.generateBtn.disabled = true;
        elements.viewCodeBtn.disabled = true;

        try {
            const response = await fetch('/convert_and_run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ curl_command: curlCommand })
            });
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Unknown server error');
            }

            // FIX: Store all curl details, including the method, into the global state
            window.appState.curlDetails = {
                url: result.url || '',
                method: result.method || 'post', // <-- FIX: Store the method
                extracted_headers: result.extracted_headers || {},
                extracted_cookies: result.extracted_cookies || {},
                extracted_params: result.extracted_params || {},
                extracted_json_data: result.extracted_json_data || {}
            };

            elements.generatedCodeEl.textContent = result.generated_code;
            // 添加延迟，确保DOM更新和CSS应用完成后再高亮
            if (window.Prism) {
                setTimeout(() => {
                    Prism.highlightElement(elements.generatedCodeEl);
                }, 50); // 50ms 延迟
            }
            elements.viewCodeBtn.disabled = false;
            elements.statusLight.className = result.status_code && String(result.status_code).startsWith('2')
                ? 'status-light success'
                : 'status-light error';

            if (result.is_json) {
                uiUtils.showNotification('返回结果为Json数据');
            }

            if (window.spiderGeneratorModule && window.spiderGeneratorModule.populateExtractedFieldsTable) {
                const extractedDetails = {
                    headers: result.extracted_headers || {},
                    cookies: result.extracted_cookies || {},
                    jsonData: result.extracted_json_data || {},
                    params: result.extracted_params || {}
                };
                window.spiderGeneratorModule.populateExtractedFieldsTable(extractedDetails);
                uiUtils.showNotification('cURL 字段已从后端提取并映射！');
                // --- NEW: 在 cURL 字段提取后，也触发全局更新 ---
                window.updateAllDynamicSelects();
            }

        } catch (error) {
            elements.statusLight.className = 'status-light error';
            uiUtils.showNotification(`转换失败: ${error.message}`, 'error');
        } finally {
            elements.codeLoader.style.display = 'none';
            elements.btnText.textContent = '生成';
            elements.generateBtn.disabled = false;
        }
    }

    // 复制代码函数
    function copyCode() {
        if (elements.generatedCodeEl) {
            try {
                // 使用 document.execCommand('copy') 兼容性更好
                const selection = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(elements.generatedCodeEl);
                selection.removeAllRanges();
                selection.addRange(range);
                document.execCommand('copy');
                selection.removeAllRanges(); // 清除选择

                // 显示复制成功提示
                const copyTooltip = elements.copyBtn.querySelector('.copy-tooltip');
                if (copyTooltip) {
                    copyTooltip.classList.add('copied');
                    setTimeout(() => {
                        copyTooltip.classList.remove('copied');
                    }, 2000); // 2秒后隐藏提示
                }
                uiUtils.showNotification('代码已复制!'); // 使用统一的通知系统
            } catch (err) {
                uiUtils.showNotification('复制失败!', 'error');
                console.error('Failed to copy text: ', err);
            }
        }
    }

    if (elements.dynamicModulesContainer) {
        window.configModule.init(elements.dynamicModulesContainer);
        window.execjsModule.init(elements.dynamicModulesContainer);
        window.queueModule.init(elements.dynamicModulesContainer);
        window.callbackModule.init(elements.dynamicModulesContainer);
        if (window.preCheckGeneratorModule) {
            window.preCheckGeneratorModule.init(elements.dynamicModulesContainer);
        }
        if (window.insertQuickModule) {
            window.insertQuickModule.init(elements.dynamicModulesContainer);
        }
        if (window.mainRequestGeneratorModule) {
            window.mainRequestGeneratorModule.init(elements.dynamicModulesContainer);
        }
        if (window.spiderGeneratorModule) {
            window.spiderGeneratorModule.init(elements.dynamicModulesContainer);
        }
        // --- NEW: 在所有模块初始化完成后，统一调用一次全局更新 ---
        window.updateAllDynamicSelects();
    }

    if (elements.generateBtn) elements.generateBtn.addEventListener('click', convertAndRun);
    if (elements.viewCodeBtn) {
        elements.viewCodeBtn.addEventListener('click', () => {
            elements.codeModalOverlay.classList.add('active');
            // 在打开模态框时，强制重新高亮代码，以解决潜在的加载时序问题
            if (window.Prism) {
                setTimeout(() => {
                    Prism.highlightElement(elements.generatedCodeEl);
                }, 50); // 50ms 延迟
            }
        });
    }
    if (elements.closeModalBtn) elements.closeModalBtn.addEventListener('click', () => elements.codeModalOverlay.classList.remove('active'));
    // 绑定复制按钮的点击事件
    if (elements.copyBtn) elements.copyBtn.addEventListener('click', copyCode);

    // --- NEW: 监听自定义事件，触发全局更新 ---
    document.addEventListener('configUpdated', () => {
        console.log('Config data updated, triggering global select refresh.');
        window.updateAllDynamicSelects();
    });

    document.addEventListener('queueItersUpdated', () => {
        console.log('QueueIters data updated, triggering global select refresh.');
        window.updateAllDynamicSelects();
    });
});


window.updateAllDynamicSelects = function() {
    const state = window.getAppState();
    const configNames = Object.keys(state.configs);
    const queueIterNames = Object.keys(state.queueIters);

    // 更新 ExecJS Config Selects
    if (window.execjsModule && window.execjsModule.updateAllConfigSelects) {
        window.execjsModule.updateAllConfigSelects();
    }

    // 更新 QueueIter 的内部 Config Selects 和 Field Selects
    document.querySelectorAll('.queue-config-select').forEach(select => {
        if (select.disabled) return;
        const currentVal = select.value;
        uiUtils.updateSelectOptions(select, configNames, '选择 Config');
        if (configNames.includes(currentVal)) {
            select.value = currentVal;
        }
        // 显式调用 updateFieldSelect 来更新关联的字段下拉菜单
        const row = select.closest('.item-row');
        const fieldSelect = row.querySelector('.queue-field-select');
        if (window.queueModule && window.queueModule.updateFieldSelect) {
            window.queueModule.updateFieldSelect(select.value, fieldSelect);
        }
        // 移除 dispatchEvent，因为我们已经显式更新了
        // select.dispatchEvent(new Event('change'));
    });

    // --- FIX: 更新 Callback 的 QueueIter Selects ---
    if (window.callbackModule && window.callbackModule.updateAllQueueIterSelects) {
        window.callbackModule.updateAllQueueIterSelects();
    }

    // 更新 Callback 的 Config Selects 和 Field Selects
    document.querySelectorAll('.callback-config-select').forEach(select => {
        if (select.disabled) return;
        const currentVal = select.value;
        uiUtils.updateSelectOptions(select, configNames, '选择 Config');
        if (configNames.includes(currentVal)) {
            select.value = currentVal;
        }
        // 显式调用 updateFieldSelect 来更新关联的字段下拉菜单
        const row = select.closest('.item-row');
        const fieldSelect = row.querySelector('.callback-field-select');
        if (window.callbackModule && window.callbackModule.updateFieldSelect) {
            window.callbackModule.updateFieldSelect(select.value, fieldSelect);
        }
        // 移除 dispatchEvent，因为我们已经显式更新了
        // select.dispatchEvent(new Event('change'));
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
