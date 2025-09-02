import os
import json
import sys
import threading
from typing import Any, List, Type, TypeVar, Generic, get_origin, get_args, Callable, Dict

T = TypeVar('T')


class _ConfigObject:
    """
    一个代理类，将字典的键访问转换为属性访问。
    它递归地将嵌套的字典和列表也转换为代理对象。
    """
    def __init__(self, data: dict, save_callback: callable, template_cls: Type):
        # 使用 object.__setattr__ 来避免触发我们自定义的 __setattr__
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_save_callback", save_callback)
        object.__setattr__(self, "_template_cls", template_cls)
        object.__setattr__(self, "_annotations", getattr(template_cls, '__annotations__', {}))

    def _wrap(self, key: str, value: Any) -> Any:
        """根据类型提示包装返回值"""
        type_hint = self._annotations.get(key)

        if get_origin(type_hint) in (list, List) and get_args(type_hint):
            item_cls = get_args(type_hint)[0]
            if isinstance(value, list):
                return _ConfigList(value, self._save_callback, item_cls)

        # 检查是否是普通类（非泛型），并且值是字典
        if isinstance(type_hint, type) and not get_origin(type_hint) and isinstance(value, dict):
            # 排除内置的集合类型
            if type_hint not in (str, int, float, bool, dict, list, set):
                return _ConfigObject(value, self._save_callback, type_hint)

        if isinstance(value, dict):
            return _ConfigObject(value, self._save_callback, type)

        if isinstance(value, list):
            return _ConfigList(value, self._save_callback, type)

        return value

    def _unwrap(self, value: Any) -> Any:
        """将代理对象转换回原始的 dict/list"""
        if isinstance(value, _ConfigObject):
            return value._data
        if isinstance(value, _ConfigList):
            return value._data
        if isinstance(value, list):
            return [self._unwrap(v) for v in value]
        if isinstance(value, dict):
            return {k: self._unwrap(v) for k, v in value.items()}
        return value

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            value = self._data.get(name)
            return self._wrap(name, value)
        # 如果数据中没有，但类中有默认值，也返回它
        if hasattr(self._template_cls, name):
            value = getattr(self._template_cls, name)
            # 包装一下以支持嵌套操作
            return self._wrap(name, value)
        return None

    def __setattr__(self, name: str, value: Any):
        unwrapped_value = self._unwrap(value)
        self._data[name] = unwrapped_value
        self._save_callback()

    def __delattr__(self, name: str):
        if name in self._data:
            del self._data[name]
            self._save_callback()
        else:
            raise AttributeError(f"'{self._template_cls.__name__}' object has no attribute '{name}'")

    def __repr__(self) -> str:
        return f"<ConfigObject wrapping {self._data}>"


class _ConfigList(Generic[T]):
    """代理类，用于处理配置中的列表，使其支持 append 等操作并自动保存。"""
    def __init__(self, data: list, save_callback: callable, item_cls: Type[T]):
        self._data = data
        self._save_callback = save_callback
        self._item_cls = item_cls

    def _wrap_item(self, item_data: Any) -> Any:
        if isinstance(item_data, dict) and self._item_cls is not type:
            return _ConfigObject(item_data, self._save_callback, self._item_cls)
        return item_data

    def _unwrap_item(self, item: Any) -> Any:
        if isinstance(item, _ConfigObject):
            return item._data
        return item

    def __getitem__(self, index: int) -> T:
        return self._wrap_item(self._data[index])

    def __setitem__(self, index: int, value: T):
        self._data[index] = self._unwrap_item(value)
        self._save_callback()

    def __delitem__(self, index: int):
        del self._data[index]
        self._save_callback()

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def append(self, item: Any):
        self._data.append(self._unwrap_item(item))
        self._save_callback()

    def clear(self):
        self._data.clear()
        self._save_callback()

    def __repr__(self) -> str:
        return f"<ConfigList wrapping {self._data}>"

class JsonConfigManager:
    def __init__(self, filename: str = "./resources/config/config.json", auto_generate_on_empty: bool = True):
        self._lock = threading.RLock()
        self.filename = self._resolve_config_path(filename)
        self.auto_generate_on_empty = auto_generate_on_empty
        self.data: dict = {}
        self._load()

    def _generate_defaults_for_class(self, target_cls: Type) -> dict:
        """
        (混合模式)
        为类生成默认值字典。
        - 如果属性有默认值，则使用它。
        - 否则，根据类型生成一个"空"值。
        """
        defaults = {}
        annotations = getattr(target_cls, '__annotations__', {})
        for name, type_hint in annotations.items():
            if hasattr(target_cls, name):
                defaults[name] = getattr(target_cls, name)
            else:
                origin = get_origin(type_hint)
                if type_hint in (int, float):
                    defaults[name] = 0
                elif type_hint is bool:
                    defaults[name] = True
                elif type_hint is str:
                    defaults[name] = ""
                elif origin in (list, List):
                    defaults[name] = []
                elif origin in (dict, Dict):
                    defaults[name] = {}
                elif isinstance(type_hint, type) and not origin:
                    defaults[name] = self._generate_defaults_for_class(type_hint)
                else:
                    defaults[name] = None
        return defaults

    def getInstance(self, cls: Type[T]) -> T:
        with self._lock:
            # 只有在数据为空且开关为 True 时才生成默认配置
            if not self.data and self.auto_generate_on_empty:
                self.data = self._generate_defaults_for_class(cls)
                if self.data:
                    self._save()
            return _ConfigObject(self.data, self._save, cls)

    def _resolve_config_path(self, filename: str) -> str:
        if os.path.isabs(filename):
            return filename
        return os.path.join(os.getcwd(), filename)

    def _load(self):
        with self._lock:
            if not os.path.exists(self.filename):
                dir_name = os.path.dirname(self.filename)
                if dir_name: os.makedirs(dir_name, exist_ok=True)
                with open(self.filename, 'w', encoding='utf-8') as f: f.write('{}')
                self.data = {}
                return
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.data = {} if not content.strip() else json.loads(content)
            except (json.JSONDecodeError, IOError) as e:
                sys.stderr.write(f"FATAL: 加载 {self.filename} 失败. Error: {e}\n")
                self.data = {}

    def _save(self):
        with self._lock:
            try:
                dir_name = os.path.dirname(self.filename)
                if dir_name: os.makedirs(dir_name, exist_ok=True)
                with open(self.filename, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=4)
            except IOError as e:
                sys.stderr.write(f"FATAL: 保存 {self.filename} 失败. Error: {e}\n")


def injectJson(manager: JsonConfigManager):
    """
    装饰器工厂: 将一个类转换为一个配置对象的"工厂"。
    """
    def decorator(cls: Type[T]) -> Callable[..., T]:
        def factory(*args, **kwargs) -> T:
            return manager.getInstance(cls)
        return factory
    return decorator

