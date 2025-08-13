"""
运行日志
"""
import os
import sys
import json
from datetime import datetime



def log_message(message, log_path, log_name="log.txt"):
    """
    保存日志消息到指定文件。

    日志格式为："时间":"保存的消息"。
    日志文件最多保存两条日志。如果超过两条，最旧的日志会被新的日志覆盖。

    Args:
        message (str): 要保存的日志消息。
        log_path (str): 日志文件保存的路径。
        log_name (str, optional): 日志文件的名称。默认为 "log.txt"。
    """
    # 获取当前脚本所在的目录
    # 这确保了即使函数被导入并在其他地方调用，也能正确找到相对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 如果日志路径是相对路径，则将其转换为相对于脚本目录的绝对路径
    if not os.path.isabs(log_path):
        log_path = os.path.join(script_dir, log_path)

    full_log_path = os.path.join(log_path, log_name)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f'"{current_time}":"{message}"'

    try:
        os.makedirs(log_path, exist_ok=True)
        with open(full_log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')

    except Exception as e:
        print(f"保存日志时发生错误: {e}", file=sys.stderr)


