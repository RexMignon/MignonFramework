import inspect
import json
from functools import wraps
from typing import List, Optional, Callable, Any

try:
    from flask import request as flask_request, jsonify as flask_jsonify
except ImportError:
    flask_request, flask_jsonify = None, None

try:
    from quart import request as quart_request, jsonify as quart_jsonify
except ImportError:
    quart_request, quart_jsonify = None, None

try:
    from django.http import JsonResponse, HttpRequest
except ImportError:
    JsonResponse, HttpRequest = None, None


class Stamp:
    """
    一个用于标识当前使用的Web框架的类。
    """
    FLASK = "Flask"
    QUART = "Quart"
    DJANGO = "Django"


# --- 全局框架配置 ---

_current_stamp: Optional[str] = None


def set_framework(stamp: str) -> None:
    """
    设置全局Web框架。此函数应在应用启动时调用一次。

    :param stamp: 使用的框架 (Stamp.FLASK, Stamp.QUART, 或 Stamp.DJANGO)。
    """
    global _current_stamp
    if stamp not in [Stamp.FLASK, Stamp.QUART, Stamp.DJANGO]:
        raise ValueError(f"不支持的框架标识: {stamp}")
    _current_stamp = stamp


def _get_request_obj(stamp: str, *args) -> Any:
    """一个辅助函数，用于根据框架获取请求对象。"""
    if stamp == Stamp.FLASK:
        if not flask_request:
            raise ImportError("Flask 未安装，但被选为当前框架。")
        return flask_request
    if stamp == Stamp.QUART:
        if not quart_request:
            raise ImportError("Quart 未安装，但被选-选为当前框架。")
        return quart_request
    if stamp == Stamp.DJANGO:
        if not HttpRequest:
            raise ImportError("Django 未安装，但被选为当前框架。")
        # 在 Django 中，请求对象是视图的第一个位置参数。
        if args and isinstance(args[0], HttpRequest):
            return args[0]
        # 在类视图中，第二个参数可能是 request
        if len(args) > 1 and isinstance(args[1], HttpRequest):
            return args[1]
        raise TypeError("Django 视图函数或方法缺少 'request' 参数。")
    raise ValueError(f"不支持的框架标识: {stamp}")


def _make_json_error(message: str, status_code: int, stamp: str) -> Any:
    """一个辅助函数，用于创建特定于框架的JSON错误响应。"""
    payload = {"status": False, "data": message}
    if stamp in [Stamp.FLASK, Stamp.QUART]:
        jsonify_func = flask_jsonify if stamp == Stamp.FLASK else quart_jsonify
        if not jsonify_func:
            # 这种情况发生在框架未安装时
            raise ImportError(f"{stamp} 未安装，无法创建JSON响应。")
        return jsonify_func(payload), status_code
    if stamp == Stamp.DJANGO:
        if not JsonResponse:
            raise ImportError("Django 未安装，无法创建 JsonResponse。")
        return JsonResponse(payload, status=status_code)
    # 未知框架的回退
    return json.dumps(payload), status_code, {'Content-Type': 'application/json'}


def _resolve_stamp(stamp: Optional[str]) -> str:
    """解析要使用的最终框架标识。"""
    final_stamp = stamp if stamp is not None else _current_stamp
    if final_stamp is None:
        raise RuntimeError(
            "框架标识未配置。请在应用启动时调用 set_framework() "
            "或将 'stamp' 参数传递给装饰器。"
        )
    return final_stamp


def RequestParams(stamp: Optional[str] = None, exclude: Optional[List[str]] = None) -> Callable:
    """
    一个通用的装饰器工厂，用于从GET请求的查询参数中
    自动提取数据并注入到视图函数的参数中。

    用法:
    # 在应用启动时:
    # set_framework(Stamp.FLASK)
    #
    # 在视图中:
    # @RequestParams(exclude=['user_id'])
    # def my_view(name, age):
    #     ...

    :param stamp: 使用的框架。如果为 None，则使用全局设置。
    :param exclude: 一个字符串列表，包含不应从请求中注入的参数名。
    """
    if exclude is None:
        exclude = []

    def decorator(func: Callable) -> Callable:
        final_stamp = _resolve_stamp(stamp)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                req = _get_request_obj(final_stamp, *args)
            except (ImportError, TypeError, ValueError) as e:
                return _make_json_error(str(e), 500, final_stamp)

            request_data = {}
            if final_stamp in [Stamp.FLASK, Stamp.QUART]:
                request_data = req.args
            elif final_stamp == Stamp.DJANGO:
                request_data = req.GET

            sig = inspect.signature(func)
            final_kwargs = kwargs.copy()

            for param in sig.parameters.values():
                if param.name in final_kwargs or param.name in exclude:
                    continue
                if param.name in request_data:
                    final_kwargs[param.name] = request_data.get(param.name)
                else:
                    final_kwargs[param.name] = None
            if inspect.iscoroutinefunction(func):
                return await func(*args, **final_kwargs)
            else:
                return func(*args, **final_kwargs)

        return wrapper
    return decorator


def RequestBody(stamp: Optional[str] = None, exclude: Optional[List[str]] = None) -> Callable:
    """
    一个通用的装饰器工厂，用于从POST/PUT等请求的JSON体中
    自动提取数据并注入到视图函数的参数中。

    用法:
    # 在应用启动时:
    # set_framework(Stamp.DJANGO)
    #
    # 在视图中:
    # @RequestBody(exclude=['role'])
    # def create_user(request, user_name, email):
    #     ...

    :param stamp: 使用的框架。如果为 None，则使用全局设置。
    :param exclude: 一个字符串列表，包含不应从JSON体中注入的参数名。
    """
    if exclude is None:
        exclude = []

    def decorator(func: Callable) -> Callable:
        final_stamp = _resolve_stamp(stamp)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                req = _get_request_obj(final_stamp, *args)
            except (ImportError, TypeError, ValueError) as e:
                return _make_json_error(str(e), 500, final_stamp)

            request_data = None
            content_type_valid = False

            try:
                if final_stamp in [Stamp.FLASK, Stamp.QUART]:
                    content_type_valid = req.is_json
                    if content_type_valid:
                        request_data = await req.get_json(silent=True) if final_stamp == Stamp.QUART else req.get_json(silent=True)
                elif final_stamp == Stamp.DJANGO:
                    if 'application/json' in req.content_type:
                        content_type_valid = True
                        if req.body:
                            request_data = json.loads(req.body)
                        else:
                            request_data = {}
            except Exception:
                request_data = None

            if not content_type_valid:
                return _make_json_error("请求头 'Content-Type' 必须是 'application/json'", 415, final_stamp)
            if request_data is None:
                return _make_json_error("请求体中不是一个有效的JSON或解析失败", 400, final_stamp)

            sig = inspect.signature(func)
            final_kwargs = kwargs.copy()
            missing_params = []

            for param in sig.parameters.values():
                param_name = param.name
                if param_name in final_kwargs or param_name in ['self', 'cls', 'request'] or param_name in exclude:
                    continue
                if param_name in request_data:
                    final_kwargs[param_name] = request_data[param_name]
                elif param.default is inspect.Parameter.empty:
                    missing_params.append(param_name)

            if missing_params:
                msg = f"请求体中缺少必需的参数: {', '.join(missing_params)}"
                return _make_json_error(msg, 400, final_stamp)

            if inspect.iscoroutinefunction(func):
                return await func(*args, **final_kwargs)
            else:
                return func(*args, **final_kwargs)

        return wrapper
    return decorator