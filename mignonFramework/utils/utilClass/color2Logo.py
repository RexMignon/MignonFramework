import math
import os

def colorize_logo(art_string: str):
    """
    使用125度斜线将ASCII Art标志分割为两种颜色。

    参数:
        art_string (str): 包含ASCII Art的多行字符串。

    返回:
        str: 带有ANSI颜色代码的彩色字符串。
    """
    # 检查是否在不支持ANSI的终端（如Windows CMD）中运行，并尝试启用
    if os.name == 'nt':
        os.system('')

    # ANSI 颜色代码
    # \033[93m 是明黄色
    # \033[95m 是亮洋红色 (在终端中通常显示为淡紫色)
    # \033[0m  是重置所有颜色和样式
    BRIGHT_YELLOW = "\033[93m"
    LIGHT_PURPLE = "\033[95m"
    RESET = "\033[0m"

    lines = art_string.split('\n')
    if not lines:
        return ""

    height = len(lines)
    # 计算整个ASCII艺术字的最宽宽度
    width = max(len(line) for line in lines)

    # 找到几何中心点
    center_x = width / 3.0
    center_y = height / 2.0

    # 将125度角转换为弧度以便计算
    angle_rad = math.radians(125)
    # 计算该角度下的斜率
    slope = math.tan(angle_rad)

    output_lines = []
    # 逐行处理
    for y, line in enumerate(lines):
        colored_line = ""
        current_color = None

        # 逐个字符处理
        for x, char in enumerate(line):
            # 如果是空格，则不进行着色，保持透明背景
            if char.isspace():
                if current_color is not None:
                    # 如果前面有颜色，则重置，避免颜色"泄露"到空白区域
                    colored_line += RESET
                    current_color = None
                colored_line += char
                continue

            # 核心逻辑：判断当前点(x, y)在斜线的哪一侧
            # 我们使用直线方程的点斜式: y - y_center = slope * (x - x_center)
            # 变形为: (y - center_y) - slope * (x - center_x) = 0
            # 这个公式的结果的正负值可以判断点在直线的哪一侧
            decision_value = (y - center_y) - slope * (x - center_x)

            # 根据正负值决定目标颜色
            # - tan(125)是负数，经过计算，小于等于0的区域对应左上部分（前一半）
            target_color_code = BRIGHT_YELLOW if decision_value <= 0 else LIGHT_PURPLE

            # 优化：只有在颜色需要改变时才插入ANSI代码
            if current_color != target_color_code:
                colored_line += target_color_code
                current_color = target_color_code

            colored_line += char

        # 在每行末尾重置颜色，确保不会影响到后续的输出
        if current_color is not None:
            colored_line += RESET

        output_lines.append(colored_line)

    return "\n".join(output_lines)
