
from abc import ABC, abstractmethod
from typing import List


class BaseStateTracker(ABC):
    """
    状态追踪器的抽象基类。

    定义了所有状态管理策略（如SQLite、文件移动等）必须实现的接口，
    从而将状态管理与核心文件处理逻辑解耦。
    """

    @abstractmethod
    def initialize(self):
        """
        初始化追踪器，例如创建数据库表或目录。
        """
        pass

    @abstractmethod
    def get_unprocessed_files(self, all_input_files: List[str]) -> List[str]:
        """
        根据已记录的状态，从提供的文件列表中筛选出需要处理的文件。

        Args:
            all_input_files (List[str]): 输入目录中当前存在的所有文件的完整路径列表。

        Returns:
            List[str]: 需要进行处理的文件路径列表。
        """
        pass

    @abstractmethod
    def mark_as_finished(self, file_path: str):
        """
        将指定文件标记为“已成功处理”。

        Args:
            file_path (str): 已成功处理的文件的路径。
        """
        pass

    @abstractmethod
    def mark_as_exception(self, file_path: str, error_message: str):
        """
        将指定文件标记为“处理异常”。

        Args:
            file_path (str): 处理失败的文件的路径。
            error_message (str): 具体的错误信息。
        """
        pass

    @abstractmethod
    def close(self):
        """
        关闭并释放所有资源，如数据库连接。
        """
        pass

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()