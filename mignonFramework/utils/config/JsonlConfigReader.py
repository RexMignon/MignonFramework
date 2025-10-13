import os
import json
import sys
import threading
import types
import ast
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
            # 如果没有明确的模板类型，使用通用类型
            return _ConfigObject(value, self._save_callback, type)

        if isinstance(value, list):
            # 如果没有明确的模板类型，使用通用类型
            return _ConfigList(value, self._save_callback, type)

        return value

    def _unwrap(self, value: Any) -> Any:
        """
        将代理对象或自定义对象转换回原始的 dict/list，用于 JSON 序列化。
        注意：此处主要处理递归结构中的代理对象，对于append操作中的原始对象，
              _ConfigList._unwrap_item 方法处理得更精确。
        """
        if isinstance(value, _ConfigObject):
            return value._data
        if isinstance(value, _ConfigList):
            return value._data

        # 递归处理列表和字典
        if isinstance(value, list):
            return [self._unwrap(v) for v in value]
        if isinstance(value, dict):
            return {k: self._unwrap(v) for k, v in value.items()}

        # 修正：处理直接赋值的自定义类实例（虽然通常通过__setattr__实现）
        if hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, list, dict, type)):
            return {k: v for k, v in value.__dict__.items() if not k.startswith('_')}

        return value

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            value = self._data.get(name)
            return self._wrap(name, value)
        # 如果数据中没有，但类中有默认值，也返回它
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
    """代理类，用于处理配置中的列表，使其支持 append 等操作并自动保存。"""
    def __init__(self, data: list, save_callback: callable, item_cls: Type[T]):
        self._data = data
        self._save_callback = save_callback
        self._item_cls = item_cls

    def _wrap_item(self, item_data: Any) -> Any:
        if isinstance(item_data, dict) and self._item_cls is not type:
            # 尝试将其包装成对应的配置对象
            return _ConfigObject(item_data, self._save_callback, self._item_cls)
        return item_data

    def _unwrap_item(self, item: Any) -> Any:
        """
        核心修复点：将自定义类实例（如 ObjectData）转换为字典以便 JSON 序列化。
        """
        if isinstance(item, _ConfigObject):
            return item._data

        # 修复：检查item是否是自定义的类实例，如果是，将其转换为字典
        # 假设所有需要序列化的自定义配置类都有 __dict__ 属性
        if hasattr(item, '__dict__') and not isinstance(item, (str, int, float, bool, list, dict, type)):
            # 排除私有属性
            return {k: v for k, v in item.__dict__.items() if not k.startswith('_')}

        # 如果 item 是一个列表或字典，递归地对其内容进行解包（如果内容是代理对象）
        if isinstance(item, list):
            return [self._unwrap_item(v) for v in item]
        if isinstance(item, dict):
            return {k: self._unwrap_item(v) for k, v in item.items()}

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

    def copy(self):
        return self._data.copy()

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def remove(self, item):
        self._data.remove(self._unwrap_item(item))
        self._save_callback()

    def pop(self, index: int = -1) -> T:
        unwrapped_value = self._data.pop(index)
        self._save_callback()
        return self._wrap_item(unwrapped_value)

    def append(self, item: Any):
        # 核心：在 append 时对 item 进行解包，触发自定义对象到字典的转换
        self._data.append(self._unwrap_item(item))
        self._save_callback()

    def clear(self):
        self._data.clear()
        self._save_callback()

    def __repr__(self) -> str:
        return f"<ConfigList wrapping {self._data}>"

    def extend(self, iterable):
        for item in iterable:
            self._data.append(self._unwrap_item(item))
        self._save_callback()

    def insert(self, index: int, item: Any):
        self._data.insert(index, self._unwrap_item(item))
        self._save_callback()

    def index(self, value, start=0, stop=sys.maxsize):
        return self._data.index(self._unwrap_item(value), start, stop)

    def count(self, value):
        return self._data.count(self._unwrap_item(value))

    def reverse(self):
        self._data.reverse()
        self._save_callback()

    def sort(self, key=None, reverse=False):
        # 对内部数据进行排序，如果提供了key，则对key进行解包
        if key:
            wrapped_key = lambda item: self._unwrap_item(key(self._wrap_item(item)))
            self._data.sort(key=wrapped_key, reverse=reverse)
        else:
            self._data.sort(reverse=reverse)
        self._save_callback()

    def __add__(self, other):
        # 返回一个新的_ConfigList实例
        new_data = self._data + self._unwrap_item(other)
        return _ConfigList(new_data, self._save_callback, self._item_cls)

    def __radd__(self, other):
        # 允许左边的操作数是其他类型
        new_data = self._unwrap_item(other) + self._data
        return _ConfigList(new_data, self._save_callback, self._item_cls)

    def __iadd__(self, other):
        # 原地加法
        self.extend(other)
        return self

    def __mul__(self, n: int):
        new_data = self._data * n
        return _ConfigList(new_data, self._save_callback, self._item_cls)

    def __rmul__(self, n: int):
        return self.__mul__(n)

    def __imul__(self, n: int):
        self._data *= n
        self._save_callback()
        return self

    def __contains__(self, item: Any) -> bool:
        return self._unwrap_item(item) in self._data

    def __eq__(self, other: Any) -> bool:
        return self._data == self._unwrap_item(other)

    def __ne__(self, other: Any) -> bool:
        return self._data != self._unwrap_item(other)

    def __lt__(self, other: Any) -> bool:
        return self._data < self._unwrap_item(other)

    def __le__(self, other: Any) -> bool:
        return self._data <= self._unwrap_item(other)

    def __gt__(self, other: Any) -> bool:
        return self._data > self._unwrap_item(other)

    def __ge__(self, other: Any) -> bool:
        return self._data >= self._unwrap_item(other)

    def __reversed__(self):
        return reversed(self._data)


class JsonConfigManager:
    def __init__(self, filename: str = "./resources/config/config.json", auto_generate_on_empty: bool = True):
        self._lock = threading.RLock()
        self.filename = self._resolve_config_path(filename)
        self.auto_generate_on_empty = auto_generate_on_empty
        self.data: dict = {}
        self._load()

    def _generate_defaults_for_class(self, target_cls: Type) -> dict:
        """
        为类生成默认值字典。
        - 如果属性有默认值，则使用它。
        - 否则，根据类型生成一个"空"值。
        """
        defaults = {}
        annotations = getattr(target_cls, '__annotations__', {})
        for name, type_hint in annotations.items():
            if hasattr(target_cls, name):
                # 优先级 1: 类属性的默认值
                defaults[name] = getattr(target_cls, name)
            else:
                # 优先级 2: 根据类型提示生成空值
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
                    # 如果是嵌套的自定义类，递归生成默认配置
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

    @staticmethod
    def _deep_dict_to_object(data: Any) -> Any:
        """递归地将字典转换为 SimpleNamespace 对象。"""
        if isinstance(data, dict):
            return types.SimpleNamespace(**{k: JsonConfigManager._deep_dict_to_object(v) for k, v in data.items()})
        elif isinstance(data, list):
            return [JsonConfigManager._deep_dict_to_object(item) for item in data]
        return data

    @staticmethod
    def dictToObject(cls: Type[T], data_dict: dict | str) -> T:
        """
        将字典或字符串转换为指定类的对象，只转换类中定义的字段。
        如果字段在字典中不存在，则为 None。
        支持嵌套对象和动态对象(Any)。
        当类型为Any时，会递归转换所有嵌套字典。
        转换后的列表对象将拥有所有原生list方法。

        :param cls: 目标类。
        :param data_dict: 输入的字典或字符串。
        :return: 转换后的类实例。
        :raises TypeError: 如果输入不是一个字典或合法的字符串。
        :raises Exception: 在转换过程中发生的任何其他错误。
        """
        if isinstance(data_dict, str):
            try:
                data_dict = json.loads(data_dict)
            except json.JSONDecodeError:
                try:
                    data_dict = ast.literal_eval(data_dict)
                except (ValueError, SyntaxError):
                    raise TypeError("Input string is not a valid JSON or Python literal.")

        if not isinstance(data_dict, dict):
            raise TypeError("Input data must be a dictionary or a string representing one.")

        try:
            # 创建目标类的一个空实例
            # 注意：这要求目标类有一个无参数的构造函数。
            instance = cls()
            annotations = getattr(cls, '__annotations__', {})

            # 遍历类中定义的所有字段
            for name, type_hint in annotations.items():
                value = data_dict.get(name)

                # 1. 如果字典中不存在该键，则将属性设置为 None
                if name not in data_dict:
                    setattr(instance, name, None)
                    continue

                # 2. 如果字典中的值为 None，直接设置
                if value is None:
                    setattr(instance, name, None)
                    continue

                origin = get_origin(type_hint)
                args = get_args(type_hint)

                # 3. 处理嵌套对象
                is_class_type_hint = isinstance(type_hint, type) and not origin
                if is_class_type_hint and isinstance(value, dict):
                    if type_hint is Any:
                        # 对于 Any 类型，递归地将字典转换为 SimpleNamespace 对象
                        setattr(instance, name, JsonConfigManager._deep_dict_to_object(value))
                    else:
                        # 递归调用 dictToObject 来创建嵌套的类实例
                        nested_obj = JsonConfigManager.dictToObject(type_hint, value)
                        setattr(instance, name, nested_obj)
                # 4. 处理列表中的嵌套对象 (核心修改点)
                elif origin in (list, List) and args and isinstance(value, list):
                    item_cls = args[0]
                    converted_list = []

                    # 判断列表项是否是需要递归转换的复杂类
                    is_item_complex_class = (isinstance(item_cls, type) and
                                             not get_origin(item_cls) and
                                             item_cls not in (Any, str, int, float, bool))

                    if is_item_complex_class:
                        # 列表项是自定义类, e.g., List[MyClass]
                        converted_list = [JsonConfigManager.dictToObject(item_cls, item) for item in value if isinstance(item, dict)]
                    else:
                        # 列表项是基本类型或Any, e.g., List[int] or List[Any]
                        # 对 List[Any] 中的字典进行深度转换
                        converted_list = [JsonConfigManager._deep_dict_to_object(item) for item in value]

                    # 将最终生成的列表包装成 _ConfigList 以提供完整的 list 功能
                    # 回调函数为空，因为这是单次转换，不涉及保存
                    wrapped_list = _ConfigList(converted_list, lambda: None, item_cls)
                    setattr(instance, name, wrapped_list)
                # 5. 对于其他情况（如 str, int, bool 等基本类型），直接赋值
                else:
                    setattr(instance, name, value)

            return instance
        except Exception as e:
            # 打印错误信息并重新抛出异常
            sys.stderr.write(f"FATAL: Error converting dictionary to {cls.__name__}: {e}\n")
            raise


    def _resolve_config_path(self, filename: str) -> str:
        """解析配置文件的绝对路径。"""
        if os.path.isabs(filename):
            return filename
        # 相对路径以执行脚本的目录为基准
        return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), filename)


    def _load(self):
        """加载配置数据。"""
        with self._lock:
            if not os.path.exists(self.filename):
                dir_name = os.path.dirname(self.filename)
                if dir_name: os.makedirs(dir_name, exist_ok=True)
                # 写入空字典以创建文件
                with open(self.filename, 'w', encoding='utf-8') as f: f.write('{}')
                self.data = {}
                return
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 如果内容为空或只包含空白字符，则视为 {}
                    self.data = {} if not content.strip() else json.loads(content)
            except json.JSONDecodeError as e:
                # 打印第一个错误：JSONDecodeError。这表明配置文件内容格式不正确。
                sys.stderr.write(f"FATAL: 加载 {self.filename} 失败. Error: {e}\n")
                self.data = {}
            except IOError as e:
                sys.stderr.write(f"FATAL: 读取 {self.filename} 失败. Error: {e}\n")
                self.data = {}

    @staticmethod
    def default_json_encoder(obj):
        """一个静态方法，用于处理自定义对象的 JSON 序列化。"""
        if hasattr(obj, 'to_dict') and callable(obj.to_dict):
            return obj.to_dict()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

    def _save(self):
        """保存配置数据。"""
        with self._lock:
            try:
                dir_name = os.path.dirname(self.filename)
                if dir_name: os.makedirs(dir_name, exist_ok=True)
                with open(self.filename, 'w', encoding='utf-8') as f:
                    # 使用 default 参数传入自定义的编码函数
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

