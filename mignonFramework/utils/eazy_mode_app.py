# eazy_mode_app.py
import json
import re
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

# 虚拟的DDL解析器作为备用
from mignonFramework.utils.SqlDDL2List import extract_column_names_from_ddl


# --- 关键修复：将完整的HTML和CSS放在这里 ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mignonFramework - Eazy Mode</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fira+Code:wght@600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        :root {
            --bg-color: #f7f8fa; --card-bg-color: #ffffff; --text-color: #111827; --text-secondary: #6b7280;
            --primary-color: #2563eb; --primary-hover: #1d4ed8; --border-color: #e5e7eb;
            --success-color: #16a34a; --warning-color: #f59e0b;
            --font-family: 'Inter', sans-serif; --font-mono: 'Fira Code', 'SFMono-Regular', Consolas, monospace;
        }
        *, *::before, *::after { box-sizing: border-box; }
        body { background-color: var(--bg-color); color: var(--text-color); font-family: var(--font-family); margin: 0; padding: 2rem 1rem; }
        .container { max-width: 1600px; margin: auto; }
        .header { text-align: center; margin-bottom: 2rem; }
        .header pre {
            font-family: var(--font-mono); font-weight: 700; font-size: 0.9rem; line-height: 1.2;
            color: #4b5563; text-align: left; display: inline-block; white-space: pre;
            background-color: transparent; border: none; padding: 0;
        }
        .main-layout { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: 2rem; align-items: flex-start; }
        .config-panel, .output-panel { display: flex; flex-direction: column; gap: 2rem; }
        .output-panel { position: sticky; top: 2rem; max-height: 90vh; overflow-y: auto; }
        .card { background-color: var(--card-bg-color); border: 1px solid var(--border-color); border-radius: 0.75rem; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.07), 0 1px 2px -1px rgba(0,0,0,0.07); }
        .card-header { padding: 1rem 1.5rem; border-bottom: 1px solid var(--border-color); font-size: 1.125rem; font-weight: 600; display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
        .card-body { padding: 1.5rem; }
        .form-control, .search-input { width: 100%; background-color: #fff; color: var(--text-color); border: 1px solid #d1d5db; border-radius: 0.5rem; padding: 0.625rem 0.875rem; transition: all 0.2s; }
        .form-control:focus, .search-input:focus { outline: 2px solid transparent; outline-offset: 2px; box-shadow: 0 0 0 2px var(--bg-color), 0 0 0 4px var(--primary-color); border-color: var(--primary-color); }
        .search-wrapper { flex-grow: 1; position: relative; }
        .search-wrapper i { position: absolute; left: 0.875rem; top: 50%; transform: translateY(-50%); color: var(--text-secondary); }
        .search-input { padding-left: 2.5rem; }
        .btn { border-radius: 0.5rem; padding: 0.625rem 1.25rem; font-weight: 600; transition: all 0.2s; border: none; display: inline-flex; align-items: center; gap: 0.5rem; cursor: pointer; }
        .btn-primary { background-color: var(--primary-color); color: #fff; }
        .btn-primary:hover { background-color: var(--primary-hover); }
        .btn-secondary { background-color: #fff; color: #374151; border: 1px solid var(--border-color); }
        .btn-secondary:hover { background-color: #f9fafb; }
        .btn-lg { padding: 0.875rem 1.5rem; font-size: 1rem; }
        .btn-success { background-color: var(--success-color); color: #fff; }
        .table-wrapper { max-height: 50vh; overflow-y: auto; border: 1px solid var(--border-color); border-radius: 0.5rem;}
        .table { width: 100%; border-collapse: collapse; }
        .table th, .table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border-color); }
        .table th { background-color: #f9fafb; position: sticky; top: 0; z-index: 1; }
        .table tbody tr:last-child td { border-bottom: none; }
        .table tbody tr:hover { background-color: #f9fafb; }
        .form-check-input { border-radius: 0.25em; }
        .code-container { position: relative; margin-top: 0.5rem; }
        pre { background-color: #f3f4f6; color: #111827; padding: 1rem; border-radius: 0.5rem; margin: 0; white-space: pre; overflow-x: auto; font-family: var(--font-mono); font-size: 0.875rem;}
        .copy-btn { position: absolute; top: 0.5rem; right: 0.5rem; background-color: #e5e7eb; color: #4b5563; border: none; padding: 0.25rem 0.5rem; border-radius: 0.375rem; cursor: pointer; opacity: 0; transition: all 0.2s; }
        .code-container:hover .copy-btn { opacity: 1; }
        #ddl-report { padding: 1rem; border-radius: 0.5rem; border-left: 4px solid; margin-top: 1rem; }
        @keyframes row-highlight-anim { 0% { background-color: #dcfce7; } 100% { background-color: transparent; } }
        .row-highlight-match { animation: row-highlight-anim 2.5s ease-out; }
        .default-value-marker { position: absolute; top: 0; right: 1rem; width: 0; height: 0; border-top: 18px solid #facc15; border-left: 18px solid transparent; }
        .footer { text-align: center; margin-top: 4rem; padding: 2rem; color: var(--text-secondary); font-size: 0.875rem; }
    </style>
</head>
<body>
    <div class="container">
        <header class="header"><pre>{{ mignon_logo|safe }}</pre></header>
        <div class="main-layout">
            <div class="config-panel">
                 <div class="card">
                    <div class="card-header"><span><i class="bi bi-database-gear"></i> 1. 粘贴DDL (可选)</span></div>
                    <div class="card-body">
                        <textarea id="ddl-input" class="form-control" rows="12" placeholder="在此处粘贴您的 CREATE TABLE 语句..."></textarea>
                        <button id="parse-ddl-btn" class="btn btn-primary mt-3"><i class="bi bi-magic"></i> 解析并高亮匹配项</button>
                        <div id="ddl-report" style="display:none;"></div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <span><i class="bi bi-table"></i> 2. 配置字段映射</span>
                        <div class="search-wrapper"><i class="bi bi-search"></i><input type="search" id="search-input" class="search-input" placeholder="搜索字段..."></div>
                        <button type="button" id="add-row-btn" class="btn btn-secondary" title="添加新的映射行"><i class="bi bi-plus-lg"></i></button>
                    </div>
                    <form id="mapping-form" method="POST" action="/">
                        <div class="table-wrapper"><table class="table">
                            <thead><tr><th>包含</th><th>源字段</th><th>目标字段</th><th>默认值</th></tr></thead>
                            <tbody id="mapping-table-body">
                                {% for key in sample_data.keys()|sort %}
                                <tr>
                                    <td><input type="checkbox" name="include_{{ key }}" id="include_{{ key }}" class="form-check-input" checked></td>
                                    <td><label for="include_{{ key }}">{{ key }}</label></td>
                                    <td><input type="text" class="form-control" name="target_{{ key }}" value="{{ to_snake_case(key) }}"></td>
                                    <td style="position: relative;"><input type="text" class="form-control" name="default_{{ key }}" placeholder="-" value="{{ pre_default_values.get(key, '') }}">
                                        {% if key in pre_default_values %}<div class="default-value-marker" title="预设值"></div>{% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table></div>
                        <div style="padding: 1.5rem;"><button type="submit" class="btn btn-primary btn-lg w-100"><i class="bi bi-file-earmark-code"></i> 生成配置</button></div>
                    </form>
                </div>
            </div>
            <div class="output-panel">
                <div class="card">
                    <div class="card-header">
                        <span><i class="bi bi-clipboard-check"></i> 3. 复制代码</span>
                        <button id="copy-all-btn" class="btn btn-secondary"><i class="bi bi-collection-fill"></i> 一键复制全部</button>
                    </div>
                    <div class="card-body">
                        <h5>include_keys</h5>
                        <div class="code-container"><button class="copy-btn"><i class="bi bi-clipboard"></i></button><pre><code id="code-include">{{ generated_code.include_keys|safe if generated_code else '# 点击左侧“生成配置”按钮' }}</code></pre></div>
                        <h5 style="margin-top: 1.5rem;">modifier_function</h5>
                        <div class="code-container"><button class="copy-btn"><i class="bi bi-clipboard"></i></button><pre><code id="code-modifier">{{ generated_code.mod_func|safe if generated_code else '# ...' }}</code></pre></div>
                        <h5 style="margin-top: 1.5rem;">default_values</h5>
                        <div class="code-container"><button class="copy-btn"><i class="bi bi-clipboard"></i></button><pre><code id="code-defaults">{{ generated_code.def_vals|safe if generated_code else '# ...' }}</code></pre></div>
                    </div>
                </div>
            </div>
        </div>
        <footer class="footer">All Rights Reserved © {{ current_year }} Mignon</footer>
    </div>
    <script>
    document.addEventListener('DOMContentLoaded', () => {
        // --- 一键复制全部 ---
        const copyAllBtn = document.getElementById('copy-all-btn');
        if(copyAllBtn) {
            copyAllBtn.addEventListener('click', () => {
                const includeCode = document.getElementById('code-include')?.innerText || '';
                const modifierCode = document.getElementById('code-modifier')?.innerText || '';
                const defaultsCode = document.getElementById('code-defaults')?.innerText || '';
                if (!includeCode.includes('生成配置')) {
                    const fullScript = `# Generated by mignonFramework Eazy Mode\\n# --- include_keys ---\\n${includeCode}\\n\\n# --- modifier_function ---\\n${modifierCode}\\n\\n# --- default_values ---\\n${defaultsCode}`.trim();
                    navigator.clipboard.writeText(fullScript).then(() => {
                        const originalText = copyAllBtn.innerHTML;
                        copyAllBtn.innerHTML = '<i class="bi bi-check-all"></i> 全部已复制!';
                        copyAllBtn.classList.add('btn-success');
                        setTimeout(() => { copyAllBtn.innerHTML = originalText; copyAllBtn.classList.remove('btn-success'); }, 2500);
                    });
                } else { alert('请先生成配置代码后再复制。'); }
            });
        }
        
        // --- 实时搜索 ---
        const searchInput = document.getElementById('search-input');
        const tableBody = document.getElementById('mapping-table-body');
        const allRows = Array.from(tableBody.getElementsByTagName('tr'));
        searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            allRows.forEach(row => {
                const sourceText = row.cells[1].textContent.toLowerCase();
                const targetText = row.querySelector('input[name^="target_"]')?.value.toLowerCase() || '';
                row.style.display = (sourceText.includes(searchTerm) || targetText.includes(searchTerm)) ? '' : 'none';
            });
        });

        // --- DDL解析 ---
        document.getElementById('parse-ddl-btn').addEventListener('click', async () => {
            const ddl = document.getElementById('ddl-input').value;
            const reportDiv = document.getElementById('ddl-report');
            if (!ddl.trim()) { alert('DDL输入不能为空!'); return; }
            try {
                const response = await fetch('/parse_ddl', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ddl }) });
                if (!response.ok) throw new Error((await response.json()).error || 'DDL解析失败');
                const data = await response.json();
                const ddlColumns = new Set(data.columns || []);
                if (ddlColumns.size === 0) { alert('未从DDL中提取到任何字段名。'); return; }
                let matchedCount = 0;
                let ddlOnly = Array.from(ddlColumns);
                const tableRows = document.querySelectorAll('#mapping-table-body tr');
                tableRows.forEach(row => {
                    const targetInput = row.querySelector('input[name^="target_"]');
                    if (!targetInput) return;
                    const isMatch = ddlColumns.has(targetInput.value);
                    const includeCheckbox = row.querySelector('input[type="checkbox"]');
                    if(includeCheckbox) includeCheckbox.checked = isMatch;
                    if (isMatch) {
                        matchedCount++;
                        ddlOnly = ddlOnly.filter(col => col !== targetInput.value);
                        row.classList.add('row-highlight-match');
                        setTimeout(() => row.classList.remove('row-highlight-match'), 2500);
                    }
                });
                const successClass = 'background-color: #f0fdf4; border-color: var(--success-color); color: #14532d;';
                const warningClass = 'background-color: #fffbeb; border-color: var(--warning-color); color: #78350f;';
                reportDiv.style.cssText = ddlOnly.length > 0 ? warningClass : successClass;
                reportDiv.style.display = 'block';
                reportDiv.innerHTML = `<h6><i class="bi bi-info-circle-fill"></i> DDL 报告</h6><p style="font-size: 0.9rem; margin:0;"><strong>${matchedCount}个字段已匹配。</strong>${ddlOnly.length > 0 ? `<br><strong>${ddlOnly.length}个字段在DDL中独有:</strong> ${ddlOnly.join(', ')}` : ''}</p>`;
                reportDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } catch (error) {
                reportDiv.style.cssText = 'background-color: #fee2e2; border-color: #ef4444; color: #991b1b;';
                reportDiv.style.display = 'block';
                reportDiv.innerHTML = `<p><strong>错误:</strong> ${error.message}</p>`;
            }
        });

        // --- 添加新行 ---
        let new_row_counter = 0;
        document.getElementById('add-row-btn').addEventListener('click', () => {
            const tableBody = document.getElementById('mapping-table-body');
            const newRow = tableBody.insertRow();
            allRows.push(newRow);
            const rowId = `new_${new_row_counter++}`;
            newRow.innerHTML = `<td><input type="checkbox" name="include_${rowId}" class="form-check-input" checked></td><td><input type="text" class="form-control" name="source_${rowId}" placeholder="新源字段"></td><td><input type="text" class="form-control" name="target_${rowId}" placeholder="新目标字段"></td><td><input type="text" class="form-control" name="default_${rowId}" placeholder="-"></td>`;
        });
        
        // --- 单独复制按钮 ---
        document.querySelectorAll('.copy-btn').forEach(button => {
            button.onclick = () => {
                const pre = button.nextElementSibling;
                navigator.clipboard.writeText(pre.innerText).then(() => {
                    const originalIcon = button.innerHTML;
                    button.innerHTML = '<i class="bi bi-check-lg" style="color:var(--success-color);"></i>';
                    setTimeout(() => { button.innerHTML = originalIcon; }, 2000);
                });
            }
        });
    });
    </script>
</body>
</html>
"""

class EazyAppRunner:
    def __init__(self, sample_data, to_snake_case_func, pre_default_values):
        self.app = Flask(__name__)
        self.sample_data = sample_data
        self.to_snake_case = to_snake_case_func
        self.pre_default_values = pre_default_values or {}
        self.mignon_logo = """                                                         
   __     __)                  
  (, /|  /|   ,                
    / | / |     _  __   _____  
 ) /  |/  |__(_(_/_/ (_(_) / (_
(_/   '       .-/              
             (_/               
                             v 0.3 mignonFramework

"""
        self._setup_routes()

    def _format_code(self, code_str):
        code_str = code_str.replace('<', '&lt;').replace('>', '&gt;')
        code_str = re.sub(r'(#.*)', r'<span style="color:#6b7280;">\1</span>', code_str)
        code_str = re.sub(r'(\bdef\b|\bfrom\b|\bimport\b|\breturn\b)', r'<span style="color:#be185d; font-weight:500;">\1</span>', code_str)
        code_str = re.sub(r"(\bRename\b)", r'<span style="color:#2563eb; font-weight:500;">\1</span>', code_str)
        code_str = re.sub(r"('.*?')", r'<span style="color:#059669;">\1</span>', code_str)
        return code_str

    def _setup_routes(self):
        @self.app.route('/', methods=['GET', 'POST'])
        def index():
            context = {
                "mignon_logo": self.mignon_logo,
                "sample_data": self.sample_data,
                "to_snake_case": self.to_snake_case,
                "pre_default_values": self.pre_default_values,
                "generated_code": None,
                "current_year": datetime.now().year
            }
            if request.method == 'POST':
                form_data = request.form
                include_keys, modifications, default_values = [], {}, {}
                for key in self.sample_data.keys():
                    if f'include_{key}' in form_data:
                        target_key = form_data.get(f'target_{key}', '').strip()
                        if not target_key: continue
                        include_keys.append(target_key)
                        default_val = form_data.get(f'default_{key}')
                        if default_val: default_values[key] = default_val
                        if target_key != self.to_snake_case(key): modifications[key] = target_key
                i = 0
                while True:
                    row_id = f'new_{i}'
                    if f'include_{row_id}' not in form_data: break
                    source_key = form_data.get(f'source_{row_id}', '').strip()
                    target_key = form_data.get(f'target_{row_id}', '').strip()
                    if source_key and target_key:
                        include_keys.append(target_key)
                        default_val = form_data.get(f'default_{row_id}')
                        if default_val: default_values[source_key] = default_val
                        if target_key != self.to_snake_case(source_key): modifications[source_key] = target_key
                    i += 1

                include_keys_str = f"include_keys = {json.dumps(sorted(list(set(include_keys))), indent=4)}"
                defaults_str_list = ["# 注意: 所有值都是字符串, 你可能需要手动修改类型", "default_values = {"]
                for k, v in sorted(default_values.items()): defaults_str_list.append(f"    '{k}': {repr(v)},")
                defaults_str_list.append("}")
                def_vals_str = "\n".join(defaults_str_list)
                mod_func_lines = ["from your_module import Rename  # 确保从正确的位置导入Rename类\n", "def modifier(data: dict) -> dict:", "    return {"]
                for key, new_name in sorted(modifications.items()): mod_func_lines.append(f"        '{key}': Rename('{new_name}'),")
                mod_func_lines.append("    }")
                mod_func_str = "\n".join(mod_func_lines)

                context["generated_code"] = {
                    "include_keys": self._format_code(include_keys_str),
                    "mod_func": self._format_code(mod_func_str),
                    "def_vals": self._format_code(def_vals_str),
                }
            return render_template_string(HTML_TEMPLATE, **context)

        @self.app.route('/parse_ddl', methods=['POST'])
        def parse_ddl():
            data = request.get_json()
            if not data or 'ddl' not in data:
                return jsonify({'error': 'Missing DDL string'}), 400
            try:
                columns = extract_column_names_from_ddl(data['ddl'])
                return jsonify({'columns': columns})
            except Exception as e:
                return jsonify({'error': f'Failed to parse DDL: {e}'}), 500

    def run(self, host='127.0.0.1', port=5000):
        print(f" * mignonFramework Eazy Mode Server is running on http://{host}:{port}")
        print(" * (Press CTRL+C to quit)")
        self.app.run(host=host, port=port, debug=False)
