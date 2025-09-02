import os
import functools
import execjs
import inspect

def execJS(js_file_path: str, js_function_name: str = None):
    """
    一个装饰器工厂，用于将 Python 函数调用代理到指定的 JavaScript 函数。
    现在支持关键字参数和位置参数的混合调用。
    """
    def decorator(py_func):
        # 提前获取Python函数的签名
        try:
            py_func_signature = inspect.signature(py_func)
        except ValueError:
            # 对于某些内置函数等可能无法获取签名，进行回退
            py_func_signature = None

        @functools.wraps(py_func)
        def wrapper(*args, **kwargs):
            """
            实际的包装器，负责读取、编译和执行 JavaScript 代码。
            """
            # 1. 确定最终要调用的 JavaScript 函数名
            target_js_func = js_function_name if js_function_name is not None else py_func.__name__

            # 2. 准备传递给 JavaScript 的参数列表
            final_args = []
            if py_func_signature:
                try:
                    # 智能地将 *args 和 **kwargs 绑定到函数签名上
                    bound_args = py_func_signature.bind(*args, **kwargs)
                    bound_args.apply_defaults() # 应用函数定义中的默认值
                    # 按签名顺序提取参数值
                    final_args = list(bound_args.arguments.values())
                except TypeError as e:
                    print(f"错误: 调用 '{py_func.__name__}' 时参数不匹配: {e}")
                    raise
            else:
                # 如果无法获取签名，则只传递位置参数
                if kwargs:
                    print(f"警告: 无法获取 '{py_func.__name__}' 的函数签名，关键字参数将被忽略。")
                final_args = list(args)


            try:
                # 3. 获取 Node.js (或其他可用) 的执行环境
                node = execjs.get()
            except execjs.RuntimeUnavailableError as e:
                print(f"错误: 未找到可用的 JavaScript 运行时 (如 Node.js)。请确保已安装。")
                raise e

            try:
                # 4. 读取并编译 JavaScript 文件
                with open(js_file_path, "r", encoding="utf-8") as f:
                    js_code = f.read()
                ctx = node.compile(js_code)
            except FileNotFoundError:
                print(f"错误: JavaScript 文件未找到: '{js_file_path}'")
                raise
            except Exception as e:
                print(f"编译 JavaScript 文件 '{js_file_path}' 时出错: {e}")
                raise

            try:
                result = ctx.call(target_js_func, *final_args)
                return result
            except Exception as e:
                print(f"执行 JavaScript 函数 '{target_js_func}' 时出错: {e}")
                raise

        return wrapper
    return decorator

