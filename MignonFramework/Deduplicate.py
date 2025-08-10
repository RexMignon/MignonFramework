"""
去重方法 deduplicate_file(input_filepath: str, output_filepath: str)
  Args:
        input_filepath (str): 输入文件的路径。
        output_filepath (str): 输出文件的路径（去重后的内容将写入此文件）。
"""
import os
import sys
import json

def deduplicate_file(input_filepath: str, output_filepath: str):
    """
    对大文件进行去重，移除重复行和空行，并显示处理进度。

    Args:
        input_filepath (str): 输入文件的路径。
        output_filepath (str): 输出文件的路径（去重后的内容将写入此文件）。
    """
    seen_lines = set()
    processed_lines_count = 0
    unique_lines_count = 0

    try:
        # 获取当前脚本所在的目录
        # 这确保了即使函数被导入并在其他地方调用，也能正确找到相对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # 如果输入文件路径是相对路径，则将其转换为相对于脚本目录的绝对路径
        # 注意：这里假设用户传入的 input_filepath 可能是相对路径
        # 如果你期望用户总是传入完整绝对路径，则不需要这部分处理
        if not os.path.isabs(input_filepath):
            input_filepath = os.path.join(script_dir, input_filepath)

        if not os.path.isabs(output_filepath):
            output_filepath = os.path.join(script_dir, output_filepath)

        # 获取文件大小，用于估算进度
        total_size = os.path.getsize(input_filepath)
        processed_size = 0

        with open(input_filepath, 'r', encoding='utf-8') as infile, \
                open(output_filepath, 'w', encoding='utf-8') as outfile:

            print(f"开始处理文件: '{input_filepath}'")
            print(f"去重结果将写入: '{output_filepath}'")

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


def read_and_write_lines(line_count, input_file, output_file):
    """
    从 input_file 中读取前 line_count 行，写入到 output_file。

    :param line_count: 要读取的行数（int）
    :param input_file: 输入文件路径（str）
    :param output_file: 输出文件路径（str）
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as infile:
            lines = []
            for _ in range(line_count):
                line = infile.readline()
                if not line:
                    break
                lines.append(line)

        with open(output_file, 'w', encoding='utf-8') as outfile:
            outfile.writelines(lines)

        print(f"成功写入 {len(lines)} 行到 {output_file}")

    except FileNotFoundError:
        print(f"错误：找不到文件 {input_file}")
    except Exception as e:
        print(f"发生异常：{e}")
