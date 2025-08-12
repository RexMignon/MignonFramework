import os
import json
import re
import asyncio
import aiofiles
from tqdm import tqdm
from typing import Callable, Optional, Dict, Any, Union, List
import ast

# 导入我们的新模块
from MignonFramework.ConfigReader import ConfigManager
from MignonFramework.BaseStateTracker import BaseStateTracker
from MignonFramework.SQLiteStateTracker import SQLiteStateTracker
from MignonFramework.MoveStateTracker import MoveStateTracker

# --- 辅助函数 (已采纳你的修改) ---
def _guide_user_for_config(config_manager: ConfigManager):
    """
    当配置文件不存在或不完整时，通过直接写入字符串模板来创建带详细注释的默认配置文件。
    """
    print("\n" + "=" * 60)
    print("处理器检测到配置缺失，将为您创建默认配置文件。")
    print(f"配置文件路径: {os.path.abspath(config_manager.filename)}")
    print("请在该文件中填写您的路径信息后再次运行。")
    print("=" * 60 + "\n")

    # 使用你指定的 [config] 节名和新路径
    config_template = f"""[config]
; --- 运行模式 ---
; mode: 运行模式。可选值为 config 或 move。
; config: 使用SQLite数据库记录文件状态 (默认, 推荐)。
; move:   物理移动处理过的文件到 "finish" 或 "exception" 目录。
mode = config

; --- 核心路径配置 ---
input_dir = ./res/input
output_dir = ./res/output
; exception_dir: 处理失败的源文件的存放目录 (两种模式下均生效)。
exception_dir = ./res/exception

; --- "move" 模式专属配置 ---
; finish_dir: 成功处理的源文件的存放目录 (仅在 mode = move 时生效)。
finish_dir = ./res/finish

; --- "config" 模式专属配置 ---
; db_path: SQLite数据库文件路径 (仅在 mode = config 时生效)。
db_path = ./resources/state/file_status.db
; db_table_name: SQLite数据库中的表名 (仅在 mode = config 时生效)。
db_table_name = file_status

; --- 输出文件配置 ---
output_base_name = output
output_extension = jsonl
max_lines_per_file = 10000

; --- 数据处理配置 ---
filename_key = source_filename
"""
    try:
        config_dir = os.path.dirname(config_manager.config_path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)

        with open(config_manager.config_path, 'w', encoding='utf-8') as f:
            f.write(config_template)
    except Exception as e:
        print(f"[错误] 创建默认配置文件失败: {e}")

# --- 公开的、同步的 `run` 接口 ---
def run(config_path: str = './resources/config/processFile.ini'):
    """
    本模块对外的同步主接口。
    它通过读取配置文件来驱动整个文件处理流程。
    """
    # 注意：这里的 section 需要和你生成的模板保持一致
    config = ConfigManager(filename=config_path, section='config')
    settings = config.get_all_fields()

    if not settings or not settings.get('input_dir'):
        _guide_user_for_config(config)
        return

    mode = settings.get('mode', 'config')
    state_tracker: BaseStateTracker
    if mode == 'move':
        state_tracker = MoveStateTracker(
            finish_dir=settings['finish_dir'],
            exception_dir=settings['exception_dir']
        )
        print("运行模式: move (移动文件)")
    else:
        state_tracker = SQLiteStateTracker(
            db_path=settings['db_path'],
            table_name=settings.get('db_table_name', 'file_status'),
            exception_dir=settings.get('exception_dir')
        )
        print("运行模式: config (使用SQLite数据库)")

    with state_tracker:
        asyncio.run(_process_files_core(
            settings=settings,
            state_tracker=state_tracker
        ))

# --- 内部核心异步逻辑 ---

def _default_parse_func(content: str) -> Union[Dict[str, Any], List[Any]]:
    """默认解析器"""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(content)
        except Exception as e:
            raise ValueError(f"Failed to parse with both json and ast. AST Error: {e}") from e

def _get_line_count(file_path: str) -> int:
    if not os.path.exists(file_path):
        return 0
    with open(file_path, 'rb') as f:
        return sum(1 for _ in f)

def _find_latest_output_file(output_dir: str, base_name: str, extension: str):
    if not os.path.isdir(output_dir):
        return None, -1
    pattern = re.compile(rf"^{re.escape(base_name)}_(\d+)\.{re.escape(extension)}$")
    max_index = -1
    latest_file = None
    for filename in os.listdir(output_dir):
        match = pattern.match(filename)
        if match:
            index = int(match.group(1))
            if index > max_index:
                max_index = index
                latest_file = os.path.join(output_dir, filename)
    return latest_file, max_index

async def _process_files_core(
        settings: Dict[str, Any],
        state_tracker: BaseStateTracker
):
    """内部异步实现，现在接收配置字典和状态追踪器。"""
    input_dir = settings['input_dir']
    output_dir = settings['output_dir']
    output_base_name = settings['output_base_name']
    output_extension = settings['output_extension']
    max_lines_per_file = int(settings['max_lines_per_file'])
    filename_key = settings['filename_key']

    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    all_files_in_dir = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
    source_files = state_tracker.get_unprocessed_files(all_files_in_dir)

    if not source_files:
        print("所有文件均已处理，无需执行新操作。")
        return

    latest_file, latest_index = _find_latest_output_file(output_dir, output_base_name, output_extension)
    file_index = latest_index if latest_index != -1 else 0
    current_line_count = _get_line_count(latest_file) if latest_file else 0

    if latest_file and current_line_count >= max_lines_per_file:
        file_index += 1
        current_line_count = 0

    output_file_path = os.path.join(output_dir, f'{output_base_name}_{file_index}.{output_extension}')
    async with aiofiles.open(output_file_path, 'a', encoding='utf-8') as f_out:
        print(f"找到 {len(source_files)} 个新文件，开始处理并写入到: {output_file_path}")

        for file_path in tqdm(source_files, desc="文件处理进度"):
            try:
                if current_line_count >= max_lines_per_file:
                    await f_out.close()
                    file_index += 1
                    current_line_count = 0
                    output_file_path = os.path.join(output_dir, f'{output_base_name}_{file_index}.{output_extension}')
                    f_out = await aiofiles.open(output_file_path, 'a', encoding='utf-8')
                    print(f"\n切换到新文件: {output_file_path}")

                with open(file_path, 'r', encoding='utf-8') as f_in:
                    content = f_in.read()

                data = _default_parse_func(content)
                if not isinstance(data, dict):
                    raise TypeError("解析后的数据不是一个字典")

                data[filename_key] = os.path.basename(file_path)
                await f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
                current_line_count += 1

                # --- 修正：已移除 await ---
                state_tracker.mark_as_finished(file_path)

            except Exception as e:
                error_msg = str(e)
                filename = os.path.basename(file_path)
                print(f"\n[处理失败] 文件名: {filename}")
                print(f"  错误信息: {error_msg}")
                # --- 修正：已移除 await ---
                state_tracker.mark_as_exception(file_path, error_msg)
                continue

# --- 运行入口 ---
if __name__ == '__main__':
    run()