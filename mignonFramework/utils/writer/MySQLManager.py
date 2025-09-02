# MysqlManager.py
import pymysql
import pymysql.cursors
import time
import functools
from typing import List, Dict, Any, Optional

from mignonFramework.utils.writer.BaseWriter import BaseWriter


# --- 新增的装饰器，用于实现自动重连 ---
def ensure_connection(func):
    """
    一个装饰器，确保在执行数据库操作前连接是有效的。
    如果连接断开，它将根据预设的策略尝试重新连接。
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            # 高效地检查连接是否存活，reconnect=True 会尝试自动重连一次
            self.connection.ping(reconnect=True)
        except (pymysql.err.OperationalError, pymysql.err.InterfaceError):
            print("[MySQLManager] 连接已丢失，正在尝试重新连接...")
            self.reconnect()  # 执行完整的重连逻辑

        # 再次尝试执行原始方法
        while True:
            try:
                return func(self, *args, **kwargs)
            except (pymysql.err.OperationalError, pymysql.err.InterfaceError) as e:
                # 如果在ping之后、操作完成之前连接再次断开
                print(f"[MySQLManager] 操作期间连接丢失: {e}。将再次尝试重连并执行操作。")
                self.reconnect()
                # 最后再尝试一次
                return func(self, *args, **kwargs)

    return wrapper


class MysqlManager(BaseWriter):
    """
    一个用于管理pymysql数据库连接和执行批量操作的类。
    这是 BaseWriter 的一个具体实现，用于写入MySQL数据库。
    此版本增加了健壮的自动重连机制。
    """

    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306,
                 max_retries: int = 999, retry_delay: int = 2):
        """
        初始化数据库管理器。
        :param max_retries: 最大重连尝试次数。
        :param retry_delay: 初始重连延迟（秒），后续会指数增加。
        """
        self.db_config = {
            'host': host, 'user': user, 'password': password, 'database': database,
            'port': port, 'charset': 'utf8mb4', 'cursorclass': pymysql.cursors.DictCursor,
            'connect_timeout': 10
        }
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection: Optional[pymysql.connections.Connection] = None
        self._connect()  # 初始连接

    def _connect(self) -> None:
        """内部方法，用于建立数据库连接。"""
        try:
            self.connection = pymysql.connect(**self.db_config)
            print("[MySQLManager] 数据库连接成功。")
        except pymysql.MySQLError as e:
            print(f"[MySQLManager] 数据库连接失败: {e}")
            self.connection = None

    def reconnect(self) -> None:
        """
        执行重连逻辑，包含多次尝试和指数退避。
        """
        if self.connection:
            try:
                self.connection.close()
            except pymysql.MySQLError:
                pass  # 如果连接已经失效，关闭时可能会出错，忽略即可
        self.connection = None

        for i in range(self.max_retries):
            delay = self.retry_delay * (2 ** i)
            print(f"[MySQLManager] 第 {i + 1}/{self.max_retries} 次尝试重连... 将在 {delay} 秒后重试。")
            time.sleep(delay)
            self._connect()
            if self.is_connected():
                return

        # 如果所有尝试都失败了，则抛出异常
        raise ConnectionError(f"[MySQLManager] 无法重新连接到数据库，已达到最大尝试次数 ({self.max_retries})。")

    def is_connected(self) -> bool:
        """检查当前是否已成功连接到数据库。"""
        return self.connection is not None and self.connection.open

    def close(self):
        """关闭数据库连接。"""
        if self.is_connected():
            self.connection.close()
            self.connection = None
            print("[MySQLManager] 数据库连接已主动关闭。")

    @ensure_connection
    def upsert_batch(self, data_list: List[Dict[str, Any]], table_name: str, test: bool = False) -> bool:
        """
        将数据字典列表批量插入或更新到数据库中 (Upsert)。
        此方法现在受自动重连机制保护。
        """
        if not data_list:
            return True

        columns = list(data_list[0].keys())
        update_columns = [col for col in columns if col.lower() not in ['id', 'create_time']]
        sql = f"""
            INSERT INTO `{table_name}` ({', '.join(f'`{col}`' for col in columns)})
            VALUES ({', '.join(['%s'] * len(columns))})
            ON DUPLICATE KEY UPDATE {', '.join(f'`{col}` = VALUES(`{col}`)' for col in update_columns)}
        """
        values = [tuple(data.get(col) for col in columns) for data in data_list]

        try:
            with self.connection.cursor() as cursor:
                cursor.executemany(sql, values)
            if not test:
                self.connection.commit()
            return True
        except pymysql.MySQLError as e:
            self.connection.rollback()
            raise e

    @ensure_connection
    def upsert_single(self, data_dict: Dict[str, Any], table_name: str, test: bool = False) -> bool:
        """
        将单个数据字典插入或更新到数据库中。
        此方法现在受自动重连机制保护。
        """
        if not data_dict:
            return True

        columns = list(data_dict.keys())
        update_columns = [col for col in columns if col.lower() not in ['id', 'create_time']]
        sql = f"""
            INSERT INTO `{table_name}` ({', '.join(f'`{col}`' for col in columns)})
            VALUES ({', '.join(['%s'] * len(columns))})
            ON DUPLICATE KEY UPDATE {', '.join(f'`{col}` = VALUES(`{col}`)' for col in update_columns)}
        """
        values = tuple(data_dict.get(col) for col in columns)

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, values)
            if not test: self.connection.commit()
            return True
        except pymysql.MySQLError as e:
            self.connection.rollback()
            raise e

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
