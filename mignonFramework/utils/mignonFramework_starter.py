# mignonFramework_starter.py

# 将导入从 ui_app 改为 app_runner
from mignonFramework.utils.starterUtil.app_runner import StarterAppRunner

def start(port: int = 5001):
    """
    MignonFramework 启动器的主入口点。
    """
    try:
        app = StarterAppRunner(port)
        app.run()
    except ImportError as e:
        print(f"\n[错误] 无法启动 Starter 应用: {e}")
        print("请确保 Flask 已安装: pip install Flask")
    except Exception as e:
        print(f"\n[致命错误] 启动器启动失败: {e}")

if __name__ == '__main__':
    start()