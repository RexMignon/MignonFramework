import os
import configparser
import sys
import threading
import inspect
from typing import Any, Union, Type


class ConfigManager:
    """
    一个线程安全的配置文件管理类，现在也充当配置实例的 DI 容器。
    """

    def __init__(self, filename='./resources/config/config.ini', section='config'):
        self._lock = threading.RLock()
        self.filename = filename
        self.section = section
        self.parser = configparser.ConfigParser()
        self.config_path = self._resolve_config_path()

        self._registry = {}

        # 确保配置文件和目录存在
        if not os.path.exists(self.config_path):
            dir_name = os.path.dirname(self.config_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            self._write_config()
        else:
            with self._lock:
                self.parser.read(self.config_path, encoding='utf-8')

    def getInstance(self, cls: Type) -> Any:
        """
        获取配置类的单例实例。
        如果实例不存在，会自动创建并缓存。这是推荐的获取配置对象的方式。
        """
        with self._lock:
            if cls not in self._registry:
                # 实例化类。被 @inject 装饰的 __init__ 会自动运行，
                # 确保所有字段都被初始化。
                self._registry[cls] = cls()
            return self._registry[cls]

    def _resolve_config_path(self):
        if os.path.isabs(self.filename):
            return self.filename
        return os.path.join(os.getcwd(), self.filename)

    def _write_config(self):
        try:
            with self._lock:
                if not self.parser.has_section(self.section):
                    self.parser.add_section(self.section)
                with open(self.config_path, 'w', encoding='utf-8') as configfile:
                    self.parser.write(configfile)
            return True
        except Exception as e:
            sys.stderr.write(f"FATAL: ConfigManager failed to write config. Error: {e}\n")
            return False

    def getConfig(self, field: str) -> Union[str, None]:
        with self._lock:
            self.parser.read(self.config_path, encoding='utf-8')
            return self.parser.get(self.section, field, fallback=None)

    def getAllConfig(self):
        """
        获取配置文件中指定节的所有字段及其值。
        此方法现在是线程安全的。

        :return: 包含配置数据的字典，如果节不存在则返回 None。
        """
        # 在读取操作前后加锁
        with self._lock:
            try:
                self.parser.read(self.config_path, encoding='utf-8')
            except configparser.Error as e:
                print(f"读取配置文件 '{self.config_path}' 时出错：{e}", file=sys.stderr)
                return None

            if self.parser.has_section(self.section):
                return dict(self.parser.items(self.section))
            else:
                print(f"错误：在 '{self.filename}' 中未找到节 '{self.section}'。", file=sys.stderr)
                return None

    def setConfig(self, field: str, value: Any) -> bool:
        with self._lock:
            self.parser.read(self.config_path, encoding='utf-8')
            if not self.parser.has_section(self.section):
                self.parser.add_section(self.section)
            self.parser.set(self.section, field, str(value))
            return self._write_config()


class ValueDescriptor:
    """数据描述符，支持用户自定义的默认值。"""

    def __init__(self, key: str, default: Any = None):
        self.key = key
        self.lower_key = key.lower()
        self.user_default = default

    def __get__(self, instance: object, owner: type) -> Any:
        if instance is None:
            return self
        manager: ConfigManager = getattr(instance, '_config_manager', None)
        if not manager:
            raise AttributeError("ConfigManager not injected.")

        raw_value = manager.getConfig(self.lower_key)
        target_type = owner.__annotations__.get(self.key)

        if raw_value is None:
            default_value: Any
            if self.user_default is not None:
                default_value = self.user_default
            else:
                if target_type in (int, float):
                    default_value = 0
                elif target_type is bool:
                    default_value = False
                else:
                    default_value = ''
            manager.setConfig(self.lower_key, default_value)
            return default_value

        if target_type:
            try:
                if target_type is bool:
                    return raw_value.lower() in ['true', '1', 'yes', 'on']
                return target_type(raw_value)
            except (ValueError, TypeError):
                return raw_value
        return raw_value

    def __set__(self, instance: object, value: Any):
        manager: ConfigManager = getattr(instance, '_config_manager', None)
        if not manager:
            raise AttributeError("ConfigManager not injected.")
        manager.setConfig(self.lower_key, value)


def inject(manager: ConfigManager):
    """
    装饰器工厂：读取类中定义的默认值，并重写 __init__ 以触发所有字段的初始化。
    """

    def decorator(cls: Type) -> Type:
        original_init = cls.__init__ if '__init__' in cls.__dict__ else None
        annotations = getattr(cls, '__annotations__', {})

        defaults = {attr_name: getattr(cls, attr_name) for attr_name in annotations if hasattr(cls, attr_name)}

        setattr(cls, '_config_manager', manager)
        for attr_name in annotations:
            setattr(cls, attr_name, ValueDescriptor(attr_name, default=defaults.get(attr_name)))

        def new_init(self, *args, **kwargs):
            if original_init:
                original_init(self, *args, **kwargs)
            for attr_name in annotations:
                getattr(self, attr_name)

        cls.__init__ = new_init
        return cls

    return decorator
