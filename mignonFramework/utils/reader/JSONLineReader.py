from mignonFramework.utils.reader.BaseReader import  BaseReader
from typing import List, Iterator, Tuple, Dict, Any, Optional
import os
import json as std_json
import ast
import random

class JsonLineReader(BaseReader):
    """
    一个具体的Reader实现，用于读取逐行JSON格式的文件（.json, .txt）。
    """

    def _discover_files(self) -> List[str]:
        """
        发现路径下所有以 .json 或 .txt 结尾的文件。
        """
        if os.path.isdir(self.path):
            return [os.path.join(self.path, f) for f in os.listdir(self.path)
                    if os.path.isfile(os.path.join(self.path, f)) and f.lower().endswith(('.json', '.txt'))]
        elif os.path.isfile(self.path):
            return [self.path]
        return []

    def _safe_json_load(self, text: str) -> Optional[Dict]:
        """
        安全地将字符串解析为JSON，支持标准JSON和Python字面量。
        """
        try:
            return std_json.loads(text)
        except std_json.JSONDecodeError:
            try:
                return ast.literal_eval(text)
            except (ValueError, SyntaxError, MemoryError, TypeError):
                return None

    def read_file(self, file_path: str, start_line: int = 1) -> Iterator[Tuple[Dict[str, Any], int]]:
        """
        从指定的JSON行文件中读取数据。
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line_num < start_line:
                    continue
                if not line.strip():
                    continue

                if json_data := self._safe_json_load(line):
                    yield json_data, line_num
                else:
                    # 可以在这里决定是跳过还是抛出异常
                    # 为了保持与原逻辑一致，我们在处理器层处理异常
                    raise ValueError("JSON 解析失败或为空")

    def get_samples(self, sample_size: int) -> List[Dict[str, Any]]:
        """
        从第一个可用的文件中随机抽取JSON行样本。
        """
        if not self.files_to_process:
            return []

        file_to_sample = self.files_to_process[0]
        samples = []
        try:
            total_lines = self.get_total_items(file_to_sample)
            if total_lines == 0:
                return []

            num_samples_to_take = min(sample_size, total_lines)
            if num_samples_to_take == 0:
                return []

            target_line_nums = sorted(random.sample(range(1, total_lines + 1), num_samples_to_take))

            current_line_num, target_index = 0, 0
            with open(file_to_sample, 'r', encoding='utf-8') as f:
                for line in f:
                    current_line_num += 1
                    if target_index >= len(target_line_nums):
                        break
                    if current_line_num == target_line_nums[target_index]:
                        target_index += 1
                        if not line.strip():
                            continue
                        if json_data := self._safe_json_load(line):
                            samples.append(json_data)
        except Exception as e:
            print(f"[WARNING] 从文件 '{os.path.basename(file_to_sample)}' 随机抽样时出错: {e}")

        return samples