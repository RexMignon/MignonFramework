// app.js: 主应用程序控制器。

window.generateFinalCode = async function() {
    const ui = window.uiUtils;
    ui.showNotification('正在校验所有模块的配置...', 'success');
    const appState = window.getAppState();

    // ... (Config 和 ExecJS 的校验逻辑保持不变) ...
    if (appState.configs && Object.keys(appState.configs).length > 0) {
        for (const className in appState.configs) {
            const configData = appState.configs[className];
            if (!configData.managerName) {
                ui.showNotification(`错误: Config 类 "${className}" 缺少 "Manager Name"！`, 'error');
                return;
            }
            if (!className || className === 'UnnamedConfig') {
                ui.showNotification(`错误: 存在未命名的 "Class Name"！`, 'error');
                return;
            }
            if (!configData.fields || configData.fields.length === 0) {
                ui.showNotification(`错误: Config 类 "${className}" 至少需要一个字段！`, 'error');
                return;
            }
            for (const field of configData.fields) {
                if (!field.name) {
                    ui.showNotification(`错误: Config 类 "${className}" 中存在未命名的字段！`, 'error');
                    return;
                }
            }
        }
    }
    if (appState.execjs && appState.execjs.length > 0) {
        for (const [index, execjsData] of appState.execjs.entries()) {
            if (!execjsData.methodName) {
                ui.showNotification(`错误: ExecJS配置第 ${index + 1} 行缺少 "JS 方法名"！`, 'error');
                return;
            }
            if (execjsData.configClassName) {
                if (!execjsData.pathFromConfigField) {
                    ui.showNotification(`错误: ExecJS方法 "${execjsData.methodName}" 已关联Config类，但未选择字段作为JS文件路径！`, 'error');
                    return;
                }
            } else {
                if (!execjsData.staticPath) {
                    ui.showNotification(`错误: ExecJS方法 "${execjsData.methodName}" 缺少 "JS 文件路径"！`, 'error');
                    return;
                }
            }
        }
    }

    // ****** 新增: QueueIter 模块校验 ******
    if (appState.queueIters && Object.keys(appState.queueIters).length > 0) {
        for (const instanceName in appState.queueIters) {
            if (instanceName === 'UnnamedQueue') {
                ui.showNotification('错误: 存在未命名的 "QueueIter 实例名"！', 'error');
                return;
            }
            const queueData = appState.queueIters[instanceName];
            if (queueData.targets && queueData.targets.length > 0) {
                for (const [index, target] of queueData.targets.entries()) {
                    // --- FIXED: Validation now checks for targetName, which corresponds to the selected field ---
                    if (!target.targetName) {
                        ui.showNotification(`错误: 队列实例 "${instanceName}" 的第 ${index + 1} 个 @target 任务未选择要更新的"字段"！`, 'error');
                        return;
                    }
                }
            }
        }
    }

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

        ui.showNotification('太棒了！ZIP包已开始下载！', 'success');

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
        copyBtn: document.getElementById('copy-button'),
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
            if (window.Prism) Prism.highlightElement(elements.generatedCodeEl);
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

    function copyCode() {
        if (elements.generatedCodeEl) {
            try {
                const selection = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(elements.generatedCodeEl);
                selection.removeAllRanges();
                selection.addRange(range);
                document.execCommand('copy');
                selection.removeAllRanges();
                uiUtils.showNotification('代码已复制!');
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
        window.updateAllDynamicSelects();
    }

    if (elements.generateBtn) elements.generateBtn.addEventListener('click', convertAndRun);
    if (elements.viewCodeBtn) elements.viewCodeBtn.addEventListener('click', () => elements.codeModalOverlay.classList.add('active'));
    if (elements.closeModalBtn) elements.closeModalBtn.addEventListener('click', () => elements.codeModalOverlay.classList.remove('active'));
    if (elements.copyBtn) elements.copyBtn.addEventListener('click', copyCode);
});
