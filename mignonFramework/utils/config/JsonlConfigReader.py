import os
import json
import sys
import threading
import types
import ast
from typing import Any, List, Type, TypeVar, Generic, get_origin, get_args, Callable, Dict

T = TypeVar('T')


def ClassKey(key_name: str):
    """
    类装饰器，用于指定哪个属性作为列表转为 HashMap 时的键。

    用法:
        @ClassKey('id')
        class User:
            id: int
            name: str
    """
    def decorator(cls: Type[T]) -> Type[T]:
        # 将键名作为一个特殊的属性存储在类本身上
        setattr(cls, '_class_key', key_name)
        return cls
    return decorator


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

        if isinstance(type_hint, type) and not get_origin(type_hint) and isinstance(value, dict):
            if type_hint not in (str, int, float, bool, dict, list, set):
                return _ConfigObject(value, self._save_callback, type_hint)

        if isinstance(value, dict):
            return _ConfigObject(value, self._save_callback, type)

        if isinstance(value, list):
            return _ConfigList(value, self._save_callback, type)

        return value

    def _unwrap(self, value: Any) -> Any:
        """
        将代理对象或自定义对象转换回原始的 dict/list，用于 JSON 序列化。
        """
        if isinstance(value, _ConfigObject):
            return value._data
        if isinstance(value, _ConfigList):
            return value._data

        if isinstance(value, list):
            return [self._unwrap(v) for v in value]
        if isinstance(value, dict):
            return {k: self._unwrap(v) for k, v in value.items()}

        if hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, list, dict, type)):
            return {k: v for k, v in value.__dict__.items() if not k.startswith('_')}

        return value

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            value = self._data.get(name)
            return self._wrap(name, value)
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
        return f"<ConfigObject wrapping {self._data}>"


class _ConfigList(Generic[T]):
    """
    代理类，用于处理配置中的列表。
    如果列表的元素类型被 @ClassKey 装饰，则会自动建立索引并提供 find/keys 方法。
    """
    def __init__(self, data: list, save_callback: callable, item_cls: Type[T]):
        self._data = data
        self._save_callback = save_callback
        self._item_cls = item_cls

        # --- 新增：检查 ClassKey 并初始化索引 ---
        self._key_name = getattr(item_cls, '_class_key', None)
        self._key_map = None
        if self._key_name:
            self._rebuild_index()
        # --- 结束新增部分 ---

    def _rebuild_index(self):
        """
        【新增】
        根据 _key_name 重新构建内部的哈希映射索引。
        索引的格式为 {key_value: list_index}
        """
        if not self._key_name:
            return
        self._key_map = {}
        for i, item_dict in enumerate(self._data):
            if isinstance(item_dict, dict):
                key_value = item_dict.get(self._key_name)
                if key_value is not None:
                    # 如果有重复的键，后面的会覆盖前面的
                    self._key_map[key_value] = i

    def find(self, key_value: Any) -> T | None:
        """
        【新增】
        根据 @ClassKey 指定的键快速查找元素。
        如果列表不支持键查找，或者找不到元素，则返回 None。
        """
        if self._key_map is None:
            raise AttributeError("This list is not indexed. Use @ClassKey on the list's item class to enable 'find'.")

        index = self._key_map.get(key_value)
        if index is not None:
            return self[index]  # 使用 __getitem__ 来获取包装后的对象
        return None

    def keys(self) -> list:
        """
        【新增】
        获取所有 @ClassKey 指定的键的列表。
        """
        if self._key_map is None:
            raise AttributeError("This list is not indexed. Use @ClassKey on the list's item class to enable 'keys'.")
        return list(self._key_map.keys())


    def _wrap_item(self, item_data: Any) -> Any:
        if isinstance(item_data, dict) and self._item_cls is not type:
            return _ConfigObject(item_data, self._save_callback, self._item_cls)
        return item_data

    def _unwrap_item(self, item: Any) -> Any:
        if isinstance(item, _ConfigObject):
            return item._data
        if hasattr(item, '__dict__') and not isinstance(item, (str, int, float, bool, list, dict, type)):
            return {k: v for k, v in item.__dict__.items() if not k.startswith('_')}
        if isinstance(item, list):
            return [self._unwrap_item(v) for v in item]
        if isinstance(item, dict):
            return {k: self._unwrap_item(v) for k, v in item.items()}
        return item

    def __getitem__(self, index: int) -> T:
        return self._wrap_item(self._data[index])

    def __setitem__(self, index: int, value: T):
        self._data[index] = self._unwrap_item(value)
        if self._key_name: self._rebuild_index() # 更新索引
        self._save_callback()

    def __delitem__(self, index: int):
        del self._data[index]
        if self._key_name: self._rebuild_index() # 更新索引
        self._save_callback()

    def __len__(self) -> int:
        return len(self._data)

    def copy(self):
        return self._data.copy()

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def remove(self, item):
        self._data.remove(self._unwrap_item(item))
        if self._key_name: self._rebuild_index() # 更新索引
        self._save_callback()

    def pop(self, index: int = -1) -> T:
        unwrapped_value = self._data.pop(index)
        if self._key_name: self._rebuild_index() # 更新索引
        self._save_callback()
        return self._wrap_item(unwrapped_value)

    def append(self, item: Any):
        self._data.append(self._unwrap_item(item))
        if self._key_name: self._rebuild_index() # 更新索引
        self._save_callback()

    def clear(self):
        self._data.clear()
        if self._key_name: self._rebuild_index() # 更新索引
        self._save_callback()

    def __repr__(self) -> str:
        if self._key_name:
            return f"<IndexedConfigList wrapping {self._data}>"
        return f"<ConfigList wrapping {self._data}>"

    def extend(self, iterable):
        for item in iterable:
            self._data.append(self._unwrap_item(item))
        if self._key_name: self._rebuild_index() # 更新索引
        self._save_callback()

    def insert(self, index: int, item: Any):
        self._data.insert(index, self._unwrap_item(item))
        if self._key_name: self._rebuild_index() # 更新索引
        self._save_callback()

    def reverse(self):
        self._data.reverse()
        if self._key_name: self._rebuild_index() # 更新索引
        self._save_callback()

    def sort(self, key=None, reverse=False):
        if key:
            wrapped_key = lambda item: self._unwrap_item(key(self._wrap_item(item)))
            self._data.sort(key=wrapped_key, reverse=reverse)
        else:
            self._data.sort(reverse=reverse)
        if self._key_name: self._rebuild_index() # 更新索引
        self._save_callback()

    def index(self, value, start=0, stop=sys.maxsize):
        return self._data.index(self._unwrap_item(value), start, stop)

    def count(self, value):
        return self._data.count(self._unwrap_item(value))

    def __add__(self, other):
        new_data = self._data + self._unwrap_item(other)
        return _ConfigList(new_data, self._save_callback, self._item_cls)

    def __radd__(self, other):
        new_data = self._unwrap_item(other) + self._data
        return _ConfigList(new_data, self._save_callback, self._item_cls)

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __mul__(self, n: int):
        new_data = self._data * n
        return _ConfigList(new_data, self._save_callback, self._item_cls)

    def __rmul__(self, n: int):
        return self.__mul__(n)

    def __imul__(self, n: int):
        self._data *= n
        if self._key_name: self._rebuild_index() # 更新索引
        self._save_callback()
        return self

    def __contains__(self, item: Any) -> bool:
        return self._unwrap_item(item) in self._data

    def __eq__(self, other: Any) -> bool:
        return self._data == self._unwrap_item(other)



class JsonConfigManager:
    def __init__(self, filename: str = "./resources/config/config.json", auto_generate_on_empty: bool = True):
        self._lock = threading.RLock()
        self.filename = self._resolve_config_path(filename)
        self.auto_generate_on_empty = auto_generate_on_empty
        self.data: dict = {}
        self._load()

    def _generate_defaults_for_class(self, target_cls: Type) -> dict:
        defaults = {}
        annotations = getattr(target_cls, '__annotations__', {})
        for name, type_hint in annotations.items():
            if hasattr(target_cls, name):
                defaults[name] = getattr(target_cls, name)
            else:
                origin = get_origin(type_hint)
                if type_hint in (int, float): defaults[name] = 0
                elif type_hint is bool: defaults[name] = True
                elif type_hint is str: defaults[name] = ""
                elif origin in (list, List): defaults[name] = []
                elif origin in (dict, Dict): defaults[name] = {}
                elif isinstance(type_hint, type) and not origin:
                    defaults[name] = self._generate_defaults_for_class(type_hint)
                else: defaults[name] = None
        return defaults

    def getInstance(self, cls: Type[T]) -> T:
        with self._lock:
            if not self.data and self.auto_generate_on_empty:
                self.data = self._generate_defaults_for_class(cls)
                if self.data: self._save()
            return _ConfigObject(self.data, self._save, cls)

    @staticmethod
    def _deep_dict_to_object(data: Any) -> Any:
        if isinstance(data, dict):
            return types.SimpleNamespace(**{k: JsonConfigManager._deep_dict_to_object(v) for k, v in data.items()})
        elif isinstance(data, list):
            return [JsonConfigManager._deep_dict_to_object(item) for item in data]
        return data

    @staticmethod
    def dictToObject(cls: Type[T], data_dict: dict | str) -> T:
        if isinstance(data_dict, str):
            try: data_dict = json.loads(data_dict)
            except json.JSONDecodeError:
                try: data_dict = ast.literal_eval(data_dict)
                except (ValueError, SyntaxError): raise TypeError("Input string is not a valid JSON or Python literal.")
        if not isinstance(data_dict, dict):
            raise TypeError("Input data must be a dictionary or a string representing one.")
        try:
            instance = cls()
            annotations = getattr(cls, '__annotations__', {})
            for name, type_hint in annotations.items():
                value = data_dict.get(name)
                if name not in data_dict: setattr(instance, name, None); continue
                if value is None: setattr(instance, name, None); continue
                origin, args = get_origin(type_hint), get_args(type_hint)
                is_class_type_hint = isinstance(type_hint, type) and not origin
                if is_class_type_hint and isinstance(value, dict):
                    if type_hint is Any: setattr(instance, name, JsonConfigManager._deep_dict_to_object(value))
                    else: setattr(instance, name, JsonConfigManager.dictToObject(type_hint, value))
                elif origin in (list, List) and args and isinstance(value, list):
                    item_cls = args[0]
                    is_item_complex_class = (isinstance(item_cls, type) and not get_origin(item_cls) and item_cls not in (Any, str, int, float, bool))
                    if is_item_complex_class: converted_list = [JsonConfigManager.dictToObject(item_cls, item) for item in value if isinstance(item, dict)]
                    else: converted_list = [JsonConfigManager._deep_dict_to_object(item) for item in value]
                    wrapped_list = _ConfigList(converted_list, lambda: None, item_cls)
                    setattr(instance, name, wrapped_list)
                else: setattr(instance, name, value)
            return instance
        except Exception as e:
            sys.stderr.write(f"FATAL: Error converting dictionary to {cls.__name__}: {e}\n")
            raise

    def _resolve_config_path(self, filename: str) -> str:
        if os.path.isabs(filename): return filename
        return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), filename)

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
            except json.JSONDecodeError as e:
                sys.stderr.write(f"FATAL: 加载 {self.filename} 失败. Error: {e}\n")
                self.data = {}
            except IOError as e:
                sys.stderr.write(f"FATAL: 读取 {self.filename} 失败. Error: {e}\n")
                self.data = {}

    @staticmethod
    def default_json_encoder(obj):
        if hasattr(obj, 'to_dict') and callable(obj.to_dict): return obj.to_dict()
        if hasattr(obj, '__dict__'): return obj.__dict__
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

    def _save(self):
        with self._lock:
            try:
                dir_name = os.path.dirname(self.filename)
                if dir_name: os.makedirs(dir_name, exist_ok=True)
                with open(self.filename, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=4, default=self.default_json_encoder)
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