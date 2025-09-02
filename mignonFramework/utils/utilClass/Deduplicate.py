import os
import sys
import json
from itertools import islice

def deduplicate_file(input_filepath: str, output_filepath: str):
    """
    对大文件进行去重，移除重复行和空行，并显示处理进度。
    相对路径将从当前工作目录解析。

    Args:
        input_filepath (str): 输入文件的路径。
        output_filepath (str): 输出文件的路径（去重后的内容将写入此文件）。
    """
    seen_lines = set()
    processed_lines_count = 0
    unique_lines_count = 0

    try:
        total_size = os.path.getsize(input_filepath)
        processed_size = 0

        with open(input_filepath, 'r', encoding='utf-8') as infile, \
                open(output_filepath, 'w', encoding='utf-8') as outfile:

            print(f"开始处理文件: '{os.path.abspath(input_filepath)}'")
            print(f"去重结果将写入: '{os.path.abspath(output_filepath)}'")

            for line in infile:
                processed_lines_count += 1
                processed_size += len(line.encode('utf-8'))
                stripped_line = line.strip()

                if not stripped_line:
                    continue

                if stripped_line not in seen_lines:
                    seen_lines.add(stripped_line)
                    outfile.write(line)
                    unique_lines_count += 1

                progress_percentage = (processed_size / total_size) * 100 if total_size > 0 else 0
                sys.stdout.write(
                    f"\r处理进度: {processed_lines_count} 行已处理 | "
                    f"发现唯一行: {unique_lines_count} 条 | "
                    f"文件读取: {progress_percentage:.2f}%"
                )
                sys.stdout.flush()

        print(f"\n文件处理完成！")
        print(f"总共处理行数: {processed_lines_count}")
        print(f"去重后唯一行数: {unique_lines_count}")

    except FileNotFoundError:
        print(f"错误: 输入文件 '{input_filepath}' 未找到。", file=sys.stderr)
    except Exception as e:
        print(f"处理文件时发生错误: {e}", file=sys.stderr)
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
            print(f"已删除部分写入的输出文件: '{output_filepath}'", file=sys.stderr)


def read_and_write_lines(line_count: int, input_file: str, output_file: str):
    """
    从 input_file 中读取前 line_count 行，写入到 output_file。
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as infile:
            lines = [next(infile) for _ in range(line_count)]
        with open(output_file, 'w', encoding='utf-8') as outfile:
            outfile.writelines(lines)
        print(f"成功写入 {len(lines)} 行到 {output_file}")
    except FileNotFoundError:
        print(f"错误：找不到文件 {input_file}")
    except StopIteration:
        print(f"文件行数少于 {line_count} 行，已读取所有行。")
    except Exception as e:
        print(f"发生异常：{e}")


# --- 新增功能 1 ---
def copy_line_by_number(source_filepath: str, target_filepath: str, line_number: int):
    """
    从源文件中读取指定行号的行，并将其写入目标文件。

    Args:
        source_filepath (str): 源文件的路径。
        target_filepath (str): 目标文件的路径。
        line_number (int): 要读取的行号 (从1开始)。
    """
    if line_number < 1:
        print("错误: 行号必须是正整数。", file=sys.stderr)
        return

    try:
        with open(source_filepath, 'r', encoding='utf-8') as infile:
            # 使用 islice 高效地跳转到指定行，避免读取整个文件
            # line_number - 1 是因为 islice 是0-based索引
            line_to_copy = next(islice(infile, line_number - 1, line_number), None)

        if line_to_copy is None:
            print(f"错误: 源文件 '{source_filepath}' 的行数少于 {line_number} 行。", file=sys.stderr)
            return

        with open(target_filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(line_to_copy)

        print(f"成功将文件 '{source_filepath}' 的第 {line_number} 行复制到 '{target_filepath}'")

    except FileNotFoundError:
        print(f"错误: 源文件 '{source_filepath}' 未找到。", file=sys.stderr)
    except Exception as e:
        print(f"处理文件时发生错误: {e}", file=sys.stderr)


# --- 新增功能 2 ---
def replace_line_with_file_content(target_filepath: str, line_to_replace: int, source_filepath: str):
    """
    将源文件的全部内容压缩为一行，并用它替换目标文件中的指定行。

    Args:
        target_filepath (str): 要修改的目标文件的路径。
        line_to_replace (int): 目标文件中要被替换的行号 (从1开始)。
        source_filepath (str): 提供替换内容的源文件的路径。
    """
    if line_to_replace < 1:
        print("错误: 行号必须是正整数。", file=sys.stderr)
        return

    try:
        # 1. 读取源文件的全部内容并压缩为一行
        with open(source_filepath, 'r', encoding='utf-8') as source_file:
            replacement_content = source_file.read().replace('\n', ' ').replace('\r', '').strip()

        # 2. 读取目标文件的所有行到内存
        with open(target_filepath, 'r', encoding='utf-8') as target_file:
            lines = target_file.readlines()

        # 3. 检查行号是否有效并执行替换
        if line_to_replace > len(lines):
            print(f"错误: 目标文件 '{target_filepath}' 的行数少于 {line_to_replace} 行。", file=sys.stderr)
            return

        # 替换指定行 (注意列表索引是0-based)
        # 确保新行以换行符结尾，以保持文件结构
        lines[line_to_replace - 1] = replacement_content + '\n'

        # 4. 将修改后的内容写回目标文件
        with open(target_filepath, 'w', encoding='utf-8') as target_file:
            target_file.writelines(lines)

        print(f"成功将文件 '{target_filepath}' 的第 {line_to_replace} 行替换为 '{source_filepath}' 的内容。")

    except FileNotFoundError as e:
        print(f"错误: 文件未找到 - {e.filename}", file=sys.stderr)
    except Exception as e:
        print(f"处理文件时发生错误: {e}", file=sys.stderr)

