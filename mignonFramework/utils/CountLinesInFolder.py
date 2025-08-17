"""
统计文件夹中每个文件的行数  count_lines_in_files(folder_path)
统计单个文件的行数 count_lines_in_single_file(file_path)
"""
import os
import re
from typing import Optional

def _count_file_lines(file_path: str) -> Optional[int]:
    """
    一个内部辅助函数，用于统计单个文件的行数。
    如果文件无法读取，返回 None。
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception as e:
        print(f"警告：无法读取文件 '{os.path.basename(file_path)}' - {e}")
        return None

def count_lines_in_files(folder_path: str, prefix: str = '', suffix: str = '', pattern: str = ''):
    """
    统计指定文件夹内符合条件的所有文件的行数。

    Args:
        folder_path (str): 目标文件夹的路径。
        prefix (str): 可选。只统计文件名以该前缀开始的文件。
        suffix (str): 可选。只统计文件名以该后缀结尾的文件。
        pattern (str): 可选。只统计文件名符合该正则表达式的文件。
    """
    if not os.path.isdir(folder_path):
        print(f"错误：'{folder_path}' 不是一个有效的文件夹路径。")
        return

    print(f"正在统计文件夹 '{folder_path}' 中文件的行数...\n")
    total_lines = 0
    file_count = 0

    # 编译正则表达式，以提高性能
    if pattern:
        try:
            regex = re.compile(pattern)
        except re.error as e:
            print(f"错误：无效的正则表达式 '{pattern}' - {e}")
            return
    else:
        regex = None

    for filename in os.listdir(folder_path):
        # 构建完整的文件路径
        filepath = os.path.join(folder_path, filename)

        # 检查是否是文件
        if not os.path.isfile(filepath):
            continue

        # 按前缀、后缀和正则表达式进行过滤
        if prefix and not filename.startswith(prefix):
            continue
        if suffix and not filename.endswith(suffix):
            continue
        if regex and not regex.search(filename):
            continue

        line_count = _count_file_lines(filepath)
        if line_count is not None:
            file_count += 1
            total_lines += line_count
            print(f"文件：'{filename}'，行数：{line_count}")

    if file_count == 0:
        print("该文件夹中没有找到任何符合条件的文件。")
    else:
        print(f"\n统计完成。共处理了 {file_count} 个文件。总行数：{total_lines}")
        return total_lines


def count_lines_in_single_file(file_path: str):
    """
    统计指定文件的行数，并输出文件名和对应的行数。

    Args:
        file_path (str): 目标文件的路径。
    """
    if not os.path.isfile(file_path):
        print(f"错误：'{file_path}' 不是一个有效的文件路径。")
        return None

    line_count = _count_file_lines(file_path)
    if line_count is not None:
        filename = os.path.basename(file_path)
        print(f"文件：'{filename}' 的总行数为：{line_count}")
        return line_count





def count_lines_in_directory(path, ignore_dirs=None, ignore_exts=None):
    """
    递归统计指定文件夹下所有文件的总行数。

    Args:
        path (str): 要统计的目录路径。
        ignore_dirs (list): 需要忽略的目录名称列表。
        ignore_exts (list): 需要忽略的文件扩展名列表。

    Returns:
        int: 总行数。
    """
    if ignore_dirs is None:
        ignore_dirs = ['.git', '__pycache__', '.idea', 'venv', 'node_modules']
    if ignore_exts is None:
        ignore_exts = ['.pyc', '.class', '.dll', '.so', '.exe', '.zip', '.gz', '.tar', '.rar', '.7z', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.mp4', '.mkv', '.avi', '.mp3', '.wav', '.flac']

    total_lines = 0
    file_count = 0

    print(f"开始统计目录: {path}")

    for root, dirs, files in os.walk(path):
        # 移除需要忽略的目录
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        for file_name in files:
            # 跳过需要忽略的文件扩展名
            if any(file_name.endswith(ext) for ext in ignore_exts):
                continue

            file_path = os.path.join(root, file_name)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    total_lines += len(lines)
                    file_count += 1
            except UnicodeDecodeError:
                # 忽略无法用 UTF-8 解码的二进制文件
                print(f"已跳过二进制文件或编码错误的文件: {file_path}")
            except Exception as e:
                print(f"处理文件 {file_path} 时发生错误: {e}")

    return total_lines, file_count




# 示例用法
if __name__ == '__main__':
    # 假设有一个名为 'test_folder' 的文件夹，里面有一些文件
    # os.makedirs('test_folder', exist_ok=True)
    # with open('test_folder/file1.py', 'w') as f: f.write('a\nb\nc')
    # with open('test_folder/file2.txt', 'w') as f: f.write('d\ne')
    # with open('test_folder/test_file.py', 'w') as f: f.write('f\ng\nh\ni')

    # 1. 统计文件夹中所有文件的行数
    print("--- 统计所有文件 ---")
    count_lines_in_files('../')

    print("\n--- 统计单个文件 ---")
    count_lines_in_single_file('test.py')

    # 2. 统计文件夹中所有以 '.py' 结尾的文件行数
    print("\n--- 统计所有 .py 文件 ---")
    count_lines_in_files('../', suffix='.py')

    # 3. 统计文件夹中所有以 'file' 开头的文件行数
    print("\n--- 统计所有以 'file' 开头的文件 ---")
    count_lines_in_files('../', prefix='file')

    # 4. 统计文件名中包含数字的文件行数 (使用正则表达式)
    print("\n--- 统计文件名中包含数字的文件 ---")
    count_lines_in_files('../', pattern=r'\d')
