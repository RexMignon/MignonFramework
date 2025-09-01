import os
import sys
import time
import functools
import traceback
from datetime import datetime
import threading
import contextlib

class _Colors:
    """一个用于存储 ANSI 颜色代码的内部类。"""
    RESET = '\033[0m'
    RED = '\033[31m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    MAGENTA = '\033[35m' # 为 EXIST 级别新增颜色

class _AutoLoggerStream:
    """
    一个自定义的流对象，用于拦截所有标准输出。
    它能智能区分普通 print 和带 \r 的单行更新。
    """
    def __init__(self, logger_instance):
        self._logger = logger_instance
        self._original_stdout = sys.__stdout__
        self._lock = threading.RLock()

    def write(self, text):
        """
        当任何代码调用 print() 或 sys.stdout.write() 时，此方法会被自动调用。
        增加了对 bytes 类型的兼容处理。
        """
        if isinstance(text, bytes):
            # 使用 'utf-8' 解码，并忽略无法解码的字节，以增加健壮性
            try:
                text = text.decode('utf-8', errors='ignore')
            except Exception:
                # 如果解码失败，则尝试使用系统默认编码
                try:
                    text = text.decode(sys.getdefaultencoding(), errors='ignore')
                except Exception:
                    # 如果仍然失败，则直接输出原始字节表示形式，避免崩溃
                    self._original_stdout.write(f"[Logger Codec Error] Could not decode bytes: {text!r}\n")
                    return

        # 检查全局的、线程安全的日志激活状态
        if not self._logger.is_active:
            self._original_stdout.write(text)
            return

        try:
            with self._lock:
                # 特殊处理 \r，以在控制台实现单行刷新效果
                if '\r' in text and '\n' not in text:
                    timestamp = self._logger.get_timestamp()
                    level = "INFO"
                    message = text.strip()

                    level_color = self._logger.color_map.get(level, '')
                    console_message = (
                        f"{timestamp} {_Colors.BLUE}[main]{_Colors.RESET} "
                        f"{level_color}[{level}]{_Colors.RESET} {message}"
                    )
                    self._original_stdout.write('\r' + console_message)
                    self._original_stdout.flush()

                    self._logger.write_log_to_file_only(level, message, timestamp)
                    return

                # 对普通 print 内容进行处理
                stripped_text = text.strip()
                if not stripped_text:
                    self._original_stdout.write(text)
                    return

                # 直接构建消息并写入，以获得更精确的控制
                timestamp = self._logger.get_timestamp()
                level = "INFO"
                level_color = self._logger.color_map.get(level, '')
                # 普通print自带换行, console_message不加\n
                console_message = (
                    f"{timestamp} {_Colors.BLUE}[main]{_Colors.RESET} "
                    f"{level_color}[{level}]{_Colors.RESET} {stripped_text}"
                )
                sys.__stdout__.write(console_message + '\n')
                sys.__stdout__.flush()
                self._logger.write_log_to_file_only(level, stripped_text, timestamp)

        except KeyboardInterrupt:
            timestamp = self._logger.get_timestamp()
            level = "EXIST"
            level_color = self._logger.color_map.get(level, '')
            console_message = (
                f"\n{timestamp} {_Colors.BLUE}[main]{_Colors.RESET} "
                f"{level_color}[{level}]{_Colors.RESET} User interruption detected. Exiting gracefully."
            )
            self._original_stdout.write(console_message + '\n')
            self._original_stdout.flush()
            sys.exit(130)
        # 增加对其他异常的捕获，防止日志系统本身崩溃
        except Exception as e:
            tb_string = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            error_msg = f"FATAL: Exception in _AutoLoggerStream.write.\n  - Error: {e!r}\n  - Traceback:\n{tb_string}"
            sys.__stderr__.write(error_msg)


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
            "SYSTEM": _Colors.CYAN,
            "EXIST": _Colors.MAGENTA # 新增 EXIST 级别颜色
        }

        # 使用普通的实例变量存储状态
        self._patch_is_active = enabld
        # 创建一个专用的锁来保护这个状态
        self._patch_state_lock = threading.RLock()

        if enabld:
            # 在替换sys.stdout之前，先保存原始的stdout
            self._original_stdout = sys.stdout
            sys.stdout = _AutoLoggerStream(self)
            self.write_log("SYSTEM", "Auto-logging enabled. Standard output is now being logged.")

    # 创建线程安全的属性来访问和修改状态
    @property
    def is_active(self):
        with self._patch_state_lock:
            return self._patch_is_active

    @is_active.setter
    def is_active(self, value):
        with self._patch_state_lock:
            self._patch_is_active = bool(value)

    @contextlib.contextmanager
    def disabled(self):
        """
        一个上下文管理器，用于临时禁用 stdout 的自动日志记录。
        """
        original_state = self.is_active
        try:
            self.is_active = False
            yield
        finally:
            self.is_active = original_state

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

        if base_path not in self._line_counts:
            self._line_counts[base_path] = self._count_lines_in_file(base_path)
        if self._line_counts[base_path] < self.MAX_LOG_LINES:
            return base_path

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

        # 对多行消息进行处理，确保每行都有时间戳
        lines = str(message).split('\n')

        with self._lock:
            log_file = self._get_current_log_filepath()
            try:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                with open(log_file, 'a', encoding='utf-8') as f:
                    for line in lines:
                        file_message = f"{timestamp} [main] [{level}] {line}"
                        f.write(file_message + '\n')
                        self._line_counts[log_file] = self._line_counts.get(log_file, 0) + 1
            except Exception as e:
                sys.__stderr__.write(f"FATAL: Logger failed to write to file. Error: {e}\n")

    def write_log(self, level: str, message: str):
        """将格式化的消息写入控制台和文件。"""
        timestamp = self.get_timestamp()

        level_color = self.color_map.get(level, '')

        # 确保日志消息总是在新的一行开始
        console_message = (
            f"\n{timestamp} {_Colors.BLUE}[main]{_Colors.RESET} "
            f"{level_color}[{level}]{_Colors.RESET} {message}"
        )

        # 错误消息写入 stderr，其他写入原始的 stdout
        output_stream = sys.__stderr__ if level == "ERROR" else getattr(self, '_original_stdout', sys.__stdout__)
        output_stream.write(console_message + '\n')
        output_stream.flush()

        self.write_log_to_file_only(level, message, timestamp)

    def __call__(self, func):
        """核心装饰器逻辑，用于 @log。"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except KeyboardInterrupt:
                self.write_log("EXIST", f"User interruption in function '{func.__name__}'. Exiting gracefully.")
                sys.exit(130)
            except Exception as e:
                tb_string = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                error_msg = f"Exception in function '{func.__name__}'.\n  - Error: {e!r}\n  - Traceback:\n{tb_string}"
                self.write_log("ERROR", error_msg)
                raise
        return wrapper
