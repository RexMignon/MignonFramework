# mignonFramework/utils/starterUtil/code_generator.py
import json
import os


class CodeGenerator:
    """
    根据前端传递的完整应用状态，生成最终的Python爬虫脚本和相关的配置文件。
    """

    def __init__(self, state):
        self.state = state
        # 主爬虫脚本的组件
        self.imports = {"import requests", "import json", "import time", "import datetime", "import sys",
                        "import random",
                        "from mignonFramework import ConfigManager, Logger, inject, QueueIter, target, Rename, InsertQuick, execJS"}
        self.code_parts = []
        self.callback_functions = []

        # 所有待生成的文件内容都存储在这里
        self.output_files = {
            "ini": {},
            "js": {},
            "py": {}
        }

    def generate(self):
        """
        主生成方法。
        返回一个包含所有待生成文件内容的字典。
        """
        # --- 生成主爬虫脚本 (main.py) ---
        self.code_parts.append("log = Logger(True)")
        self.code_parts.append("\n# Have a Good Request\n#        --By mignonFramework\n\n")
        self.code_parts.append("\n# ======================Managers & Queues=====================")
        self._generate_config_managers_and_inis()
        self._generate_queue_instances()
        self.code_parts.append("\n# ======================DI & Targets========================")
        self._generate_targets_and_injected_classes()
        self.code_parts.append("\n# ======================ExecJS============================")
        self._generate_execjs()
        self.code_parts.append("\n# ======================Callbacks============================")
        self._generate_callbacks()
        if self.callback_functions:
            self.code_parts.extend(self.callback_functions)
        self.code_parts.append("\n# ======================Request Components======================")
        self._generate_request_components()
        self._generate_pre_check_request()
        self._assign_callbacks_to_queues()

        # FIX: Generate the main control logic
        self.code_parts.append("\n# ======================Main Control Logic======================")
        self._generate_request_to()
        self._generate_master_control_service()

        # 组合主脚本
        main_imports = "\n".join(sorted(list(self.imports)))
        main_body = "\n\n".join(self.code_parts)
        self.output_files["py"]["main.py"] = f"{main_imports}\n\n\n{main_body}"

        # --- 根据UI状态，生成 InsertQuick 相关文件 ---
        if self.state.get('insertQuickEnabled'):
            self._generate_insert_quick_files()

        return self.output_files

    def _generate_config_managers_and_inis(self):
        """生成ConfigManager实例和.ini文件，并将其存入 self.output_files"""
        configs = self.state.get('configs', {})
        if not configs:
            return
        for class_name, config_data in configs.items():
            manager_name = config_data.get('managerName')
            ini_path_name = config_data.get('managerIniPath', '').strip()

            ini_content = f"[{class_name}]\n"
            has_ini_content = False
            for field in config_data.get('fields', []):
                if 'default' in field:
                    ini_content += f"{field.get('name').lower()} = {field.get('default', '')}\n"
                    has_ini_content = True

            ini_filename = f"{ini_path_name}.ini" if ini_path_name else f"{manager_name}.ini"
            if has_ini_content:
                self.output_files["ini"][ini_filename] = ini_content

            if ini_path_name:
                manager_declaration = f"{manager_name} = ConfigManager('./resources/config/{ini_filename}', section='{class_name}')"
            else:
                manager_declaration = f"{manager_name} = ConfigManager(section='{class_name}')"
            self.code_parts.append(manager_declaration)

    def _generate_execjs(self):
        """生成ExecJS相关代码和JS文件，并将其存入 self.output_files"""
        execjs_configs = self.state.get('execjs', [])
        if not execjs_configs:
            return

        py_func_strs = []
        js_file_contents = {}  # 使用一个字典来收集JS文件内容，按文件名分组

        for config in execjs_configs:
            method_name = config.get('methodName')
            params = config.get('params', [])
            params_str = ", ".join(params)

            # 生成Python函数装饰器代码
            decorator_arg = ""
            js_filename = ""
            config_class_name = config.get('configClassName')
            config_field_name = config.get('pathFromConfigField')

            if config_class_name and config_field_name:
                decorator_arg = f"{config_class_name.lower()}.{config_field_name}"
                js_path_from_config = ""
                all_configs = self.state.get('configs', {})
                if config_class_name in all_configs:
                    for field in all_configs[config_class_name].get('fields', []):
                        if field.get('name') == config_field_name:
                            js_path_from_config = field.get('default', '').strip()
                            break
                is_valid_path = (js_path_from_config.startswith('./resources/js/') and
                                 (js_path_from_config.endswith('.js') or js_path_from_config.endswith('.jsx')))
                if is_valid_path:
                    js_filename = os.path.basename(js_path_from_config)
                else:
                    js_filename = f"{method_name}.js"
            elif config.get('staticPath'):
                static_path = config.get('staticPath')
                decorator_arg = f"'./resources/js/{static_path}'"
                js_filename = static_path

            if js_filename:
                # 生成JS函数内容
                js_content = f"function {method_name}({params_str}) {{\n    // Your JavaScript logic here\n    return null;\n}}\n\n"

                # 收集JS文件内容，确保不会覆盖
                if js_filename not in js_file_contents:
                    js_file_contents[js_filename] = ""
                js_file_contents[js_filename] += js_content

            py_func_str = f"@execJS({decorator_arg})\ndef {method_name}({params_str}):\n    return None\n"
            py_func_strs.append(py_func_str)

        # 将生成的JS文件内容添加到输出
        self.output_files["js"] = js_file_contents
        # 将所有Python函数代码添加到主脚本
        self.code_parts.extend(py_func_strs)

    def _generate_insert_quick_files(self):
        """
        如果用户启用了InsertQuick，则生成 insertQuickly.py 和 generic.ini。
        """
        py_content = """from mignonFramework import InsertQuick, Logger, ConfigManager, inject, QueueIter, target, Rename, MysqlManager

log = Logger(True)

# have a Good Insert QQQuick
#                 --by mignonFramework


InsertQuick(eazy=True).run()
"""
        self.output_files["py"]["insertQuickly.py"] = py_content

        ini_content = """[GenericProcessor]
host = YOUR_DATABASE_HOST
user = YOUR_USERNAME
password = YOUR_PASSWORD
database = YOUR_DATABASE_NAME
port = 3306
table_name = YOUR_TARGET_TABLE
path = PATH_TO_YOUR_FILE_OR_DIRECTORY
"""
        self.output_files["ini"]["generic.ini"] = ini_content

    def _generate_queue_instances(self):
        """生成QueueIter实例，并关联正确的ConfigManager"""
        queues = self.state.get('queueIters', {})
        configs = self.state.get('configs', {})

        queue_to_manager_map = {}
        for instance_name, queue_data in queues.items():
            if instance_name == 'UnnamedQueue':
                continue
            for t in queue_data.get('targets', []):
                if t.get('enabled'):
                    config_class = t.get('configClassName')
                    if config_class in configs:
                        manager_name = configs[config_class].get('managerName')
                        queue_to_manager_map[instance_name] = manager_name
                        break

        for instance_name in queues.keys():
            if instance_name != 'UnnamedQueue':
                manager_arg = queue_to_manager_map.get(instance_name, '')
                self.code_parts.append(f"{instance_name} = QueueIter({manager_arg})")

    def _generate_targets_and_injected_classes(self):
        """生成@target和@inject的类"""
        configs = self.state.get('configs', {})
        queues = self.state.get('queueIters', {})

        target_map = {}
        for instance_name, queue_data in queues.items():
            if instance_name == 'UnnamedQueue':
                continue
            for t in queue_data.get('targets', []):
                if t.get('enabled'):
                    config_class = t.get('configClassName')
                    if config_class not in target_map:
                        target_map[config_class] = []
                    target_map[config_class].append({
                        "instance_name": instance_name,
                        "config_field": t.get('configFieldName'),
                        "default_val": t.get('defaultValue') or 'None'
                    })

        for class_name, config_data in configs.items():
            if class_name == 'UnnamedConfig':
                continue
            code_block = ""
            if class_name in target_map:
                for target_info in target_map[class_name]:
                    raw_default_val = target_info['default_val']

                    if raw_default_val.strip().startswith('lambda'):
                        final_default_val = raw_default_val
                    elif raw_default_val == 'None':
                        final_default_val = 'None'
                    else:
                        try:
                            float(raw_default_val)
                            final_default_val = raw_default_val
                        except ValueError:
                            final_default_val = f"'{raw_default_val}'"

                    decorator = f"@target({target_info['instance_name']}, '{target_info['config_field']}', {final_default_val})"
                    code_block += f"{decorator}\n"

            manager_name = config_data.get('managerName')
            code_block += f"@inject({manager_name})\n"

            code_block += f"class {class_name}:\n"
            fields = config_data.get('fields', [])
            if not fields:
                code_block += "    pass\n"
            else:
                for field in fields:
                    code_block += f"    {field.get('name')}: {field.get('type', 'str')}\n"

            instance_name = class_name.lower()
            code_block += f"\n{instance_name}: {class_name} = {manager_name}.getInstance({class_name})"

            self.code_parts.append(code_block)

    def _generate_callbacks(self):
        """生成回调函数定义"""
        callbacks = self.state.get('callbacks', {})
        all_callback_defs = {}
        for queue_iter_name, callback_list in callbacks.items():
            for callback_data in callback_list:
                method_name = callback_data.get('methodName')
                if not method_name:
                    continue

                if method_name not in all_callback_defs:
                    code = f"def {method_name}(que: QueueIter):\n"
                    associated_configs = set()
                    for q_name, cb_list in callbacks.items():
                        for cb in cb_list:
                            if cb.get('methodName') == method_name and cb.get('isConfigEnabled'):
                                associated_configs.add(cb.get('configClassName'))

                    if not associated_configs:
                        code += "    pass\n"
                    else:
                        for config_class in associated_configs:
                            code += f"    global {config_class.lower()}\n"

                    all_callback_defs[method_name] = {"code": code, "assignments": []}

                if callback_data.get('isConfigEnabled'):
                    config_class = callback_data.get('configClassName')
                    config_field = callback_data.get('configFieldName')
                    assign_value = callback_data.get('assignValue')
                    if config_class and config_field and assign_value:
                        assignment_str = f"    {config_class.lower()}.{config_field} = {assign_value}\n"
                        all_callback_defs[method_name]["assignments"].append(assignment_str)

        for method_name, data in all_callback_defs.items():
            final_code = data['code']
            if data['assignments']:
                final_code += "".join(data['assignments'])
            self.callback_functions.append(final_code)

    def _assign_callbacks_to_queues(self):
        """在主代码逻辑中，将回调函数赋值给QueueIter实例"""
        callbacks = self.state.get('callbacks', {})
        assignments = []
        unique_assignments = set()
        for queue_iter_name, callback_list in callbacks.items():
            if callback_list:
                method_name = callback_list[0].get('methodName')
                if method_name:
                    assignment = f"{queue_iter_name}.callback = {method_name}"
                    if assignment not in unique_assignments:
                        assignments.append(assignment)
                        unique_assignments.add(assignment)

        if assignments:
            self.code_parts.append("\n# ======================Assign Callbacks======================")
            self.code_parts.extend(assignments)

    def _generate_request_components(self):
        """根据 '请求字段映射' 的配置生成 url, headers, cookies, params, 和 json_data。"""
        curl_details = self.state.get('curlDetails', {})
        url = curl_details.get('url', '')
        self.code_parts.append(f'urls = "{url}"')

        def build_dict_code(dict_name, field_type_key, original_data_key):
            # 修正：首先从状态中过滤掉所有被标记为删除的字段
            mapped_fields_with_deleted = self.state.get('extractedFields', {}).get(field_type_key, [])
            mapped_fields = [f for f in mapped_fields_with_deleted if not f.get('isDeleted')]

            original_data = curl_details.get(original_data_key, {})
            all_fields_in_ui = {f['fieldName'] for f in mapped_fields}
            if not all_fields_in_ui and not original_data:
                return None

            mapping_lookup = {f['fieldName']: f for f in mapped_fields}
            lines, all_keys = [], all_fields_in_ui.union(original_data.keys())

            # 修正：在迭代之前对键进行排序，以确保一致性
            for field_name in sorted(list(all_keys)):
                # 如果字段名在非删除映射中，则使用其配置
                if field_name in mapping_lookup:
                    mapping = mapping_lookup.get(field_name)
                    value_str = ""
                    if mapping and mapping.get('configClassName') and mapping.get('configFieldName'):
                        config_class, config_field = mapping.get('configClassName'), mapping.get('configFieldName')
                        value_str = f"{config_class.lower()}.{config_field}"
                    else:
                        original_value = original_data.get(field_name)
                        value_str = "''" if original_value is None else repr(original_value)
                    lines.append(f'    "{field_name}": {value_str},')
                # 如果字段只存在于原始数据中，但未在UI中被删除，则也应包含它
                elif field_name in original_data:
                    # 确保这个字段没有被UI中的同名删除字段覆盖
                    if field_name not in {f['fieldName'] for f in mapped_fields_with_deleted if f.get('isDeleted')}:
                        original_value = original_data.get(field_name)
                        value_str = "''" if original_value is None else repr(original_value)
                        lines.append(f'    "{field_name}": {value_str},')

            if not lines:
                return None
            return f"{dict_name} = {{\n" + "\n".join(lines) + "\n}"

        for name, f_type, o_key in [('headers', 'headers', 'extracted_headers'),
                                    ('cookies', 'cookies', 'extracted_cookies'),
                                    ('params', 'params', 'extracted_params'),
                                    ('json_data', 'jsonData', 'extracted_json_data')]:
            code = build_dict_code(name, f_type, o_key)
            if code:
                self.code_parts.append(code)

    def _generate_pre_check_request(self):
        """
        如果用户选择，则生成 preCheckRequest 函数。
        """
        if not self.state.get('preCheckRequestEnabled'):
            return

        method = self.state.get('curlDetails', {}).get('method', 'post').lower()
        global_vars = {'urls'}
        request_params = ['urls']
        copies_lines_list = []

        component_map = {
            'headers': 'headers', 'json_data': 'json',
            'params': 'params', 'cookies': 'cookies'
        }

        for var_name, param_name in component_map.items():
            if any(f'{var_name} = {{' in part for part in self.code_parts):
                global_vars.add(var_name)
                copies_lines_list.append(f"    {var_name}_copy = {var_name}.copy()")
                request_params.append(f'{param_name}={var_name}_copy')

        globals_line = f"    global {', '.join(sorted(list(global_vars)))}"
        copies_lines = "\n".join(copies_lines_list)
        request_params_str = ",\n        ".join(request_params)

        code = f"""
@log
def preCheckRequest():
{globals_line}
{copies_lines}
    response = None
    response = requests.{method}(
        {request_params_str}
    )
    if response.status_code == 200:
        res = response
        total = 0 # TODO: Implement logic to extract total from 'res'
        return total
    raise Exception(f"返回内容不正确:  {{response}}: {{response.text}}")
"""
        self.code_parts.append(code)

    def _generate_request_to(self):
        """生成带有重试逻辑的 requestTo 函数。"""
        method = self.state.get('curlDetails', {}).get('method', 'post').lower()
        global_vars = {'urls'}
        request_params = ['urls']
        copies_lines_list = []

        component_map = {
            'headers': 'headers', 'json_data': 'json',
            'params': 'params', 'cookies': 'cookies'
        }

        for var_name, param_name in component_map.items():
            if any(f'{var_name} = {{' in part for part in self.code_parts):
                global_vars.add(var_name)
                copies_lines_list.append(f"    {var_name}_copy = {var_name}.copy()")
                request_params.append(f'{param_name}={var_name}_copy')

        # Add 'data' if it's used in any callback
        if any('data' in cb.get('assignValue', '') for cb_list in self.state.get('callbacks', {}).values() for cb in
               cb_list):
            global_vars.add('data')

        globals_line = f"    global {', '.join(sorted(list(global_vars)))}"
        copies_lines = "\n".join(copies_lines_list)
        request_params_str = ",\n            ".join(request_params)

        code = f"""
@log
def requestTo():
{globals_line}
{copies_lines}
    status = 0
    response = None
    while True:
        try:
            response = requests.{method}(
                {request_params_str}
            )
            if response.status_code == 200:
                res = response
                print(res.text)
                # TODO: You may need to process 'res' and assign to 'data'
                # data = res.json() 
                return True
        except Exception as e:
            status += 1
            time.sleep(status * 0.4)
            print(response)
            if status >= 17:
                raise e
"""
        self.code_parts.append(code)

    def _generate_master_control_service(self):
        """
        根据排序和回调设置，生成具有动态嵌套循环的 masterControlService 函数。
        """
        mappings = self.state.get('mainRequest', {}).get('mappings', [])
        valid_mappings = [m for m in mappings if m.get('queueIterName')]

        # FIX: If no queues are mapped, generate a simple service that calls requestTo once.
        if not valid_mappings:
            body = []
            if self.state.get('preCheckRequestEnabled'):
                body.append("    total = preCheckRequest()")
            body.append("    requestTo()")

            body_str = "\n".join(body)

            full_code = f"""
@log
def masterControlService():
    # Since no QueueIter is mapped, this is a single request task.
    global data
{body_str}

if __name__ == '__main__':
    masterControlService()
"""
            self.code_parts.append(full_code)
            return

        # --- Logic for when there ARE valid mappings ---
        try:
            sorted_mappings = sorted(valid_mappings, key=lambda m: int(m.get('sort', 0)))
        except (ValueError, TypeError):
            sorted_mappings = valid_mappings

        all_queues = {m['queueIterName'] for m in sorted_mappings}
        globals_line = f"    global {', '.join(sorted(list(all_queues.union({'data'}))))}"

        init_lines = []
        if self.state.get('preCheckRequestEnabled'):
            init_lines.append("    total = preCheckRequest()")
        init_lines.append("    # 逻辑控制器")
        for m in sorted_mappings:
            init_lines.append(f"    {m['queueIterName']}.pages = range(0, 1) # TODO: Adjust page range as needed")

        init_str = "\n".join(init_lines)

        innermost_mapping = sorted_mappings[0]
        innermost_queue = innermost_mapping['queueIterName']

        code = f"if requestTo():\n"
        if innermost_mapping.get('triggerCallback'):
            code += f"    {innermost_queue}.call()"
        else:
            code += f"    pass"

        for mapping in sorted_mappings:
            queue_name = mapping['queueIterName']

            indented_code = "\n".join([f"    {line}" for line in code.splitlines()])

            wrapper = f"while {queue_name}.hasNext():\n"
            wrapper += f"    next_{queue_name} = next({queue_name})\n"
            wrapper += indented_code

            if mapping != innermost_mapping and mapping.get('triggerCallback'):
                wrapper += f"\n    {queue_name}.call()"

            code = wrapper

        loop_body = "\n".join([f"    {line}" for line in code.splitlines()])

        full_code = f"""
@log
def masterControlService():
{globals_line}
{init_str}
{loop_body}

if __name__ == '__main__':
    masterControlService()
"""
        self.code_parts.append(full_code)


def generate_scraper_code_and_configs(state: dict) -> dict:
    generator = CodeGenerator(state)
    return generator.generate()
