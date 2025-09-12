import os
import shlex
import re
import json
import urllib.parse
from typing import Optional, Union, Any, Dict, List, Tuple

# --- 新增/统一的导入 ---
import requests
import ast
import io
import contextlib


class CurlToRequestsConverter:
    """
    一个灵活的工具类，用于将 cURL 命令转换为可用的 Python requests 代码。
    该版本已整合了对 multipart/form-data (-F)、基本认证 (-u) 和其他常见 cURL 选项的支持。
    """

    def __init__(self, curl_input: str, output_filename: str = 'generated_request.py'):
        """
        初始化转换器。
        :param curl_input: cURL 命令字符串或包含该命令的文件路径。
        :param output_filename: 输出的 Python 文件名。
        """
        self._curl_input = curl_input
        self._output_filename = output_filename
        self._parsed_data = self._parse_curl_command()

    def _read_from_file(self) -> str:
        """从文件中读取 cURL 命令字符串。"""
        if not os.path.exists(self._curl_input):
            raise FileNotFoundError(f"文件 '{self._curl_input}' 不存在。")
        try:
            with open(self._curl_input, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            raise IOError(f"读取文件 '{self._curl_input}' 时出错: {e}")

    def _try_parse_json(self, data_str: str) -> Union[dict, str]:
        """尝试将字符串解析为JSON，如果失败则返回原字符串。"""
        try:
            return json.loads(data_str)
        except json.JSONDecodeError:
            return data_str

    def _parse_curl_command(self) -> Dict[str, Any]:
        """
        核心解析方法：解析 cURL 命令字符串，提取所有组件。
        """
        curl_command_string = self._curl_input
        if os.path.exists(self._curl_input) and os.path.isfile(self._curl_input):
            print(f"正在从文件 '{self._curl_input}' 读取 cURL 命令...")
            curl_command_string = self._read_from_file()
        elif not curl_command_string.strip().startswith('curl'):
            raise ValueError("输入不是有效的 cURL 命令字符串或文件路径。")

        # 使用 shlex 分割命令，正确处理引号和转义字符
        command_list = shlex.split(curl_command_string)

        data: Dict[str, Any] = {
            'method': 'GET',
            'url': None,
            'headers': {},
            'cookies': {},
            'data': None,
            'json': None,
            'params': {},
            'files': [],
            'auth': None,
            'proxies': None,
            'verify': True,
            'timeout': None
        }

        get_data_as_params = False
        content_type = '' # 用于追踪 Content-Type 请求头

        i = 1
        while i < len(command_list):
            arg = command_list[i]

            if not arg.startswith('-') and data['url'] is None:
                parsed_url = urllib.parse.urlparse(arg)
                data['url'] = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
                if parsed_url.query:
                    parsed_params = urllib.parse.parse_qs(parsed_url.query, keep_blank_values=True)
                    data['params'] = {k: v if len(v) > 1 else v[0] for k, v in parsed_params.items()}

            elif arg in ('-X', '--request'):
                if i + 1 < len(command_list):
                    data['method'] = command_list[i + 1].upper()
                    i += 1

            elif arg == '-G' or arg == '--get':
                get_data_as_params = True

            elif arg in ('-H', '--header'):
                if i + 1 < len(command_list):
                    parts = command_list[i + 1].split(':', 1)
                    header_key = parts[0].strip()
                    header_value = parts[1].strip() if len(parts) > 1 else ''

                    if header_key.lower() == 'content-type':
                        content_type = header_value.strip().lower() # 存储 Content-Type

                    if header_key.lower() not in ['content-length']:
                        data['headers'][header_key] = header_value
                    i += 1

            elif arg in ('-A', '--user-agent'):
                if i + 1 < len(command_list):
                    data['headers']['User-Agent'] = command_list[i + 1]
                    i += 1

            elif arg in ('-d', '--data', '--data-raw', '--data-binary'):
                if i + 1 < len(command_list):
                    raw_data_str = command_list[i + 1]

                    # 检查并移除 cURL 中 `$''` 语法可能留下的前导 '$'
                    # shlex.split 通常会处理引号，但 `$ ` 可能被保留。
                    if raw_data_str.startswith('$'):
                        raw_data_str = raw_data_str.lstrip('$')

                    if get_data_as_params:
                        parsed_params = urllib.parse.parse_qs(raw_data_str)
                        for k, v in parsed_params.items():
                            data['params'][k] = v if len(v) > 1 else v[0]
                    else:
                        # 只有在使用 -G 选项时，GET 请求的数据才会被转为 params
                        # 否则，cURL 的默认行为是如果 -d 存在，就将请求方法变为 POST
                        if data['method'] == 'GET':
                            data['method'] = 'POST'

                        # 如果 Content-Type 是 JSON，则尝试解析。如果失败，则回退到原始数据。
                        if 'application/json' in content_type:
                            try:
                                data['json'] = json.loads(raw_data_str)
                            except json.JSONDecodeError:
                                # 根据用户要求：不抛出异常，回退到原始数据处理
                                data['data'] = raw_data_str
                                print("警告: Content-Type 为 'application/json'，但数据无法解析为 JSON。将作为原始数据 (bytes) 处理。")
                        else:
                            # 否则，作为原始数据处理
                            data['data'] = raw_data_str
                    i += 1

            elif arg in ('-F', '--form'):
                if data['method'] == 'GET':
                    data['method'] = 'POST'
                if i + 1 < len(command_list):
                    key, value = command_list[i+1].split('=', 1)
                    data['files'].append((key, value))
                    i += 1

            elif arg in ('-b', '--cookie'):
                if i + 1 < len(command_list):
                    cookies_str = command_list[i + 1]
                    for cookie in cookies_str.split(';'):
                        if '=' in cookie:
                            key, value = cookie.split('=', 1)
                            data['cookies'][key.strip()] = value.strip()
                    i += 1

            elif arg in ('-u', '--user'):
                if i + 1 < len(command_list):
                    credentials = command_list[i+1]
                    user, _, password = credentials.partition(':')
                    data['auth'] = (user, password)
                    i += 1

            elif arg in ('-x', '--proxy'):
                if i + 1 < len(command_list):
                    data['proxies'] = {'http': command_list[i+1], 'https': command_list[i+1]}
                    i += 1

            elif arg in ('--insecure', '-k'):
                data['verify'] = False
            elif arg in ('--max-time', '-m'):
                if i + 1 < len(command_list):
                    try:
                        data['timeout'] = int(command_list[i+1])
                    except ValueError:
                        print(f"警告: 无效的超时值 '{command_list[i+1]}'. 将被忽略。")
                    i += 1
            i += 1

        if data['url'] is None:
            raise ValueError("在 cURL 命令中未找到有效的 URL。")
        return data

    def convert_and_execute(self) -> tuple[str, str, bool, str]:
        generated_code = self._generate_python_code()

        exec_globals = {
            'requests': requests,
            'json': json
        }

        response_obj = None
        captured_stdout = io.StringIO()
        try:
            is_json = False
            return generated_code, "", is_json, "200"

        except requests.exceptions.Timeout:
            error_message = f"--- 代码执行失败 ---\n请求超时 (超过 {self._parsed_data.get('timeout')} 秒)"
            return generated_code, error_message, False, "Timeout Error"
        except Exception as e:
            error_message = f"--- 代码执行失败 ---\n{e}\n\n--- 捕获的输出 ---\n{captured_stdout.getvalue()}"
            return generated_code, error_message, False, "Execution Error"

    def _generate_python_code(self) -> str:
        """根据解析后的数据生成 Python requests 代码字符串。"""
        p = self._parsed_data

        lines = ["import requests", "import json", "import urllib.parse", "from mignonFramework import JSONFormatter","\n# 由 Mignon Rex 的 MignonFramework.CurlToRequestsConverter 生成",
                 "# Have a good Request\n"]

        if p['headers']:
            lines.append(f"headers = {json.dumps(p['headers'], indent=4, ensure_ascii=False)}\n")
        if p['cookies']:
            lines.append(f"cookies = {json.dumps(p['cookies'], indent=4, ensure_ascii=False)}\n")
        if p['params']:
            lines.append(f"params = {json.dumps(p['params'], indent=4, ensure_ascii=False)}\n")

        if p['json'] is not None:
            json_str = json.dumps(p['json'], indent=4, ensure_ascii=False)
            json_str = json_str.replace('true', 'True').replace('false', 'False').replace('null', 'None')
            lines.append(f"json_data = {json_str}\n")

        # --- 严格按照 GET / POST 方法区分 data 的处理方式 ---
        elif p['data'] is not None:
            # 对于 POST 或其他有请求体的方法
            if p['method'].upper() not in ['GET']:
                try:
                    stripped_data = p['data'].strip()
                    if '=' in stripped_data and not stripped_data.startswith(('{', '[')):
                        parsed_dict = urllib.parse.parse_qs(p['data'], keep_blank_values=True)
                        data_dict = {k: v[0] if len(v) == 1 else v for k, v in parsed_dict.items()}
                        data_str = json.dumps(data_dict, indent=4, ensure_ascii=False)
                        lines.append(f"data = {data_str}\n")
                    else:
                        # 如果无法解析为键值对（例如是纯文本），则作为原始字符串
                        escaped_data_repr = repr(p['data'])
                        lines.append(f"data = {escaped_data_repr}\n")
                except Exception:
                    escaped_data_repr = repr(p['data'])
                    lines.append(f"data = {escaped_data_repr}\n")
            # 对于 GET 请求（非标准用法）
            else:
                escaped_data_repr = repr(p['data'])
                # 遵照用户的特定要求
                lines.append(f"data = {escaped_data_repr}.encode('unicode_escape') # 注意：此编码方式对于标准JSON请求可能需要调整。\n")

        if p['files']:
            files_list = []
            for key, value in p['files']:
                if value.startswith('@'):
                    file_path = value[1:]
                    files_list.append(f"'{key}': ('{os.path.basename(file_path)}', open('{file_path}', 'rb'))")
                else:
                    files_list.append(f"'{key}': (None, '{value}')")
            lines.append(f"files = {{\n    " + ",\n    ".join(files_list) + "\n}\n")

        if p['auth']:
            lines.append(f"auth = {p['auth']}\n")

        request_params = ['url']
        if p['headers']:
            request_params.append("headers=headers")
        if p['cookies']:
            request_params.append("cookies=cookies")
        if p['params']:
            request_params.append("params=params")
        if p['json'] is not None:
            request_params.append("json=json_data")
        elif p['data'] is not None:
            request_params.append("data=data")
        if p['files']:
            request_params.append("files=files")
        if p['auth']:
            request_params.append("auth=auth")
        if p['proxies']:
            request_params.append(f"proxies={p['proxies']}")
        if not p['verify']:
            request_params.append("verify=False")
        if p['timeout'] is not None:
            request_params.append(f"timeout={p['timeout']}")

        request_params_str = ',\n    '.join(request_params)

        lines.append(f"url = \"{p['url']}\"")
        lines.append(f"\nresponse = requests.{p['method'].lower()}(\n    {request_params_str}\n)")
        lines.append("\n# The following print statements are for debugging and are not part of the core request logic.")
        lines.append("print(f\"状态码: {response.status_code}\")")
        lines.append("try:")
        lines.append("    print(\"响应 JSON:\", response.json())")
        lines.append("    JSONFormatter(response.text)")
        lines.append("except json.JSONDecodeError:")
        lines.append("    print(\"响应文本:\", response.text)")

        return "\n".join(lines)

    def run(self):
        """执行转换并保存到 Python 文件。"""
        try:
            py_code = self._generate_python_code()
            with open(self._output_filename, 'w', encoding='utf-8') as f:
                f.write(py_code)
            print(f"转换成功！已将代码保存到文件: '{self._output_filename}'")
        except (ValueError, FileNotFoundError, IOError) as e:
            print(f"转换失败: {e}")
        except Exception as e:
            print(f"发生未知错误: {e}")

