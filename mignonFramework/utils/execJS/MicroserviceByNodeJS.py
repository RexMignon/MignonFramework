import subprocess
import requests
import atexit
import time
import os
import socket
import sys
import threading
from functools import wraps

# 假设这个模块是存在的，根据您的代码保留
# 我们将使用 Any 类型来增加 logger 参数的灵活性
from mignonFramework.utils.Logger import Logger
from typing import Any

# 为了处理标准 logging 或 loguru logger，需要引入 logging
import logging


class MicroServiceByNodeJS:
    import subprocess
import requests
import atexit
import time
import os
import socket
import sys
import threading
from functools import wraps

# 假设这个模块是存在的，根据您的代码保留
# 我们将使用 Any 类型来增加 logger 参数的灵活性
from mignonFramework.utils.Logger import Logger
from typing import Any

# 为了处理标准 logging 或 loguru logger，需要引入 logging
import logging


class MicroServiceByNodeJS:
    # 将 logger 的类型提示改为 Any，以允许传入不同类型的 logger 对象
    def __init__(self, client_only=False, logger:Any=None,
                 url_base="http://127.0.0.1:3000", # 默认传入完整的地址
                 scan_dir="./resources/js",
                 node_modules_path=None,  # 新增: node_modules 文件夹的位置
                 invoker_path=None, js_log_print=True):

        current_dir = os.path.dirname(os.path.abspath(__file__))
        static_folder = os.path.join(current_dir, '../starterUtil', "static")

        # 移除 self.port
        self.js_log = js_log_print

        if invoker_path is None:
            invoker_path = os.path.join(static_folder, 'js', "invoker.js")

        self.url_base = url_base # 直接使用传入的完整 URL
        self.node_modules_path = node_modules_path # 保存 node_modules 路径

        self.process = None
        self.client_only = client_only
        self.logger:Any = logger

        # 启动服务时传递 node_modules_path 和 url_base
        self._start_server(invoker_path, scan_dir, node_modules_path)

    def _get_log_func(self, level: str, output_stream):
        """
        根据 logger 的类型（Mignon Logger, Loguru, 标准 Logging）和请求的 level，
        动态返回一个可调用的日志函数 func(message)。
        """
        logger = self.logger
        if not logger:
            return lambda msg: print(msg, file=output_stream)

        # 1. 优先适配 Mignon 自定义 Logger (Logger.py)
        # 特征: 拥有 write_log 方法
        if hasattr(logger, 'write_log'):
            level_upper = level.upper()
            return lambda msg: logger.write_log(level_upper, msg)

        # 2. 适配 Loguru 或 标准 Logging
        # 特征: 拥有 info, error, warning 等小写方法
        method_name = level.lower()
        if method_name == 'warn':
            method_name = 'warning'

        # 尝试获取对应级别的方法，例如 logger.info 或 logger.error
        log_method = getattr(logger, method_name, None)

        # 如果获取不到（例如 level="SYSTEM" 但标准库没有 system 方法），则回退到 info
        if not log_method:
            log_method = getattr(logger, 'info', None)

        if log_method:
            return log_method

        # 3. 实在无法识别，回退到 print
        return lambda msg: print(msg, file=output_stream)

    def _stream_printer(self, stream, output_stream, level="INFO"):
        """
        在后台线程中读取子进程的流, 并将其直接打印到Python的标准流中.
        支持动态识别 Logger 类型并分发到对应级别 (INFO/ERROR)。
        """
        try:
            # 在循环外解析一次日志函数，避免在 while 循环中频繁 getattr/hasattr
            log_func = self._get_log_func(level, output_stream)

            for line in iter(stream.readline, ''):
                line = line.strip()
                if line:
                    log_func(line)
            stream.close()
        except Exception as e:
            # 主进程关闭时，这里的读取可能会出错，属于正常现象
            pass

    # 移除 _is_port_in_use 和 _find_and_kill_process_on_port

    def _verify_service(self):
        """验证 Node.js 服务是否正在运行"""
        try:
            # 完整使用 self.url_base
            response = requests.get(f'{self.url_base}/status', timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('service_name') == 'js_invoker_microservice'
        except (requests.exceptions.RequestException, ValueError):
            return False
        return False

    # 启动服务时传递 node_modules_path 和 url_base
    def _start_server(self, invoker_path, scan_dir, node_modules_path):
        if self.client_only:
            if not self._verify_service():
                raise ConnectionError(f"在 client_only 模式下，无法连接到{self.url_base} 上的服务。")
            return

        # 不再进行端口占用检查和杀进程操作，仅检查服务是否运行
        if self._verify_service():
            print(f"Node.js 服务已在 {self.url_base} 上运行，跳过启动。")
            return

        if not os.path.exists(invoker_path):
            raise FileNotFoundError(f"Invoker file not found: {invoker_path}")

        command = ['node', invoker_path]

        # 1. 扫描目录 (invike.js 的 process.argv[2])
        # 修正: 即使为空也传递空字符串，保证位置对齐
        command.append(scan_dir if scan_dir else "")

        # 2. node_modules 路径 (invike.js 的 process.argv[3])
        # 修正: 即使为空也传递空字符串，防止 url_base 补位导致解析错误
        command.append(node_modules_path if node_modules_path else "")

        # 3. 完整的 url_base (invike.js 的 process.argv[4])，用于 Node.js 提取端口
        command.append(self.url_base)

        project_root = os.getcwd()
        env = os.environ.copy()

        # 移除 NODE_PATH 逻辑，因为现在由命令行参数传递给 invike.js 处理

        popen_kwargs = {
            "cwd": project_root,
            "env": env,
            "shell": False
        }

        if self.js_log:
            # 重定向输出流到管道
            popen_kwargs['stdout'] = subprocess.PIPE
            popen_kwargs['stderr'] = subprocess.PIPE
            popen_kwargs['text'] = True
            popen_kwargs['bufsize'] = 1
        else:
            popen_kwargs['stdout'] = subprocess.DEVNULL
            popen_kwargs['stderr'] = subprocess.DEVNULL

        self.process = subprocess.Popen(command, **popen_kwargs)

        # 如果开启了日志，则启动后台线程来打印日志
        if self.js_log:
            # STDOUT -> INFO 级别
            stdout_thread = threading.Thread(
                target=self._stream_printer,
                args=(self.process.stdout, sys.stdout, "INFO")
            )
            stdout_thread.daemon = True
            stdout_thread.start()

            # STDERR -> ERROR 级别
            stderr_thread = threading.Thread(
                target=self._stream_printer,
                args=(self.process.stderr, sys.stderr, "ERROR")
            )
            stderr_thread.daemon = True
            stderr_thread.start()

        atexit.register(self.shutdown)
        print(f"Node.js Service process has been started, targeting URL {self.url_base}.")

        # 等待服务启动并验证
        time.sleep(2) # 给予一些时间启动
        if not self._verify_service():
            raise ConnectionError(f"Node.js 服务启动失败或在 {self.url_base} 上无法访问。")

    def invoke(self, file_name, func_name, *args, **kwargs):
        payload = {
            'func_name': func_name,
            'args': list(args)
        }
        # 完整使用 self.url_base
        url = f"{self.url_base}/{file_name}/invoke"

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result['success']:
                return result['result']
            else:
                error_message = f"JS execution failed: {result.get('error', '未知错误')}"
                print(error_message, file=sys.stderr)
                raise RuntimeError(error_message)
        except requests.exceptions.RequestException as e:
            print(f"Could not connect to Node.js service at {self.url_base}: {e}", file=sys.stderr)
            if self.process:
                self.shutdown()
            raise ConnectionError(f"Could not connect to Node.js service at {self.url_base}: {e}")

    def shutdown(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
                print("Node.js service shut down gracefully.")
            except subprocess.TimeoutExpired:
                print("Node.js service did not terminate, killing it.", file=sys.stderr)
                self.process.kill()
            self.process = None

    def evalJS(self, file_name, func_name=None):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                nonlocal func_name
                if func_name is None:
                    func_name = func.__name__

                return self.invoke(file_name, func_name, *args, **kwargs)

            return wrapper

        return decorator

    def startAsMicro(self):
        try:
            while True:
                # 保持主线程活跃
                time.sleep(1)
        except KeyboardInterrupt:
            print("Received exit signal, shutting down service.")
            self.shutdown()