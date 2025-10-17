import multiprocessing
import threading

class RunOnce:
    """
    一个确保函数只在“执行实例”的主进程中运行一次的工具类。
    它能区分独立的Python脚本和由主脚本创建的子进程。
    """
    _lock = threading.Lock()
    _has_run = False

    @classmethod
    def execute(cls, func, *args, **kwargs):
        """
        执行一个函数，确保它只在主进程中被执行一次。
        所有通过 multiprocessing.Process 创建的子进程都不会执行此函数。
        """
        if multiprocessing.parent_process() is not None:
            return

        with cls._lock:
            if not cls._has_run:
                func(*args, **kwargs)
                cls._has_run = True