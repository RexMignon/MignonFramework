# MysqlManager.py
import pymysql
import pymysql.cursors
from typing import List, Dict, Any, Optional
from mignonFramework.utils.BaseWriter import BaseWriter


class MysqlManager(BaseWriter):
    """
    一个用于管理pymysql数据库连接和执行批量操作的类。
    这是 BaseWriter 的一个具体实现，用于写入MySQL数据库。
    """

    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306):
        """
        初始化数据库管理器并建立连接。
        """
        self.db_config = {
            'host': host, 'user': user, 'password': password, 'database': database,
            'port': port, 'charset': 'utf8mb4', 'cursorclass': pymysql.cursors.DictCursor,
            'connect_timeout': 10
        }
        self.connection: Optional[pymysql.connections.Connection] = self._connect()

    def _connect(self) -> Optional[pymysql.connections.Connection]:
        """内部方法，用于建立数据库连接。"""
        try:
            return pymysql.connect(**self.db_config)
        except pymysql.MySQLError as e:
            print(f"数据库连接失败: {e}")
            return None

    def is_connected(self) -> bool:
        """检查当前是否已成功连接到数据库。"""
        return self.connection is not None

    def close(self):
        """关闭数据库连接。"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def upsert_batch(self, data_list: List[Dict[str, Any]], table_name: str, test: bool = False) -> bool:
        """
        将数据字典列表批量插入或更新到数据库中 (Upsert)。
        这是 BaseWriter 接口的实现。
        """
        if not self.is_connected():
            raise ConnectionError("数据库未连接，无法执行更新/插入操作。")
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
            if not test: self.connection.commit()
            return True
        except pymysql.MySQLError as e:
            self.connection.rollback()
            raise e

    # --- 新增方法: upsert_single ---
    def upsert_single(self, data_dict: Dict[str, Any], table_name: str, test: bool = False) -> bool:
        """
        将单个数据字典插入或更新到数据库中。
        主要用于错误恢复模式。
        """
        if not self.is_connected():
            raise ConnectionError("数据库未连接，无法执行单行更新/插入操作。")
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
