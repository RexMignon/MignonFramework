"""
MysqlManager: 一个健壮的 MySQL 数据库管理器。它封装了数据库的连接、关闭、以及高效的批量“更新或插入”（Upsert）操作，
并通过上下文管理器（with语句）简化了资源管理，确保连接的自动关闭。
"""
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
        """
        try:
            connection = pymysql.connect(**self.db_config)
            # print("数据库连接成功！") # 在框架中通常静默处理
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
        """
        return self.connection is not None

    def close(self):
        """
        关闭数据库连接。
        """
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
            except pymysql.MySQLError as e:
                print(f"关闭连接时发生错误: {e}")
                raise e

    def upsert_batch(self, data_list: List[Dict[str, Any]], table_name: str, test: bool = False) -> bool:
        """
        将数据字典列表批量插入或更新到数据库中 (Upsert)。
        这是 BaseWriter 接口的实现。
        """
        if not self.is_connected():
            print("错误：数据库未连接，无法执行更新/插入操作。")
            return False
        if not data_list:
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
                cursor.executemany(sql, values)

            # 关键：在测试模式下，不提交事务
            if not test:
                self.connection.commit()

            return True
        except pymysql.MySQLError as e:
            # 即使在测试模式下，也回滚以清理事务状态
            self.connection.rollback()
            # 重新抛出异常，以便上层（GenericFileProcessor）可以捕获并进行智能分析
            raise e

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
