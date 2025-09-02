from abc import ABC, abstractmethod
from typing import List, Iterator, Tuple, Dict, Any
import os
from mignonFramework.utils.utilClass.CountLinesInFolder import count_lines_in_single_file


class BaseReader(ABC):
    """
    数据读取器的抽象基类。
    所有自定义读取器（如CsvReader, XmlReader等）都应继承此类。
    """

    def __init__(self, path: str):
        """
        初始化读取器。

        Args:
            path (str): 要读取的文件路径或目录路径。
        """
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"提供的路径无效或不存在: {path}")
        self.path = path
        self.files_to_process = self._discover_files()
        if not self.files_to_process:
            print(f"[WARNING] 在路径 '{self.path}' 中未找到可处理的文件。")

    @abstractmethod
    def _discover_files(self) -> List[str]:
        """
        根据初始路径发现所有需要处理的文件。
        应由子类实现，以定义何种文件是“可处理的”。

        Returns:
            List[str]: 包含所有待处理文件完整路径的列表。
        """
        pass

    def get_files(self) -> List[str]:
        """
        获取待处理的文件列表。

        Returns:
            List[str]: 文件路径列表。
        """
        return self.files_to_process

    @abstractmethod
    def read_file(self, file_path: str, start_line: int = 1) -> Iterator[Tuple[Dict[str, Any], int]]:
        """
        逐行读取单个文件并解析内容。

        Args:
            file_path (str): 要读取的文件的完整路径。
            start_line (int): 从指定的行号开始读取。

        Yields:
            Iterator[Tuple[Dict[str, Any], int]]: 一个迭代器，每次产出一个元组，
                                                  包含解析后的数据字典和对应的行号。
        """
        pass

    def get_total_items(self, file_path: str) -> int:
        """
        获取单个文件中的总项目数（例如，总行数）。
        子类可以重写此方法以提供更精确的计数方式。

        Args:
            file_path (str): 文件的完整路径。

        Returns:
            int: 文件中的总项目数。
        """
        return count_lines_in_single_file(file_path) or 0

    @abstractmethod
    def get_samples(self, sample_size: int) -> List[Dict[str, Any]]:
        """
        从一个或多个文件中随机抽取指定数量的样本。

        Args:
            sample_size (int): 要抽取的样本数量。

        Returns:
            List[Dict[str, Any]]: 包含样本数据的字典列表。
        """
        pass