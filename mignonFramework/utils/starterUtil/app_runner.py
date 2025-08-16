import os
from flask import Flask
from .views import bp as starter_bp # 导入 views 模块中定义的 Blueprint 实例

# 获取当前文件所在的目录的绝对路径
_current_dir = os.path.dirname(os.path.abspath(__file__))

class StarterAppRunner:
    """
    负责创建、配置并运行 MignonFramework Starter 的 Flask Web 应用。
    """
    def __init__(self):
        # 使用绝对路径来定义模板和静态文件夹，确保万无一失
        template_folder = os.path.join(_current_dir, 'templates')
        static_folder = os.path.join(_current_dir, 'static')

        self.app = Flask(
            __name__,
            template_folder=template_folder,
            static_folder=static_folder
        )
        self.app.register_blueprint(starter_bp) # 注册 Blueprint，而不是调用 register_routes 函数

    def run(self, host='127.0.0.1', port=5001):
        """启动Flask服务器"""
        print(f" * MignonFramework Starter [Patched] 已启动，请访问 http://{host}:{port}")
        self.app.run(host=host, port=port, debug=False)