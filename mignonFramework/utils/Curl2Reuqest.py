import os
import shlex
import re
import json
import urllib.parse
from typing import Optional, Union, Any, Dict, List, Tuple

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
            'files': [], # 新增：用于处理 -F 表单数据
            'auth': None,  # 新增：用于处理 -u 用户认证
            'proxies': None,
            'verify': True,
            'timeout': None
        }

        # 标志位，用于处理 -G 和 -d 结合的情况
        get_data_as_params = False

        i = 1
        while i < len(command_list):
            arg = command_list[i]

            # 1. 识别并解析 URL
            if not arg.startswith('-') and data['url'] is None:
                parsed_url = urllib.parse.urlparse(arg)
                data['url'] = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
                if parsed_url.query:
                    parsed_params = urllib.parse.parse_qs(parsed_url.query, keep_blank_values=True)
                    data['params'] = {k: v if len(v) > 1 else v[0] for k, v in parsed_params.items()}

            # 2. 解析请求方法
            elif arg in ('-X', '--request'):
                if i + 1 < len(command_list):
                    data['method'] = command_list[i + 1].upper()
                    i += 1

            # 3. 解析 -G 标志，它会影响 -d 的行为
            elif arg == '-G' or arg == '--get':
                get_data_as_params = True

            # 4. 解析请求头
            elif arg in ('-H', '--header'):
                if i + 1 < len(command_list):
                    parts = command_list[i + 1].split(':', 1)
                    header_key = parts[0].strip()
                    header_value = parts[1].strip() if len(parts) > 1 else ''
                    if header_key.lower() not in ['content-length']:
                        data['headers'][header_key] = header_value
                    i += 1

            # 5. 解析用户代理
            elif arg in ('-A', '--user-agent'):
                if i + 1 < len(command_list):
                    data['headers']['User-Agent'] = command_list[i + 1]
                    i += 1

            # 6. 解析请求体数据 (-d) 或 URL 参数 (当与 -G 结合时)
            elif arg in ('-d', '--data', '--data-raw', '--data-binary'):
                if i + 1 < len(command_list):
                    raw_data_str = command_list[i + 1]

                    if get_data_as_params:
                        # 如果 -G 存在, 将 -d 的数据作为 URL 参数
                        parsed_params = urllib.parse.parse_qs(raw_data_str)
                        for k, v in parsed_params.items():
                            data['params'][k] = v if len(v) > 1 else v[0]
                    else:
                        # 否则作为请求体
                        if data['method'] == 'GET':
                            data['method'] = 'POST'
                        parsed_body = self._try_parse_json(raw_data_str)
                        if isinstance(parsed_body, dict):
                            data['json'] = parsed_body
                        else:
                            data['data'] = raw_data_str
                    i += 1

            # 7. 新增：解析 multipart/form-data (-F)
            elif arg in ('-F', '--form'):
                if data['method'] == 'GET':
                    data['method'] = 'POST'
                if i + 1 < len(command_list):
                    key, value = command_list[i+1].split('=', 1)
                    data['files'].append((key, value))
                    i += 1

            # 8. 解析 Cookies
            elif arg in ('-b', '--cookie'):
                if i + 1 < len(command_list):
                    cookies_str = command_list[i + 1]
                    for cookie in cookies_str.split(';'):
                        if '=' in cookie:
                            key, value = cookie.split('=', 1)
                            data['cookies'][key.strip()] = value.strip()
                    i += 1

            # 9. 新增：解析基本认证
            elif arg in ('-u', '--user'):
                if i + 1 < len(command_list):
                    credentials = command_list[i+1]
                    user, _, password = credentials.partition(':')
                    data['auth'] = (user, password)
                    i += 1

            # 10. 解析代理
            elif arg in ('-x', '--proxy'):
                if i + 1 < len(command_list):
                    data['proxies'] = {'http': command_list[i+1], 'https': command_list[i+1]}
                    i += 1

            # 11. 解析其他选项
            elif arg in ('--insecure', '-k'):
                data['verify'] = False
            elif arg in ('--max-time', '-m'):
                if i + 1 < len(command_list):
                    data['timeout'] = int(command_list[i+1])
                    i += 1

            i += 1

        if data['url'] is None:
            raise ValueError("在 cURL 命令中未找到有效的 URL。")

        return data

    def _generate_python_code(self) -> str:
        """根据解析后的数据生成 Python requests 代码字符串。"""
        p = self._parsed_data

        lines = ["import requests", "import json", "", "# 由 Mignon Rex 的 MignonFramework.CurlToRequestsConverter 生成",
                 "# Have a good Request\n"]

        if p['headers']:
            lines.append(f"headers = {json.dumps(p['headers'], indent=4, ensure_ascii=False)}\n")
        if p['cookies']:
            lines.append(f"cookies = {json.dumps(p['cookies'], indent=4, ensure_ascii=False)}\n")
        if p['params']:
            lines.append(f"params = {json.dumps(p['params'], indent=4, ensure_ascii=False)}\n")
        if p['json'] is not None:
            # 修正：确保将 json 的 true/false/null 转换为 Python 的 True/False/None
            json_str = json.dumps(p['json'], indent=4, ensure_ascii=False)
            json_str = json_str.replace('true', 'True').replace('false', 'False').replace('null', 'None')
            lines.append(f"json_data = {json_str}\n")
        elif p['data'] is not None:
            lines.append(f"data = {repr(p['data'])}\n")

        # 新增：处理 files
        if p['files']:
            files_list = []
            for key, value in p['files']:
                if value.startswith('@'):
                    # 表示文件上传
                    file_path = value[1:]
                    files_list.append(f"'{key}': ('{os.path.basename(file_path)}', open('{file_path}', 'rb'))")
                else:
                    # 普通表单字段
                    files_list.append(f"'{key}': (None, '{value}')")
            lines.append(f"files = {{\n    " + ",\n    ".join(files_list) + "\n}\n")

        # 新增：处理 auth
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
            request_params.append("files=files") # 新增
        if p['auth']:
            request_params.append("auth=auth") # 新增
        if p['proxies']:
            request_params.append(f"proxies={p['proxies']}")
        if not p['verify']:
            request_params.append("verify=False")
        if p['timeout'] is not None:
            request_params.append(f"timeout={p['timeout']}")

        request_params_str = ',\n    '.join(request_params)

        lines.append(f"url = \"{p['url']}\"")
        lines.append(f"\nresponse = requests.{p['method'].lower()}(\n    {request_params_str}\n)")
        lines.append("\nprint(f\"状态码: {response.status_code}\")")
        lines.append("try:")
        lines.append("    print(\"响应 JSON:\", response.json())")
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


# --- 示例用法 ---
if __name__ == '__main__':
    # 示例 1: POST JSON (包含布尔值)
    print("--- 示例 1: POST JSON 请求 (包含布尔值) ---")
    curl_post = "curl -X POST 'https://httpbin.org/post' -H 'Content-Type: application/json' -d '{\"name\":\"NewItem\", \"is_active\": true, \"is_deleted\": false}'"
    CurlToRequestsConverter(curl_input=curl_post, output_filename='post_request.py').convert_and_save()
    print("-" * 40)

    # 示例 2: multipart/form-data 文件上传
    print("--- 示例 2: Multipart/form-data 文件上传 ---")
    # 创建一个临时文件用于演示
    with open("sample.txt", "w") as f:
        f.write("This is a test file.")
    curl_form = "curl -X POST 'https://httpbin.org/post' -F 'text_field=some_value' -F 'file_field=@sample.txt'"
    CurlToRequestsConverter(curl_input=curl_form, output_filename='form_upload_request.py').convert_and_save()
    os.remove("sample.txt") # 清理临时文件
    print("-" * 40)

    # 示例 3: 基本认证
    print("--- 示例 3: 基本认证 ---")
    curl_auth = "curl -u 'myuser:mypassword123' 'https://httpbin.org/basic-auth/myuser/mypassword123'"
    CurlToRequestsConverter(curl_input=curl_auth, output_filename='auth_request.py').convert_and_save()
    print("-" * 40)

    # 示例 4: 使用 -G 将 -d 数据作为 URL 参数
    print("--- 示例 4: 使用 -G 和 -d ---")
    curl_get_data = "curl -G 'http://example.com/search' -d 'query=widgets&sort=price'"
    CurlToRequestsConverter(curl_input=curl_get_data, output_filename='get_with_data_request.py').convert_and_save()
    print("-" * 40)
