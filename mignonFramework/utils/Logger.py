import os
import sys
import time
import functools
import traceback
from datetime import datetime
import threading

class _Colors:
    """一个用于存储 ANSI 颜色代码的内部类。"""
    RESET = '\033[0m'
    RED = '\033[31m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'

class _AutoLoggerStream:
    """
    一个自定义的流对象，用于拦截所有标准输出。
    它能智能区分普通 print 和带 \r 的单行更新。
    """
    def __init__(self, logger_instance):
        self._logger = logger_instance
        self._original_stdout = sys.__stdout__
        self._lock = threading.RLock()

    def write(self, text: str):
        """当任何代码调用 print() 或 sys.stdout.write() 时，此方法会被自动调用。"""
        try:
            with self._lock:
                # 特殊处理 \r，以在控制台实现单行刷新效果
                if '\r' in text and '\n' not in text:
                    # 1. 准备日志内容和元数据
                    timestamp = self._logger.get_timestamp()
                    level = "INFO"
                    message = text.strip()

                    # 2. 准备并写入带前缀的控制台消息
                    level_color = self._logger.color_map.get(level, '')
                    console_message = (
                        f"{timestamp} {_Colors.BLUE}[main]{_Colors.RESET} "
                        f"{level_color}[{level}]{_Colors.RESET} {message}"
                    )
                    self._original_stdout.write('\r' + console_message)
                    self._original_stdout.flush()

                    # 3. 将纯文本日志写入文件
                    self._logger.write_log_to_file_only(level, message, timestamp)
                    return

                # 对普通 print 内容进行处理
                stripped_text = text.strip()
                if not stripped_text:
                    self._original_stdout.write(text)
                    return

                self._logger.write_log("INFO", stripped_text)
        except KeyboardInterrupt:
            # 当用户按下 Ctrl+C 时，提供一个干净的退出，而不是显示一个混乱的堆栈跟踪。
            timestamp = self._logger.get_timestamp()
            level = "EXIST"

            # 2. 准备并写入带前缀的控制台消息
            level_color = self._logger.color_map.get(level, '')
            console_message = (
                f"{timestamp} {_Colors.BLUE}[main]{_Colors.RESET} "
                f"{level_color}[{level}]{_Colors.RESET}"
            )
            self._original_stdout.write(f"\n{console_message} interruption detected. Exiting gracefully.\n")
            # 干净地退出程序，返回一个表示被中断的状态码
            sys.exit(130)

    def flush(self):
        """提供 flush 方法以兼容标准流接口。"""
        self._original_stdout.flush()

class Logger:
    """
    一个健壮的、混合模式的日志框架，支持日志分割和彩色输出。
    """
    MAX_LOG_LINES = 100000 # 日志文件最大行数

    def __init__(self, enabld=False, log_path='./resources/log', name_template='{date}.log'):
        self._log_path = log_path
        self._name_template = name_template
        self._lock = threading.RLock()
        self._line_counts = {} # 缓存每个日志文件的行数
        self.color_map = {
            "INFO": _Colors.YELLOW,
            "ERROR": _Colors.RED,
            "SYSTEM": _Colors.CYAN
        }

        if enabld:
            sys.stdout = _AutoLoggerStream(self)
            self.write_log("SYSTEM", "Auto-logging enabled. Standard output is now being logged.")

    def get_timestamp(self) -> str:
        """返回一个带毫秒的高精度时间戳字符串。"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _count_lines_in_file(self, filepath: str) -> int:
        """高效地计算文件行数。"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except FileNotFoundError:
            return 0

    def _get_current_log_filepath(self) -> str:
        """获取当前可用的日志文件路径，实现自动分割。"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        base_filename = self._name_template.format(date=date_str)
        base_path = os.path.join(os.getcwd(), self._log_path, base_filename)

        # 检查主日志文件
        if base_path not in self._line_counts:
            self._line_counts[base_path] = self._count_lines_in_file(base_path)
        if self._line_counts[base_path] < self.MAX_LOG_LINES:
            return base_path

        # 如果主文件已满，查找分割文件
        index = 0
        while True:
            name, ext = os.path.splitext(base_filename)
            rotated_filename = f"{name}_{index}{ext}"
            rotated_path = os.path.join(os.getcwd(), self._log_path, rotated_filename)

            if rotated_path not in self._line_counts:
                self._line_counts[rotated_path] = self._count_lines_in_file(rotated_path)

            if self._line_counts[rotated_path] < self.MAX_LOG_LINES:
                return rotated_path
            index += 1

    def write_log_to_file_only(self, level: str, message: str, timestamp: str = None):
        """只将日志写入文件，用于处理 \r 等特殊情况。"""
        if timestamp is None:
            timestamp = self.get_timestamp()

        file_message = f"{timestamp} [main] [{level}] {message}"
        log_file = self._get_current_log_filepath()

        with self._lock:
            try:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(file_message + '\n')
                self._line_counts[log_file] = self._line_counts.get(log_file, 0) + 1
            except Exception as e:
                sys.__stderr__.write(f"FATAL: Logger failed to write to file. Error: {e}\n")

    def write_log(self, level: str, message: str):
        """将格式化的消息写入控制台和文件。"""
        timestamp = self.get_timestamp()

        # 准备并打印控制台日志
        level_color = self.color_map.get(level, '')
        console_message = f"{timestamp} {_Colors.BLUE}[main]{_Colors.RESET} {level_color}[{level}]{_Colors.RESET} {message}"
        output_stream = sys.__stderr__ if level == "ERROR" else sys.__stdout__
        output_stream.write(console_message + '\n')
        output_stream.flush()

        # 将日志写入文件
        self.write_log_to_file_only(level, message, timestamp)

    def __call__(self, func):
        """核心装饰器逻辑，用于 @log。"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                tb_string = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                error_msg = f"Exception in function '{func.__name__}'.\n  - Error: {e!r}\n  - Traceback:\n{tb_string}"
                self.write_log("ERROR", error_msg)
                raise
        return wrapper



