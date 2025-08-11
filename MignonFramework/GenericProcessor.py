"""
一个高度通用的文件到数据库ETL（提取、转换、加载）工具。它通过一个统一的 run() 方法，
可以智能处理单个文件或整个目录，支持“整文件JSON”和“逐行JSON”两种模式，并提供了断点续传、
可视化进度条和事件回调等高级功能。
"""
import json as std_json
import os
import shutil
import ast
import sys
import io
import re
from contextlib import redirect_stdout
from datetime import datetime
from typing import Dict, Callable, List, Optional, Any

from MignonFramework.MySQLManager import MysqlManager
from MignonFramework.CountLinesInFolder import count_lines_in_single_file


class GenericFileProcessor:
    """
    一个通用的、可定制的JSON文件处理器，用于将文件内容批量导入数据库。
    """

    def __init__(self,
                 db_manager: MysqlManager,
                 table_name: str,
                 mode: str = 'file',
                 modifier_function: Optional[Callable[[Dict], Dict]] = None,
                 exclude_keys: Optional[List[str]] = None,
                 default_values: Optional[Dict[str, Any]] = None,
                 batch_size: int = 1000,
                 callBack: Optional[Callable[[bool, List[Dict], str, Optional[int]], None]] = None):
        """
        初始化处理器。

        Args:
            db_manager (MysqlManager): 数据库管理器实例。
            table_name (str): 目标数据库表名。
            modifier_function (Callable, optional): 自定义修改函数。在自动解析后应用，用于修改或添加字段。
            exclude_keys (List[str], optional): 在自动解析模式下，需要排除的源JSON键列表。
            default_values (Dict[str, Any], optional): 在自动解析模式下，为缺失或为None的键提供默认值。
            mode (str): 文件处理模式。可选值为 'file' (默认) 或 'line'。
            batch_size (int): 每批提交的记录数。
            callBack (Callable, optional): 批处理完成后的回调函数。
        """
        if not isinstance(db_manager, MysqlManager) or not db_manager.is_connected():
            raise ValueError("必须提供一个已连接的MysqlManager实例。")
        if mode not in ['file', 'line']:
            raise ValueError("mode 参数必须是 'file' 或 'line'。")

        self.db_manager = db_manager
        self.table_name = table_name
        self.modifier_function = modifier_function
        self.exclude_keys = set(exclude_keys) if exclude_keys else set()
        self.default_values = default_values if default_values else {}
        self.mode = mode
        self.batch_size = batch_size
        self.callBack = callBack

    def _to_snake_case(self, name: str) -> str:
        """将PascalCase或camelCase字符串转换为snake_case。"""
        if not isinstance(name, str) or not name:
            return ""
        s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _safe_json_load(self, text: str) -> Optional[Dict]:
        """尝试使用 json.loads 解析字符串，如果失败则回退到 ast.literal_eval。"""
        try:
            return std_json.loads(text)
        except std_json.JSONDecodeError:
            try:
                return ast.literal_eval(text)
            except (ValueError, SyntaxError, MemoryError, TypeError):
                return None

    def _finalize_types(self, data_dict: dict) -> dict:
        """对字典中的值进行最终类型转换，确保可以安全写入数据库。"""
        final_data = {}
        for key, value in data_dict.items():
            if value is None:
                final_data[key] = ''
            elif isinstance(value, (dict, list)):
                final_data[key] = std_json.dumps(value, ensure_ascii=False)
            else:
                final_data[key] = value
        return final_data

    def _process_single_item(self, json_data: dict) -> Optional[Dict]:
        """根据初始化配置，处理单个JSON对象。"""
        # 步骤 1: 自动解析基础数据
        parsed_data = {}
        all_original_keys = set(json_data.keys()) | set(self.default_values.keys())

        for original_key in all_original_keys:
            if original_key in self.exclude_keys:
                continue

            value = json_data.get(original_key)
            if value is None:
                final_value = self.default_values.get(original_key)
            else:
                final_value = value

            new_key = self._to_snake_case(original_key)
            parsed_data[new_key] = final_value

        # 步骤 2: 如果有修改函数，则应用“补丁”
        if self.modifier_function:
            patch_dict = self.modifier_function(json_data)
            for original_key, patch_instruction in patch_dict.items():
                auto_generated_key = self._to_snake_case(original_key)

                # 场景A: 自定义键名和值
                if isinstance(patch_instruction, dict) and "key" in patch_instruction and "value" in patch_instruction:
                    custom_key = patch_instruction["key"]
                    custom_value = patch_instruction["value"]
                    if auto_generated_key in parsed_data:
                        del parsed_data[auto_generated_key]
                    parsed_data[custom_key] = custom_value
                # 场景B: 只修改值（或添加新字段）
                else:
                    parsed_data[auto_generated_key] = patch_instruction

        # 步骤 3: 对最终结果进行类型转换
        return self._finalize_types(parsed_data)

    def _execute_batch(self, json_list: List[Dict], filename: str, line_num: Optional[int] = None):
        """内部辅助函数，用于执行批量插入并触发回调。"""
        if not json_list:
            return

        f = io.StringIO()
        status = False
        with redirect_stdout(f):
            status = self.db_manager.upsert_batch(json_list, self.table_name)

        if self.callBack:
            try:
                self.callBack(status, json_list, filename, line_num)
            except Exception as cb_e:
                print(f"\n[ERROR] 回调函数执行失败: {cb_e}")

    def run(self, path: str, start_line: int = 1):
        """
        运行处理器。自动检测路径是文件还是目录，并根据初始化的mode进行处理。

        Args:
            path (str): 要处理的文件或目录的路径。
            start_line (int): (仅用于'line'模式) 指定开始处理的行号，用于断点续传。
        """
        if not os.path.exists(path):
            print(f"[ERROR] 路径不存在: {path}")
            return

        if self.mode == 'line' and os.path.isdir(path):
            print(f"[ERROR] 在 'line' 模式下，输入路径必须是单个文件，而不是目录: '{path}'")
            return

        files_to_process = []
        if os.path.isdir(path):
            files_to_process = [os.path.join(path, f) for f in os.listdir(path)
                                if os.path.isfile(os.path.join(path, f))
                                and f.lower().endswith(('.json', '.txt'))]
        elif os.path.isfile(path):
            files_to_process = [path]

        if not files_to_process:
            print(f"在路径 '{path}' 中未找到可处理的文件。")
            return

        print(f"\n--- 开始处理路径: {path} (模式: {self.mode}) ---")
        print(f"发现 {len(files_to_process)} 个文件待处理...")

        for i, file_path in enumerate(files_to_process):
            filename = os.path.basename(file_path)
            print(f"\n[{i + 1}/{len(files_to_process)}] 正在处理: {filename}")

            line_num = 0

            try:
                if self.mode == 'file':
                    json_list_for_file = []
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if content.strip():
                        json_data = self._safe_json_load(content)
                        if json_data:
                            parsed_dic = self._process_single_item(json_data)
                            if parsed_dic:
                                json_list_for_file.append(parsed_dic)
                        else:
                            print(f"\n[WARNING] 无法解析文件内容: {filename}")
                    self._execute_batch(json_list_for_file, filename)

                elif self.mode == 'line':
                    if start_line > 1:
                        print(f"  [INFO] 从第 {start_line} 行开始处理...")

                    total_lines = count_lines_in_single_file(file_path)
                    if total_lines is None:
                        total_lines = 0

                    json_list = []
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if line_num < start_line:
                                continue
                            if not line.strip():
                                continue

                            json_data = self._safe_json_load(line)
                            if json_data:
                                parsed_dic = self._process_single_item(json_data)
                                if parsed_dic:
                                    json_list.append(parsed_dic)

                                if total_lines > 0:
                                    percentage = (line_num / total_lines) * 100
                                    bar_length = 40
                                    filled_length = int(bar_length * line_num // total_lines)
                                    bar = '█' * filled_length + '-' * (bar_length - filled_length)
                                    progress_text = f'\r|{bar}| {percentage:.1f}% ({line_num}/{total_lines})  本批: [{len(json_list)}/{self.batch_size}]'
                                    sys.stdout.write(progress_text)
                                    sys.stdout.flush()
                                else:
                                    sys.stdout.write(f"\r当前文件行数: {line_num} | 本批已加载: [{len(json_list)}/{self.batch_size}]")

                                if len(json_list) >= self.batch_size:
                                    self._execute_batch(json_list, filename, line_num)
                                    json_list = []
                            else:
                                print(f"\n[WARNING] 解析失败，跳过文件 {filename} 的第 {line_num} 行。")

                    print()
                    self._execute_batch(json_list, filename, line_num)

                print(f"  [成功] 文件已处理。")

            except Exception as e:
                if self.mode == 'line':
                    print(f"\n  [失败] 处理文件 {filename} 的第 {line_num} 行附近时发生错误: {e}。")
                else:
                    print(f"\n  [失败] 处理文件 {filename} 时发生错误: {e}。")
                continue

        print("\n--- 所有任务处理完成 ---")


if __name__ == '__main__':
    from typing import Dict
    from MignonFramework import MySQLManager
    from MignonFramework import GenericProcessor
    from isapi.samples.redirector import excludes

    table_name = "project_info"
    original_file_name = "../xxx.txt"

    manager = MySQLManager.MysqlManager(
        "localhost",
        "root",
        "xxx",
        "xxx",
        port=3306
    )

    # 排除列表, 不需要插入的, 对应源文件中json里的字段名
    exclude = ["userName"]
    # 如果为空时的默认值, 这里默认为 ""
    default_values = {
        "userName" : ''
    }

    # 解析方法,

    def parseJson(dic: Dict[str, Any])->dict[str, str | dict[str, str]]:

        # 可用于自定义字段名, 解析方法, 当然, 这里仅覆盖目标字段
        return {
            "processedTime": datetime.now().isoformat(),
            "userName": {
                # 这里的key是自定义字段名 , value是 解析的值, 同时, 默认值优先级低于解析方法
                "value": dic["userName"],
                "key" : "user_Name"
            },
        }

    ge = GenericProcessor.GenericFileProcessor(
        manager,
        table_name,
        'line',
        modifier_function=parseJson,
        exclude_keys=excludes,
        default_values=default_values
    )


    ge.run(original_file_name)


