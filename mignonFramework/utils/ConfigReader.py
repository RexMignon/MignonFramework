import os
import configparser
import sys
import threading

class ConfigManager:
    """
    一个线程安全的配置文件管理类，用于简化配置的获取和写入操作。

    通过在所有读写操作中使用锁，确保了在多线程环境中的数据一致性。
    """

    def __init__(self, filename='./resources/config/config.ini', section='config', default_config_data=None):
        """
        初始化 ConfigManager 实例。
        """
        self.filename = filename
        self.section = section
        self.parser = configparser.ConfigParser()
        self.config_path = self._resolve_config_path()

        # 线程安全：引入一个锁来保护共享资源
        self._lock = threading.Lock()

        config_exists = os.path.exists(self.config_path)

        if default_config_data:
            self.parser.read_dict(default_config_data)

        if config_exists:
            try:
                # 初始化时的读取操作也需要锁
                with self._lock:
                    self.parser.read(self.config_path, encoding='utf-8')
            except configparser.Error as e:
                print(f"初始化时读取配置文件 '{self.config_path}' 时出错：{e}", file=sys.stderr)
        else:
            if not self.parser.has_section(self.section):
                self.parser.add_section(self.section)

            try:
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                # 初始化时的写入操作也需要锁
                with self._lock:
                    with open(self.config_path, 'w', encoding='utf-8') as configfile:
                        self.parser.write(configfile)
                print(f"配置文件 '{self.config_path}' 不存在，已根据默认值（或空节）创建。", file=sys.stdout)
            except Exception as e:
                print(f"创建默认配置文件 '{self.config_path}' 时出错：{e}", file=sys.stderr)


    def _resolve_config_path(self):
        """
        内部方法：根据文件名解析配置文件的绝对路径。
        """
        current_execution_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        if not os.path.isabs(self.filename):
            return os.path.abspath(os.path.join(current_execution_dir, self.filename))
        else:
            return self.filename

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

    def getConfig(self, field):
        """
        获取配置文件中指定节的单个字段值。
        此方法现在是线程安全的。

        :param field: 要获取的字段名称（str）。
        :return: 字段的值（str），如果配置文件、节或字段不存在则返回 None。
        """
        all_fields = self.getAllConfig()
        if all_fields is None:
            return None
        return all_fields.get(field)

    def setConfig(self, field, value):
        """
        更新配置文件中指定节的单个字段值。
        此方法现在是线程安全的。

        :param field: 要更新的字段名称（str）。
        :param value: 要设置的字段值（str 或可转换为 str 的类型）。
        :return: 成功返回 True，失败返回 False。
        """
        if not isinstance(value, str):
            value = str(value)

        # 在写入操作前后加锁
        with self._lock:
            if os.path.exists(self.config_path):
                try:
                    self.parser.read(self.config_path, encoding='utf-8')
                except configparser.Error as e:
                    print(f"写入前读取配置文件 '{self.config_path}' 时出错：{e}", file=sys.stderr)
                    return False

            if not self.parser.has_section(self.section):
                self.parser.add_section(self.section)

            self.parser.set(self.section, field, value)

            try:
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w', encoding='utf-8') as configfile:
                    self.parser.write(configfile)
                return True
            except Exception as e:
                print(f"写入配置文件 '{self.config_path}' 时出错：{e}", file=sys.stderr)
                return False

