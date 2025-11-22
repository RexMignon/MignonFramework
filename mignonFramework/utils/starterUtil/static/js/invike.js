const express = require('express');
const app = express();
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const os = require('os');
// 引入内置的 createRequire
const { createRequire } = require('module');

app.use(bodyParser.json());
const loadedModules = {};

// 动态获取当前脚本的路径
const currentScriptPath = process.argv[1];

// 命令行参数处理
// process.argv[2]: scriptsDir
// process.argv[3]: node_modules_path (可能是空字符串 "")
// process.argv[4]: url_base

const arg2 = process.argv[2];
// 如果 arg2 是空字符串，回退到默认目录
const scriptsDir = (arg2 && arg2.trim() !== '') ? path.resolve(arg2) : path.resolve(process.cwd(), './resources/js');

const arg3 = process.argv[3];
// 【核心逻辑】：如果 arg3 是空字符串 ""，则 nodeModulesPath 为 null。
// 这样后续代码就会跳过 NODE_PATH 设置，实现你想要的"默认扫"(Node原生递归查找)。
const nodeModulesPath = (arg3 && arg3.trim() !== '') ? path.resolve(arg3) : null;

const urlBase = process.argv[4];

let port = 3000;
let listenAddress = '0.0.0.0';

// 解析端口
if (urlBase) {
    try {
        const url = new URL(urlBase);
        if (url.port) {
            port = parseInt(url.port, 10);
        } else {
            port = (url.protocol === 'https:') ? 443 : 80;
        }
    } catch (e) {
        port = process.env.PORT || 3000;
    }
} else {
    port = process.env.PORT || 3000;
}

// 设置 NODE_PATH
// 只有当 nodeModulesPath 真的存在时才设置，否则完全保留 Node.js 原生行为
if (nodeModulesPath) {
    if (fs.existsSync(nodeModulesPath)) {
        console.log(`Setting up NODE_PATH to: ${nodeModulesPath}`);
        process.env.NODE_PATH = nodeModulesPath + (process.env.NODE_PATH ? path.delimiter + process.env.NODE_PATH : '');
        require('module')._initPaths();
    } else {
        console.warn(`Warning: Specified node_modules directory not found: ${nodeModulesPath}`);
    }
} else {
    // 这就是你要的：不设置 NODE_PATH，让它默认去扫
    console.log("No specific node_modules path provided, using default Node.js module resolution.");
}

function loadScripts(directory) {
    if (!fs.existsSync(directory)) {
        console.error(`Error: Directory not found: ${directory}`);
        return;
    }
    fs.readdirSync(directory).forEach(file => {
        const ext = path.extname(file);
        if (ext === '.js' || ext === '.jsx') {
            const moduleName = path.basename(file, ext);
            const scriptPath = path.join(directory, file);

            // 跳过服务器文件
            if (path.resolve(scriptPath) === path.resolve(__filename)) {
                return;
            }

            try {
                const scriptCode = fs.readFileSync(scriptPath, 'utf-8');
                const module = { exports: {} };
                const __dirname = path.dirname(scriptPath);
                const __filename = scriptPath;

                // **核心修改：使用 createRequire**
                // 创建一个专属的 require，基准路径锚定在 scriptPath
                // 这样它就会自动去该脚本所在的目录查找 node_modules，完全符合原生行为
                const scriptRequire = createRequire(scriptPath);

                // 构造一个函数工厂，而不是直接 eval 执行
                // 这样我们可以把 scriptRequire 干净地注入进去
                const wrappedCode = `(function(exports, require, module, __filename, __dirname) {
                    ${scriptCode}
                })`;

                // eval 返回这个函数
                const factory = eval(wrappedCode);

                // 执行函数，传入我们要注入的 scriptRequire
                factory(module.exports, scriptRequire, module, __filename, __dirname);

                loadedModules[moduleName] = module.exports;
                console.log(`Loaded module: ${moduleName}`);
            } catch (e) {
                console.error(`Error loading script ${file}: ${e.message}`);
            }
        }
    });
}

loadScripts(scriptsDir);

app.post('/:filename/invoke', async (req, res) => {
    try {
        const { filename } = req.params;
        const { func_name, args = [] } = req.body;
        console.log(`${req.path} was accessed.`)
        if (!loadedModules[filename]) {
            return res.status(404).json({ success: false, error: `Module '${filename}' not found.` });
        }

        const module = loadedModules[filename];
        if (typeof module[func_name] === 'function') {
            const result = await module[func_name](...args);
            res.json({ success: true, result });
        } else {
            res.status(404).json({ success: false, error: `Function '${func_name}' not found in module '${filename}'.` });
        }
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/status', (req, res) => {
    res.json({ status: 'running', service_name: 'js_invoker_microservice' });
});

app.listen(port, '0.0.0.0', () => {
    const listenAddress = '0.0.0.0';
    console.log(`Namespaced invoker service is running on http://${listenAddress}:${port}`);
    console.log(`Scanning directory: ${scriptsDir}`);

    console.log("scanned result:")
    console.log(loadedModules)
    console.log("If the result is missing, please check whether the module has the same name and whether there are exports before the method.")

    if (listenAddress === '0.0.0.0') {
        const networkInterfaces = os.networkInterfaces();
        const localIps = new Set();
        localIps.add('127.0.0.1');

        for (const interfaceName in networkInterfaces) {
            const ifaces = networkInterfaces[interfaceName];
            for (const iface of ifaces) {
                if (iface.family === 'IPv4' && !iface.internal) {
                    if (iface.address.startsWith('192.168.') || iface.address.startsWith('10.') || iface.address.startsWith('172.')) {
                        localIps.add(iface.address);
                    }
                }
            }
        }
        const sortedLocalIps = Array.from(localIps).sort();

        console.log('--- Local network address ---');
        sortedLocalIps.forEach(ip => {
            console.log(`  - http://${ip}:${port}`);
        });
        console.log('-----------------------------');
    }
});