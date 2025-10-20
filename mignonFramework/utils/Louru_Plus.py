import logging
import sys
import os
import inspect
import re
from loguru import logger
from typing import Union, Any, Callable, Dict
from functools import wraps


def strip_ansi_codes(text: str) -> str:
    """
    使用正则表达式移除字符串中的 ANSI 转义码。
    """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


class LoguruPlus:
    _initialized = False
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    console_format: str
    file_format: str
    _THIS_FILENAME = os.path.basename(__file__)

    class _InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 0
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    def __init__(self, level: Union[str, int] = "INFO", enable_console: bool = True, formats: str = None,
                 file_formats: str = None, hiddenStackTrace: bool = False,
                 filter_: Callable[[Dict[str, Any]], bool] = None
                 , colorize=True):
        self.console_format: Callable[[Dict[str, Any]], Any] | None | (Dict[str, Any]) | str = None
        if self._initialized: return
        logger.remove()

        self.hiddenStackTrace = hiddenStackTrace
        self.file_format = file_formats

        if enable_console:
            if formats is None:
                def formatter(record):
                    # 优先从 extra 字典中获取 (来自 getLogger 的日志)
                    module = record["extra"].get("module_name")
                    class_ = record["extra"].get("class_name")
                    func = record["extra"].get("function_name")

                    if not module:
                        module = record["name"]
                    if not func:
                        func = record["function"]

                    caller_parts = []
                    if module:
                        if module == "__main__":
                            module = os.path.splitext(os.path.basename(record["file"].path))[0]
                        caller_parts.append(f"<blue>{module}</blue>")

                    if class_:
                        caller_parts.append(f"<yellow>{class_}</yellow>")

                    # 避免重复显示模块名 (例如 werkzeug.log_request)
                    if func and func not in module:
                        func_display = "$module" if func == "<module>" else func
                        caller_parts.append(f"<dim>{func_display}</dim>")

                    formatted_caller = ".".join(caller_parts)

                    return (
                        "<magenta>{time:YYYY-MM-DD HH:mm:ss.SSS}</magenta> "
                        "<level>[{level}]</level> "
                        f"{formatted_caller}"
                        "<cyan> @{line} </cyan> "
                        "<yellow>=> </yellow>"
                        "<level>{message}</level>\n"
                    )

                if hiddenStackTrace:
                    self.console_format = (
                        "<magenta>{time:YYYY-MM-DD HH:mm:ss.SSS}</magenta> "
                        "<level>[{level}]</level> "
                        "*.*"
                        "<cyan> @{line} </cyan> "
                        "<yellow>=> </yellow>"
                        "<level>{message}</level>\n"
                    )
                else:
                    self.console_format = formatter
            else:
                self.console_format = formats

            logger.configure(extra={"module_name": "", "class_name": None, "function_name": ""})
            logger.add(sys.stderr, level=level, format=self.console_format, colorize=colorize, filter=filter_)

        logging.basicConfig(handlers=[self._InterceptHandler()], level=0, force=True)
        self.__class__._initialized = True

    def add_file_handler(self, name: str, path: str = "./resources/log", level: str = "INFO",
                         formats: str = None, rotation: str = "3 MB", retention: str = "10 days",
                         compression: str = "zip", encoding: str = "utf-8"):
        """
        添加一个带过滤器的文件日志处理器。
        只有 record["name"] 以 `name` 参数开头的日志才会被写入。
        适用于为特定模块（如 'database', 'api'）创建独立的日志文件。

        :param encoding:
        :param name: 日志文件名前缀，也用作过滤器。
        :param path: 日志文件存放目录。
        :param level: 日志级别。
        :param formats: 自定义此文件处理器的日志格式。如果为 None，则使用初始化时定义的 `file_formats`，否则使用默认格式。
        :param rotation: 日志文件轮转条件。
        :param retention: 日志文件保留时间。
        :param compression: 日志文件压缩格式。
        """
        os.makedirs(path, exist_ok=True)
        file_path_template = os.path.join(path, f"{name}.{{time:YYYY-MM-DD}}.log")

        if self.hiddenStackTrace:
            default_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} [{level}] *.* @{line} => {message}\n"
        else:
            default_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} [{level}] {name}.{function} @{line} => {message}\n"

        # 优先级: 方法参数 format > 实例属性 self.file_format > 默认格式
        final_format = formats or self.file_format or default_format

        def formatter(record):
            record["message"] = strip_ansi_codes(str(record["message"]))
            return final_format

        logger.add(
            sink=file_path_template, level=level,
            format=formatter,
            encoding=encoding,
            rotation=rotation, retention=retention, compression=compression,
            filter=lambda record: record["name"].startswith(name)
        )

    def add_main_log_file(self, name: str = "main", path: str = "./resources/log", level: str = "INFO",
                          formats: str = None, rotation: str = "10 MB", retention: str = "10 days",
                          compression: str = "zip", filter_: Callable[[Dict[str, Any]], bool] = None, encoding="utf-8"):
        """
        添加一个不过滤的、捕获所有日志的主日志文件处理器。
        所有流经 Loguru 的日志（包括从其他库拦截的）都会被写入。
        适用于创建应用的主日志文件。

        :param encoding:
        :param filter_:
        :param formats:
        :param name: 主日志文件名前缀。
        :param path: 日志文件存放目录。
        :param level: 日志级别。
        :param rotation: 日志文件轮转条件。
        :param retention: 日志文件保留时间。
        :param compression: 日志文件压缩格式。
        """
        os.makedirs(path, exist_ok=True)
        file_path_template = os.path.join(path, f"{name}.{{time:YYYY-MM-DD}}.log")

        if self.hiddenStackTrace:
            default_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} [{level}] *.* @{line} => {message}\n"
        else:
            default_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} [{level}] {name}.{function} @{line} => {message}\n"

        # 优先级: 方法参数 format_ > 实例属性 self.file_format > 默认格式
        final_format = formats or self.file_format or default_format

        def formatter(record):
            record["message"] = strip_ansi_codes(str(record["message"]))
            return final_format

        logger.add(
            sink=file_path_template, level=level,
            format=formatter,
            encoding=encoding,
            filter=filter_,
            rotation=rotation, retention=retention, compression=compression
        )

    def setUpLogger(self, exclude: list[str] = None, proxy_only: list[str] = None) -> None:
        """
        自动发现并拦截所有标准库 logging 的记录器，将它们的输出重定向到 Loguru。

        :param exclude: 一个字符串列表，包含不应被拦截的 logger 名称。
        :param proxy_only: 一个字符串列表，包含应保留其现有 handler 的 logger 名称。
                           对于这些 logger，Loguru 的拦截器仅作为代理添加，而不会清空它们原有的 handler。
        """
        if exclude is None:
            exclude = []
        if proxy_only is None:
            proxy_only = []
        intercept_handler = self._InterceptHandler()

        for logger_name in list(logging.root.manager.loggerDict):
            if logger_name in exclude:
                continue

            _logger = logging.getLogger(logger_name)

            # 如果当前 logger 不在 proxy_only 列表中，则清空其 handlers
            if logger_name not in proxy_only:
                _logger.handlers.clear()

            _logger.addHandler(intercept_handler)
            _logger.propagate = False

        # 单独处理 root logger
        if "root" not in exclude:
            # 如果 root logger 不在 proxy_only 列表中，则清空其 handlers
            if "root" not in proxy_only:
                logging.root.handlers.clear()

            logging.root.addHandler(intercept_handler)

    def getLogger(self, name: str = None):
        """
        获取一个 Loguru logger 实例，并自动推断调用者信息。
        如果从类的方法中调用，会自动在 name 后附加类名。
        """
        if name is None:
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            if module:
                name = module.__name__
                if name == '__main__':
                    filename = os.path.basename(module.__file__)
                    name = os.path.splitext(filename)[0]
            else:
                name = "unknown"

        def patcher(record):
            module_name = name
            class_name = None

            log_frame = inspect.currentframe()
            while log_frame and os.path.basename(log_frame.f_code.co_filename) in ("_logger.py", self._THIS_FILENAME):
                log_frame = log_frame.f_back

            if log_frame and 'self' in log_frame.f_locals:
                class_name = log_frame.f_locals['self'].__class__.__name__

            record["extra"]["module_name"] = module_name
            record["extra"]["class_name"] = class_name
            record["extra"]["function_name"] = record["function"]

            if class_name:
                record["name"] = f"{module_name}.{class_name}"
            else:
                record["name"] = module_name

        def patcherByHiddenStackTrace(record):
            pass

        if self.hiddenStackTrace:
            return logger.patch(patcherByHiddenStackTrace)
        else:
            return logger.patch(patcher)

    @staticmethod
    def shutdown():
        logger.complete()
        logging.shutdown()


def SendLog(level: str, **kwargs: Any):
    def decorator(func):
        logger.add(func, level=level, **kwargs)
        return func

    return decorator
