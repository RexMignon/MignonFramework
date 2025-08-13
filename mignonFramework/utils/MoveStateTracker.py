import os
import shutil
import asyncio
from typing import List
from mignonFramework.utils.BaseStateTracker import BaseStateTracker

class MoveStateTracker(BaseStateTracker):
    """
    使用移动文件的方式来跟踪处理状态的具体实现。
    """
    def __init__(self, finish_dir: str, exception_dir: str):
        self.finish_dir = finish_dir
        self.exception_dir = exception_dir

    def initialize(self):
        """创建 'finish' 和 'exception' 目录。"""
        os.makedirs(self.finish_dir, exist_ok=True)
        os.makedirs(self.exception_dir, exist_ok=True)

    def get_unprocessed_files(self, all_input_files: List[str]) -> List[str]:
        """在移动模式下，输入目录中的所有文件都视为待处理。"""
        return all_input_files

    async def _move_file_async(self, src: str, dst_dir: str):
        """异步移动文件。"""
        if not os.path.exists(src):
            return # 如果文件已被另一个进程移动，则忽略
        dst = os.path.join(dst_dir, os.path.basename(src))
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, shutil.move, src, dst)
        except Exception as e:
            print(f"\n[警告] 异步移动文件失败: 从 {src} 到 {dst} - {e}")

    async def mark_as_finished(self, file_path: str):
        """将文件移动到 'finish' 目录。"""
        await self._move_file_async(file_path, self.finish_dir)

    async def mark_as_exception(self, file_path: str, error_message: str):
        """将文件移动到 'exception' 目录。"""
        # error_message 在此模式下不使用，但为了遵循接口而保留
        await self._move_file_async(file_path, self.exception_dir)

    def close(self):
        """此模式下无需关闭任何资源。"""
        pass