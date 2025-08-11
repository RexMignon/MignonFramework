"""
MysqlManager: 一个健壮的 MySQL 数据库管理器。它封装了数据库的连接、关闭、以及高效的批量“更新或插入”（Upsert）操作，
并通过上下文管理器（with语句）简化了资源管理，确保连接的自动关闭。
"""
import pymysql
import pymysql.cursors
from typing import List, Dict, Any, Optional

class MysqlManager:
    """
    一个用于管理pymysql数据库连接和执行批量操作的类。

    该类封装了数据库的连接、关闭、批量插入和批量更新/插入（Upsert）等操作。
    推荐使用 'with' 语句来自动管理连接的生命周期。

    使用示例:
        db_config = {
            "host": "localhost",
            "user": "your_user",
            "password": "your_password",
            "database": "your_db"
        }
        with DatabaseManager(**db_config) as db:
            if db.is_connected():
                # db.insert_batch(...)
                # db.upsert_batch(...)
    """

    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306):
        """
        初始化数据库管理器并建立连接。

        Args:
            host (str): 数据库主机地址。
            user (str): 用户名。
            password (str): 密码。
            database (str): 数据库名称。
            port (int): 端口号，默认为 3306。
        """
        self.db_config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'port': port,
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
            'connect_timeout': 10
        }
        self.connection: Optional[pymysql.connections.Connection] = self._connect()

    def _connect(self) -> Optional[pymysql.connections.Connection]:
        """
        内部方法，用于建立数据库连接。

        Returns:
            pymysql.connections.Connection or None: 成功则返回连接对象, 失败则返回None。
        """
        try:
            connection = pymysql.connect(**self.db_config)
            print("数据库连接成功！")
            return connection
        except pymysql.MySQLError as e:
            print(f"数据库连接失败: {e}")
            return None
        except Exception as e:
            print(f"发生未知错误: {e}")
            return None

    def is_connected(self) -> bool:
        """
        检查当前是否已成功连接到数据库。

        Returns:
            bool: 如果连接有效则返回 True，否则返回 False。
        """
        return self.connection is not None

    def close(self):
        """
        关闭数据库连接。
        """
        if self.connection:
            try:
                self.connection.close()
                print("数据库连接已关闭。")
                self.connection = None
            except pymysql.MySQLError as e:
                print(f"关闭连接时发生错误: {e}")

    def insert_batch(self, data_list: List[Dict[str, Any]], table_name: str) -> bool:
        """
        将数据字典列表批量插入到数据库表中。

        Args:
            data_list (List[Dict[str, Any]]): 字典列表，每个字典代表一行数据。
            table_name (str): 目标数据库表的名称。

        Returns:
            bool: 成功返回True，否则返回False。
        """
        if not self.is_connected():
            print("错误：数据库未连接，无法执行插入操作。")
            return False
        if not data_list:
            print("数据列表为空，无需插入。")
            return True

        columns = list(data_list[0].keys())
        sql = f"INSERT INTO `{table_name}` ({', '.join(f'`{col}`' for col in columns)}) VALUES ({', '.join(['%s'] * len(columns))})"
        values = [tuple(data.get(col) for col in columns) for data in data_list]

        try:
            with self.connection.cursor() as cursor:
                affected_rows = cursor.executemany(sql, values)
            self.connection.commit()
            print(f"成功批量插入 {affected_rows} 条数据到表 '{table_name}'。")
            return True
        except pymysql.MySQLError as e:
            print(f"批量插入失败: {e}")
            self.connection.rollback()
            return False

    def upsert_batch(self, data_list: List[Dict[str, Any]], table_name: str) -> bool:
        """
        将数据字典列表批量插入或更新到数据库中 (Upsert)。
        使用 INSERT ... ON DUPLICATE KEY UPDATE 实现。

        Args:
            data_list (List[Dict[str, Any]]): 字典列表，每个字典代表一行数据。
            table_name (str): 目标数据库表的名称。

        Returns:
            bool: 成功返回True，否则返回False。
        """
        if not self.is_connected():
            print("错误：数据库未连接，无法执行更新/插入操作。")
            return False
        if not data_list:
            print("数据列表为空，无需插入或更新。")
            return True

        columns = list(data_list[0].keys())
        update_columns = [col for col in columns if col.lower() not in ['id', 'create_time']]

        sql = f"""
            INSERT INTO `{table_name}` ({', '.join(f'`{col}`' for col in columns)})
            VALUES ({', '.join(['%s'] * len(columns))})
            ON DUPLICATE KEY UPDATE
            {', '.join(f'`{col}` = VALUES(`{col}`)' for col in update_columns)}
        """
        values = [tuple(data.get(col) for col in columns) for data in data_list]

        try:
            with self.connection.cursor() as cursor:
                affected_rows = cursor.executemany(sql, values)
            self.connection.commit()
            print(f"成功批量插入/更新 {affected_rows} 条数据到表 '{table_name}'。")
            return True
        except pymysql.MySQLError as e:
            print(f"批量插入/更新失败: {e}")
            self.connection.rollback()
            return False

    def __enter__(self):
        """
        上下文管理器入口方法。
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口方法，自动关闭连接。
        """
        self.close()

