import subprocess
import requests
import atexit
import time
import os
import socket
import sys
from functools import wraps


class MicroServiceByNodeJS:
    def __init__(self, client_only=False, port=3000, url_base="127.0.0.1", scan_dir="./resources/js",
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
        self._start_server(invoker_path, scan_dir)

    def _is_port_in_use(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', self.port)) == 0

    def _verify_service(self):
        try:
            response = requests.get(f'{self.url_base}/status', timeout=2)
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
                    subprocess.run(['taskkill', '/F', '/PID', pid], check=True)
                else:
                    subprocess.run(['kill', pid], check=True)
                print(f"进程 {pid} 已被终止。")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        return False

    def _start_server(self, invoker_path, scan_dir):
        if self._is_port_in_use():
            if self._verify_service():

                if self.client_only:
                    return
            else:
                if self.client_only:
                    raise ConnectionError(f"在 client_only 模式下，端口 {self.port} 被占用且无法连接到我们的服务。")
                else:
                    self._find_and_kill_process_on_port(self.port)
                    time.sleep(1)

        if self.client_only:
            if not self._is_port_in_use() or not self._verify_service():
                raise ConnectionError(f"在 client_only 模式下，无法连接到{self.url_base} 上的服务。")
            return

        if not os.path.exists(invoker_path):
            raise FileNotFoundError(f"Invoker file not found: {invoker_path}")

        command = ['node', invoker_path]
        if scan_dir:
            command.append(scan_dir)
        command.append(str(self.port))

        project_root = os.getcwd()
        env = os.environ.copy()
        project_root = os.getcwd()
        node_modules_path = os.path.join(project_root, 'node_modules')

        if 'NODE_PATH' in env:
            env['NODE_PATH'] = f"{node_modules_path}{os.pathsep}{env['NODE_PATH']}"
        else:
            env['NODE_PATH'] = node_modules_path
        if self.js_log:

            self.process = subprocess.Popen(
                command,
                cwd = project_root,
                env = env,
                shell=False
            )
        else:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                shell=False
            )
        atexit.register(self.shutdown)
        print("Node.js Service started.")

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
                raise RuntimeError(f"JS execution failed: {result.get('error', '未知错误')}")
        except requests.exceptions.RequestException as e:
            if self.process:
                self.shutdown()
            raise ConnectionError(f"Could not connect to Node.js service: {e}")

    def shutdown(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
            print("Node.js service shut down.")
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
        while True:
            input()


