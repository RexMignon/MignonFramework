import subprocess
import requests
import atexit
import time
import os
import socket
import sys
import threading
from functools import wraps

from mignonFramework.utils.Logger import Logger


class MicroServiceByNodeJS:
    def __init__(self, client_only=False, logger:Logger=None, port=3000, url_base="127.0.0.1", scan_dir="./resources/js",
                 invoker_path=None, js_log_print=True):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        static_folder = os.path.join(current_dir, 'starterUtil', "static")
        self.port = port
        self.js_log = js_log_print
        if invoker_path is None:
            invoker_path = os.path.join(static_folder, 'js', "invoker.js")
        self.url_base = f"http://{url_base}:{self.port}"
        self.process = None
        self.client_only = client_only
        self.logger:Logger = logger
        self._start_server(invoker_path, scan_dir)

    def _stream_printer(self, stream, output_stream):
        """
        在后台线程中读取子进程的流, 并将其直接打印到Python的标准流中.
        你全局的 Logger Hook 会自动捕获这里的 print 输出.
        """
        try:
            for line in iter(stream.readline, ''):
                if line:
                    self.logger.write_log("INFO", line.strip())
            stream.close()
        except Exception as e:
            # 主进程关闭时，这里的读取可能会出错，属于正常现象
            pass

    def _is_port_in_use(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', self.port)) == 0

    def _verify_service(self):
        try:
            response = requests.get(f'{self.url_base}/status', timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('service_name') == 'js_invoker_microservice'
        except (requests.exceptions.RequestException, ValueError):
            return False
        return False

    def _find_and_kill_process_on_port(self, port):
        pid = None
        if sys.platform in ['linux', 'darwin']:
            try:
                output = subprocess.check_output(['lsof', '-i', f':{port}'], universal_newlines=True)
                lines = output.strip().split('\n')
                if len(lines) > 1:
                    pid = lines[1].split()[1]
            except subprocess.CalledProcessError:
                pid = None
        elif sys.platform == 'win32':
            try:
                output = subprocess.check_output(['netstat', '-ano'], universal_newlines=True)
                lines = [line for line in output.split('\n') if f':{port}' in line]
                if lines:
                    pid = lines[0].strip().split()[-1]
            except subprocess.CalledProcessError:
                pid = None

        if pid:
            try:
                print(f"检测到端口 {port} 被进程 {pid} 占用，正在尝试强制关闭。")
                if sys.platform == 'win32':
                    subprocess.run(['taskkill', '/F', '/PID', pid], check=True, capture_output=True)
                else:
                    subprocess.run(['kill', pid], check=True, capture_output=True)
                print(f"进程 {pid} 已被终止。")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        return False

    def _start_server(self, invoker_path, scan_dir):
        if self.client_only:
            if not self._verify_service():
                raise ConnectionError(f"在 client_only 模式下，无法连接到{self.url_base} 上的服务。")
            return

        if self._is_port_in_use():
            if self._verify_service():
                if self.client_only:
                    return
            else:
                self._find_and_kill_process_on_port(self.port)
                time.sleep(1)



        if not os.path.exists(invoker_path):
            raise FileNotFoundError(f"Invoker file not found: {invoker_path}")

        command = ['node', invoker_path]
        if scan_dir:
            command.append(scan_dir)
        command.append(str(self.port))

        project_root = os.getcwd()
        env = os.environ.copy()
        node_modules_path = os.path.join(project_root, 'node_modules')

        if 'NODE_PATH' in env:
            env['NODE_PATH'] = f"{node_modules_path}{os.pathsep}{env['NODE_PATH']}"
        else:
            env['NODE_PATH'] = node_modules_path

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
            if self.logger is None:
                self.logger = Logger(True)
            stdout_thread = threading.Thread(
                target=self._stream_printer,
                args=(self.process.stdout, sys.stdout)  # 将子进程stdout打印到sys.stdout
            )
            stdout_thread.daemon = True
            stdout_thread.start()

            stderr_thread = threading.Thread(
                target=self._stream_printer,
                args=(self.process.stderr, sys.stderr)  # 将子进程stderr打印到sys.stderr
            )
            stderr_thread.daemon = True
            stderr_thread.start()

        atexit.register(self.shutdown)
        print("Node.js Service process has been started.")

    def invoke(self, file_name, func_name, *args, **kwargs):
        payload = {
            'func_name': func_name,
            'args': list(args)
        }
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
            print(f"Could not connect to Node.js service: {e}", file=sys.stderr)
            if self.process:
                self.shutdown()
            raise ConnectionError(f"Could not connect to Node.js service: {e}")

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
                input()
        except KeyboardInterrupt:
            print("Received exit signal, shutting down service.")
            self.shutdown()
