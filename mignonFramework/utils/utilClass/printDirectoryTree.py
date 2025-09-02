import os

def print_directory_tree(path, indent=0):
    """
    递归地打印目录及子目录下的文件和文件夹，形成树状结构。

    Args:
        path (str): 要遍历的起始路径。
        indent (int): 缩进级别，用于控制树状结构显示。
    """
    # 确保路径存在
    if not os.path.exists(path):
        print(f"错误: 路径 '{path}' 不存在。")
        return

    # 获取当前目录下的所有文件和文件夹
    items = sorted(os.listdir(path))
    num_items = len(items)

    for i, item in enumerate(items):
        item_path = os.path.join(path, item)
        is_last = (i == num_items - 1)

        # 打印当前项的缩进和前缀
        prefix = '    ' * indent + ('└── ' if is_last else '├── ')
        print(prefix + item)

        # 如果是目录，则递归调用自身
        if os.path.isdir(item_path):
            # 新的缩进级别
            new_indent = indent + 1
            # 递归调用时，如果不是最后一项，需要额外打印一个竖线
            new_prefix = '│   ' if not is_last else '    '
            print_directory_tree(item_path, new_indent)
