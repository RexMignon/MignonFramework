import os
import sys
import threading
import types
import dataclasses
from typing import Any, List, Type, TypeVar, Generic, get_origin, get_args, Callable, Dict

# 尝试导入 toml 库
try:
    import toml
except ImportError:
    sys.stderr.write("FATAL: 缺少 'toml' 库。请运行: pip install toml\n")
    sys.exit(1)

T = TypeVar('T')

def ClassKey(key_name: str):
    """
    类装饰器，用于指定哪个属性作为列表转为 HashMap 时的键。
    """
    def decorator(cls: Type[T]) -> Type[T]:
        setattr(cls, '_class_key', key_name)
        return cls
    return decorator

class _TomlProxyObject:
    """TOML 对象的代理类"""
    def __init__(self, data: dict, save_callback: callable, template_cls: Type):
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_save_callback", save_callback)
        object.__setattr__(self, "_template_cls", template_cls)
        object.__setattr__(self, "_annotations", getattr(template_cls, '__annotations__', {}))

    def _wrap(self, key: str, value: Any) -> Any:
        type_hint = self._annotations.get(key)

        if get_origin(type_hint) in (list, List) and get_args(type_hint):
            item_cls = get_args(type_hint)[0]
            if isinstance(value, list):
                return _TomlProxyList(value, self._save_callback, item_cls)

        if isinstance(type_hint, type) and not get_origin(type_hint) and isinstance(value, dict):
            if type_hint not in (str, int, float, bool, dict, list, set, Any):
                return _TomlProxyObject(value, self._save_callback, type_hint)

        if isinstance(value, dict):
            return _TomlProxyObject(value, self._save_callback, type)
        if isinstance(value, list):
            return _TomlProxyList(value, self._save_callback, type)
        return value

    def _unwrap(self, value: Any) -> Any:
        if isinstance(value, _TomlProxyObject): return value._data
        if isinstance(value, _TomlProxyList): return value._data
        if isinstance(value, list): return [self._unwrap(v) for v in value]
        if isinstance(value, dict): return {k: self._unwrap(v) for k, v in value.items()}
        if hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, list, dict, type)):
            return {k: v for k, v in value.__dict__.items() if not k.startswith('_')}
        return value

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            value = self._data.get(name)
            return self._wrap(name, value)
        # 即使数据中没有，如果类定义里有默认值，我们也可以返回默认值
        # 但此时不会写入文件，直到用户赋值。
        if hasattr(self._template_cls, name):
            value = getattr(self._template_cls, name)
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
        return f"<TomlObject wrapping {self._data}>"


class _TomlProxyList(Generic[T]):
    """TOML 列表代理类"""
    def __init__(self, data: list, save_callback: callable, item_cls: Type[T]):
        self._data = data
        self._save_callback = save_callback
        self._item_cls = item_cls
        self._key_name = getattr(item_cls, '_class_key', None)
        self._key_map = None
        if self._key_name: self._rebuild_index()

    def _rebuild_index(self):
        if not self._key_name: return
        self._key_map = {}
        for i, item_dict in enumerate(self._data):
            if isinstance(item_dict, dict):
                key_value = item_dict.get(self._key_name)
                if key_value is not None: self._key_map[key_value] = i

    def find(self, key_value: Any) -> T | None:
        if self._key_map is None: raise AttributeError("List not indexed. Use @ClassKey.")
        index = self._key_map.get(key_value)
        return self[index] if index is not None else None

    def keys(self) -> list:
        if self._key_map is None: raise AttributeError("List not indexed. Use @ClassKey.")
        return list(self._key_map.keys())

    def _wrap_item(self, item_data: Any) -> Any:
        if isinstance(item_data, dict) and self._item_cls is not type:
            return _TomlProxyObject(item_data, self._save_callback, self._item_cls)
        return item_data

    def _unwrap_item(self, item: Any) -> Any:
        if isinstance(item, _TomlProxyObject): return item._data
        if hasattr(item, '__dict__') and not isinstance(item, (str, int, float, bool, list, dict, type)):
            return {k: v for k, v in item.__dict__.items() if not k.startswith('_')}
        if isinstance(item, list): return [self._unwrap_item(v) for v in item]
        if isinstance(item, dict): return {k: self._unwrap_item(v) for k, v in item.items()}
        return item

    def __getitem__(self, index: int) -> T:
        return self._wrap_item(self._data[index])

    def __setitem__(self, index: int, value: T):
        self._data[index] = self._unwrap_item(value)
        if self._key_name: self._rebuild_index()
        self._save_callback()

    def __delitem__(self, index: int):
        del self._data[index]
        if self._key_name: self._rebuild_index()
        self._save_callback()

    def __len__(self) -> int: return len(self._data)
    def append(self, item: Any):
        self._data.append(self._unwrap_item(item))
        if self._key_name: self._rebuild_index()
        self._save_callback()
    def remove(self, item: Any):
        self._data.remove(self._unwrap_item(item))
        if self._key_name: self._rebuild_index()
        self._save_callback()
    def clear(self):
        self._data.clear()
        if self._key_name: self._rebuild_index()
        self._save_callback()
    def __iter__(self):
        for i in range(len(self)): yield self[i]
    def __repr__(self) -> str: return f"<TomlList wrapping {self._data}>"


class TomlConfigManager:
    def __init__(self, filename: str = "./resources/config/config.toml", auto_sync: bool = True):
        self._lock = threading.RLock()
        self.filename = self._resolve_config_path(filename)
        self.auto_sync = auto_sync  # 控制是否自动补全缺失字段
        self.data: dict = {}
        self._load()

    def _resolve_config_path(self, filename: str) -> str:
        if os.path.isabs(filename): return filename
        return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), filename)

    def _generate_defaults_for_class(self, target_cls: Type) -> dict:
        """
        递归生成默认配置字典。
        """
        defaults = {}
        annotations = getattr(target_cls, '__annotations__', {})

        # 兼容 Dataclasses，处理 field(default=...) 和 field(default_factory=...)
        is_dc = dataclasses.is_dataclass(target_cls)

        for name, type_hint in annotations.items():
            value_set = False
            default_value = None

            # 1. 尝试从类属性获取 (适用于普通类和 dataclass 的 default)
            if hasattr(target_cls, name):
                val = getattr(target_cls, name)
                # 排除 dataclasses.Field 对象，我们需要它的 default 值
                if not (is_dc and isinstance(val, dataclasses.Field)):
                    default_value = val
                    value_set = True

            # 2. 如果是 dataclass 且是 Field 对象，尝试提取 default 或 default_factory
            if not value_set and is_dc:
                # 找到对应的 Field 对象
                for f in dataclasses.fields(target_cls):
                    if f.name == name:
                        if f.default is not dataclasses.MISSING:
                            default_value = f.default
                            value_set = True
                        elif f.default_factory is not dataclasses.MISSING:
                            try:
                                default_value = f.default_factory()
                                value_set = True
                            except: pass
                        break

            if value_set:
                # 如果获取到的值是自定义类对象，需要将其转为字典（递归）
                if hasattr(default_value, '__annotations__') and not isinstance(default_value, (str, int, float, bool, list, dict)):
                    defaults[name] = self._generate_defaults_for_class(type(default_value))
                # 如果是列表，且里面的元素是对象，也需要转换（简化处理：暂只处理空列表或基础类型）
                else:
                    defaults[name] = default_value
            else:
                # 3. 如果没有默认值，根据类型提示生成零值
                origin = get_origin(type_hint)
                if type_hint in (int, float): defaults[name] = 0
                elif type_hint is bool: defaults[name] = True
                elif type_hint is str: defaults[name] = ""
                elif origin in (list, List): defaults[name] = []
                elif origin in (dict, Dict): defaults[name] = {}
                elif isinstance(type_hint, type) and not origin:
                    # 递归处理嵌套类
                    defaults[name] = self._generate_defaults_for_class(type_hint)
                else:
                    defaults[name] = ""
        return defaults

    def _merge_defaults(self, defaults: dict, current_data: dict) -> bool:
        """
        【核心逻辑】深度合并默认值到当前数据中。
        只有当 key 不存在时才写入默认值（增量更新），
        如果 key 存在，则保留现有值。
        返回 True 表示有数据被修改/新增。
        """
        is_modified = False
        for key, default_val in defaults.items():
            if key not in current_data:
                # 缺失字段，补全
                current_data[key] = default_val
                is_modified = True
            elif isinstance(default_val, dict) and isinstance(current_data[key], dict):
                # 递归合并嵌套字典 (Section)
                if self._merge_defaults(default_val, current_data[key]):
                    is_modified = True
            # 列表和基本类型，以当前文件中的值为准，不覆盖
        return is_modified

    def getInstance(self, cls: Type[T]) -> T:
        with self._lock:
            # 1. 生成代码中定义的最新结构默认值
            defaults = self._generate_defaults_for_class(cls)

            if not self.data:
                # Case A: 文件不存在或为空，完全使用默认值
                self.data = defaults
                self._save()
            elif self.auto_sync:
                # Case B: 文件存在，执行增量合并
                # 如果合并过程中发现有新字段被添加，则保存
                if self._merge_defaults(defaults, self.data):
                    self._save()

            return _TomlProxyObject(self.data, self._save, cls)

    def _load(self):
        with self._lock:
            if not os.path.exists(self.filename):
                dir_name = os.path.dirname(self.filename)
                if dir_name: os.makedirs(dir_name, exist_ok=True)
                with open(self.filename, 'w', encoding='utf-8') as f: f.write('')
                self.data = {}
                return
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.data = toml.loads(content) if content.strip() else {}
            except Exception as e:
                sys.stderr.write(f"FATAL: 加载 TOML {self.filename} 失败. Error: {e}\n")
                self.data = {}

    def _save(self):
        with self._lock:
            try:
                dir_name = os.path.dirname(self.filename)
                if dir_name: os.makedirs(dir_name, exist_ok=True)
                with open(self.filename, 'w', encoding='utf-8') as f:
                    toml.dump(self.data, f)
            except Exception as e:
                sys.stderr.write(f"FATAL: 保存 TOML {self.filename} 失败. Error: {e}\n")


def injectToml(manager: TomlConfigManager):
    """
    装饰器工厂: 将一个类转换为 TOML 配置对象。
    """
    def decorator(cls: Type[T]) -> Callable[..., T]:
        def factory(*args, **kwargs) -> T:
            return manager.getInstance(cls)
        return factory
    return decorator