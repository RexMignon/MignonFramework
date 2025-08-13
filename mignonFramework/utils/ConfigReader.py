import os
import configparser
import sys
import threading
from typing import Any, Union, Type

# -----------------------------------------------------------------------------
# 1. ConfigManager 类 (无需改动)
# -----------------------------------------------------------------------------
class ConfigManager:
    """一个线程安全的配置文件管理类。"""
    def __init__(self, filename='./resources/config/config.ini', section='config'):
        self.filename = filename
        self.section = section
        self.parser = configparser.ConfigParser()
        self._lock = threading.RLock()
        self.config_path = self._resolve_config_path()

        if not os.path.exists(self.config_path):
            print(f"配置文件 '{self.config_path}' 不存在，将创建一个新的。")
            self._write_config()
        else:
            with self._lock:
                self.parser.read(self.config_path, encoding='utf-8')

    def _write_config(self):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with self._lock:
                if not self.parser.has_section(self.section):
                    self.parser.add_section(self.section)
                with open(self.config_path, 'w', encoding='utf-8') as configfile:
                    self.parser.write(configfile)
            return True
        except Exception as e:
            print(f"写入/创建配置文件 '{self.config_path}' 时出错：{e}", file=sys.stderr)
            return False

    def _resolve_config_path(self):
        if os.path.isabs(self.filename):
            return self.filename
        return os.path.join(os.getcwd(), self.filename)

    def getConfig(self, field: str) -> Union[str, None]:
        with self._lock:
            self.parser.read(self.config_path, encoding='utf-8')
            return self.parser.get(self.section, field, fallback=None)

    def setConfig(self, field: str, value: Any) -> bool:
        with self._lock:
            self.parser.read(self.config_path, encoding='utf-8')
            if not self.parser.has_section(self.section):
                self.parser.add_section(self.section)
            self.parser.set(self.section, field, str(value))
            return self._write_config()

# -----------------------------------------------------------------------------
# 2. 依赖注入框架 (核心升级)
# -----------------------------------------------------------------------------

class ValueDescriptor:
    """数据描述符，现在能正确处理布尔值和提供更智能的默认值。"""
    def __init__(self, key: str):
        self.key = key
        self.lower_key = key.lower()

    def __get__(self, instance: object, owner: type) -> Any:
        if instance is None:
            return self

        manager: ConfigManager = getattr(instance, '_config_manager', None)
        if not manager:
            raise AttributeError("ConfigManager not injected. Use the @inject(manager) decorator.")

        raw_value = manager.getConfig(self.lower_key)
        target_type = owner.__annotations__.get(self.key)

        if raw_value is None:
            # FIX: 提供更智能的默认值
            default_value: Any
            if target_type in (int, float):
                default_value = 0
            elif target_type is bool:
                default_value = False
            else:  # str and others
                default_value = 'str'

            manager.setConfig(self.lower_key, default_value)
            return default_value

        if target_type:
            try:
                # FIX: 正确处理布尔值的转换
                if target_type is bool:
                    return raw_value.lower() in ['true', '1', 'yes', 'on']
                return target_type(raw_value)
            except (ValueError, TypeError):
                return raw_value
        return raw_value

    def __set__(self, instance: object, value: Any):
        manager: ConfigManager = getattr(instance, '_config_manager', None)
        if not manager:
            raise AttributeError("ConfigManager not injected. Use the @inject(manager) decorator.")
        manager.setConfig(self.lower_key, value)


def inject(manager: ConfigManager):
    """
    装饰器工厂：现在会为类添加一个 __init__ 方法，
    以在实例化时主动初始化所有字段。
    """
    def decorator(cls: Type) -> Type:
        # 保存可能存在的原始 __init__
        original_init = cls.__init__ if '__init__' in cls.__dict__ else None

        def new_init(self, *args, **kwargs):
            """这个新的 __init__ 会在调用原始 __init__ 后，主动初始化所有字段。"""
            if original_init:
                original_init(self, *args, **kwargs)

            # 遍历所有注解的属性以触发它们的默认值创建
            for attr_name in getattr(cls, '__annotations__', {}):
                # 简单地访问属性就会触发 ValueDescriptor 的 __get__
                getattr(self, attr_name)

        # 1. 设置描述符和 manager
        setattr(cls, '_config_manager', manager)
        for attr_name in getattr(cls, '__annotations__', {}):
            setattr(cls, attr_name, ValueDescriptor(attr_name))

        # 2. 用我们的新 __init__ 替换掉原始的
        cls.__init__ = new_init

        return cls
    return decorator

