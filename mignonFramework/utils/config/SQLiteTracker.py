import os
import sqlite3
import sys
import threading
from typing import Any, List, Type, TypeVar, Generic, get_origin, get_args, Callable, Union, Optional

T = TypeVar('T')

# --- 装饰器定义 ---

def TableId(key_name: str):
    """
    类装饰器: 指定该类映射到数据库表时的主键字段。
    """
    def decorator(cls: Type[T]) -> Type[T]:
        setattr(cls, '_table_id', key_name)
        return cls
    return decorator

def VarChar(arg1: Union[str, int], arg2: Optional[int] = None):
    """
    【全新升级】类装饰器工厂: 为 str 字段设置 VARCHAR 长度。

    用法 1 (默认长度):
        @VarChar(100) # 本类所有 str 字段默认为 VARCHAR(100)
        class User: ...

    用法 2 (特定长度):
        @VarChar("email", 200) # email 字段指定为 VARCHAR(200)
        class User: ...
    """
    def decorator(cls: Type[T]) -> Type[T]:
        if isinstance(arg1, int) and arg2 is None:
            setattr(cls, '_varchar_default_length', arg1)
        elif isinstance(arg1, str) and isinstance(arg2, int):
            if not hasattr(cls, '_varchar_fields'):
                setattr(cls, '_varchar_fields', {})
            cls._varchar_fields[arg1] = arg2
        else:
            raise TypeError("Invalid arguments for @VarChar. Use @VarChar(length) or @VarChar(field_name, length).")
        return cls
    return decorator

# --- 核心实现 ---

class _SQLiteItemProxy:
    """
    代理从数据库表中取出的单个对象（行）。
    """
    def __init__(self, list_proxy: '_SQLiteProxyList', item_data: sqlite3.Row):
        object.__setattr__(self, "_list_proxy", list_proxy)
        object.__setattr__(self, "_data", dict(item_data))
        object.__setattr__(self, "_id_column", list_proxy._id_column)
        object.__setattr__(self, "_primary_key", item_data[list_proxy._id_column])

    def __getattr__(self, name: str):
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any):
        self._data[name] = value
        sql = f"UPDATE \"{self._list_proxy._table_name}\" SET \"{name}\" = ? WHERE \"{self._id_column}\" = ?"
        with self._list_proxy._conn:
            cur = self._list_proxy._conn.cursor()
            cur.execute(sql, (value, self._primary_key))

    def delete(self):
        """
        删除数据库中与此对象对应的行。
        """
        self._list_proxy.remove(self._primary_key)
        object.__setattr__(self, "_data", {})

    def __repr__(self) -> str:
        return f"<SQLiteItemProxy data={self._data}>"


class _SQLiteProxyList(Generic[T]):
    """
    代理一个 List[CustomClass] 类型，将其所有操作直接映射到数据库表。
    """
    def __init__(self, tracker: 'SQLiteTracker', table_name: str, item_cls: Type[T]):
        self._conn = tracker._conn
        self._table_name = table_name
        self._item_cls = item_cls
        self._id_column = getattr(item_cls, '_table_id', None)
        if not self._id_column:
            raise TypeError(f"Class '{item_cls.__name__}' used in a List must be decorated with @TableId.")
        self._fields = list(getattr(item_cls, '__annotations__', {}).keys())

    def _item_to_tuple(self, item: T) -> tuple:
        return tuple(getattr(item, field) for field in self._fields)

    def _row_to_proxy(self, row: sqlite3.Row) -> _SQLiteItemProxy:
        return _SQLiteItemProxy(self, row)

    def append(self, item: T):
        if not isinstance(item, self._item_cls):
            raise TypeError(f"Can only append instances of '{self._item_cls.__name__}'")

        placeholders = ', '.join(['?'] * len(self._fields))
        safe_fields = ", ".join(f'"{field}"' for field in self._fields)
        sql = f"INSERT OR REPLACE INTO \"{self._table_name}\" ({safe_fields}) VALUES ({placeholders})"

        with self._conn:
            cur = self._conn.cursor()
            cur.execute(sql, self._item_to_tuple(item))

    def find(self, key_value: Any) -> T | None:
        sql = f"SELECT * FROM \"{self._table_name}\" WHERE \"{self._id_column}\" = ?"
        cur = self._conn.cursor()
        cur.execute(sql, (key_value,))
        row = cur.fetchone()
        return self._row_to_proxy(row) if row else None

    def remove(self, item: Union[T, Any]):
        if isinstance(item, _SQLiteItemProxy):
            key_value = item._primary_key
        elif isinstance(item, self._item_cls):
            key_value = getattr(item, self._id_column)
        else:
            key_value = item

        sql = f"DELETE FROM \"{self._table_name}\" WHERE \"{self._id_column}\" = ?"
        with self._conn:
            cur = self._conn.cursor()
            cur.execute(sql, (key_value,))

    def keys(self) -> list:
        sql = f"SELECT \"{self._id_column}\" FROM \"{self._table_name}\""
        cur = self._conn.cursor()
        cur.execute(sql)
        return [row[0] for row in cur.fetchall()]

    def __iter__(self):
        sql = f"SELECT * FROM \"{self._table_name}\""
        cur = self._conn.cursor()
        cur.execute(sql)
        for row in cur.fetchall():
            yield self._row_to_proxy(row)

    def __len__(self) -> int:
        sql = f"SELECT COUNT(*) FROM \"{self._table_name}\""
        cur = self._conn.cursor()
        cur.execute(sql)
        return cur.fetchone()[0]

    def __getitem__(self, key: Union[int, slice]) -> Union[T, List[T]]:
        """
        【全新升级】支持整数索引和切片语法，并保证按插入顺序返回。
        """
        # 获取当前列表的总长度
        length = self.__len__()

        if isinstance(key, int):
            # 处理整数索引 (e.g., my_list[3] or my_list[-1])
            if key < 0:
                key += length
            # 边界检查
            if not (0 <= key < length):
                raise IndexError("List index out of range.")

            # 使用 OFFSET 获取特定行，ORDER BY ROWID 保证顺序
            sql = f"SELECT * FROM \"{self._table_name}\" ORDER BY ROWID ASC LIMIT 1 OFFSET ?"
            cur = self._conn.cursor()
            cur.execute(sql, (key,))
            row = cur.fetchone()
            if row:
                return self._row_to_proxy(row)
            else:
                # 理论上，前面的长度检查后不应该发生，但作为保障
                raise IndexError("List index out of range.")

        elif isinstance(key, slice):
            # 处理切片 (e.g., my_list[-10:], my_list[1:5], my_list[::-1])
            # slice.indices 会将负数索引、None 等转换为明确的 start, stop, step
            # 这也优雅地处理了您提到的 [-10:] 在列表总数不足10时的情况
            start, stop, step = key.indices(length)

            if step > 0:
                # 正向切片
                query_offset = start
                query_limit = stop - start
            else: # step < 0
                # 反向切片，我们仍然正向获取所需的最小数据块，然后在内存中反转
                # 所需的数据范围是从 stop + 1 到 start
                query_offset = stop + 1
                query_limit = start - (stop + 1) + 1

            # 如果计算出的范围为空，直接返回空列表
            if query_limit <= 0:
                return []

            # 明确使用 ORDER BY ROWID ASC 来保证插入顺序
            sql = f"SELECT * FROM \"{self._table_name}\" ORDER BY ROWID ASC LIMIT ? OFFSET ?"
            cur = self._conn.cursor()
            cur.execute(sql, (query_limit, query_offset))

            rows = cur.fetchall()
            proxies = [self._row_to_proxy(row) for row in rows]

            # 在内存中应用反向和步长
            # 如果 step < 0, 我们需要反转从数据库中顺序取出的结果
            if step < 0:
                proxies.reverse()

            # 最后，应用步长。
            # 对于正向切片，是 proxies[::step]
            # 对于反向，因为已经 reverse() 过了，所以用 proxies[::abs(step)]
            return proxies[::abs(step)]
        else:
            raise TypeError("List indices must be integers or slices.")

    def __repr__(self) -> str:
        # 修正 __repr__ 以避免在打印对象时触发新的数据库查询和潜在的递归
        return f"<SQLiteProxyList table='{self._table_name}'>"

class _SQLiteProxyObject:
    """
    代理顶层配置对象。
    """
    def __init__(self, tracker: 'SQLiteTracker', cls: Type):
        object.__setattr__(self, "_tracker", tracker)
        object.__setattr__(self, "_cls", cls)
        object.__setattr__(self, "_annotations", getattr(cls, '__annotations__', {}))

    def __getattr__(self, name: str):
        type_hint = self._annotations.get(name)
        if not type_hint:
            return None
        origin = get_origin(type_hint)
        if origin in (list, List):
            item_cls = get_args(type_hint)[0]
            table_name = f"{self._cls.__name__}_{name}"
            return _SQLiteProxyList(self._tracker, table_name, item_cls)
        return self._tracker._get_main_config_value(name)

    def __setattr__(self, name: str, value: Any):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return
        type_hint = self._annotations.get(name)
        if get_origin(type_hint) in (list, List):
            raise AttributeError(f"Cannot assign to a proxied list '{name}'. Use methods like .append() or .remove().")
        self._tracker._set_main_config_value(name, value)


class SQLiteTracker:
    """
    主追踪器类，负责数据库连接和模式同步。
    """
    def __init__(self, db_path: str = "./resources/dbs/tracker.db"):
        self._lock = threading.RLock()
        self._db_path = self._resolve_db_path(db_path)
        self._conn = None
        self._connect()

    def _connect(self):
        with self._lock:
            dir_name = os.path.dirname(self._db_path)
            if dir_name: os.makedirs(dir_name, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("""
                               CREATE TABLE IF NOT EXISTS main_config (
                                                                          key TEXT PRIMARY KEY,
                                                                          value TEXT,
                                                                          type TEXT
                               )
                               """)
            self._conn.commit()

    def _map_type_to_sql(self, type_hint: Any) -> str:
        """将 Python 基本类型提示转换为 SQLite 数据类型"""
        if type_hint is int: return "INTEGER"
        if type_hint is float: return "REAL"
        if type_hint is bool: return "INTEGER"
        if type_hint is str: return "TEXT"
        return "TEXT"

    def _sync_schema(self, cls: Type):
        with self._lock, self._conn:
            cur = self._conn.cursor()
            annotations = getattr(cls, '__annotations__', {})
            for name, type_hint in annotations.items():
                origin = get_origin(type_hint)
                if origin in (list, List):
                    item_cls = get_args(type_hint)[0]
                    table_name = f"{cls.__name__}_{name}"
                    self._create_or_update_table_for_class(cur, table_name, item_cls)

    def _create_or_update_table_for_class(self, cur: sqlite3.Cursor, table_name: str, item_cls: Type):
        # 1. 根据 Python 类定义，构建期望的 schema
        item_annotations = getattr(item_cls, '__annotations__', {})
        id_column = getattr(item_cls, '_table_id', None)
        varchar_fields = getattr(item_cls, '_varchar_fields', {})
        default_varchar_len = getattr(item_cls, '_varchar_default_length', None)

        desired_schema = {}
        for field, type_hint in item_annotations.items():
            if field in varchar_fields:
                sql_type = f"VARCHAR({varchar_fields[field]})"
            elif type_hint is str and default_varchar_len:
                sql_type = f"VARCHAR({default_varchar_len})"
            else:
                sql_type = self._map_type_to_sql(type_hint)
            desired_schema[field] = sql_type

        # 2. 检查表是否存在
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        table_exists = cur.fetchone() is not None

        if not table_exists:
            # 3a. 如果不存在，直接创建
            cols_defs = [f'"{field}" {sql_type}' + (" PRIMARY KEY" if field == id_column else "") for field, sql_type in desired_schema.items()]
            create_sql = f"CREATE TABLE \"{table_name}\" ({', '.join(cols_defs)})"
            cur.execute(create_sql)
            return

        # 3b. 如果存在，获取现有 schema 并比较
        cur.execute(f'PRAGMA table_info("{table_name}")')
        existing_schema = {row['name']: row['type'].upper() for row in cur.fetchall()}

        # 规范化期望的 schema 以进行比较
        normalized_desired = {k: v.upper().replace(" ", "") for k, v in desired_schema.items()}

        if normalized_desired == existing_schema:
            return # Schema 一致，无需操作

        temp_table = f"_{table_name}_temp_migration"

        # a. 重命名旧表
        cur.execute(f'ALTER TABLE "{table_name}" RENAME TO "{temp_table}"')

        # b. 用新 schema 创建表
        cols_defs = [f'"{field}" {sql_type}' + (" PRIMARY KEY" if field == id_column else "") for field, sql_type in desired_schema.items()]
        create_sql = f"CREATE TABLE \"{table_name}\" ({', '.join(cols_defs)})"
        cur.execute(create_sql)

        # c. 找出新旧表共有的字段，以复制数据
        common_cols = set(existing_schema.keys()) & set(desired_schema.keys())
        if common_cols:
            safe_common_cols = ", ".join(f'"{col}"' for col in common_cols)
            # d. 从临时表复制数据到新表
            insert_sql = f'INSERT INTO "{table_name}" ({safe_common_cols}) SELECT {safe_common_cols} FROM "{temp_table}"'
            cur.execute(insert_sql)

        # e. 删除临时表
        cur.execute(f'DROP TABLE "{temp_table}"')


    def _get_main_config_value(self, key: str) -> Any:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT value, type FROM main_config WHERE key = ?", (key,))
            row = cur.fetchone()
            if not row: return None
            value_str, type_str = row['value'], row['type']
            if type_str == 'int': return int(value_str)
            if type_str == 'float': return float(value_str)
            if type_str == 'bool': return value_str == 'True'
            return value_str

    def _set_main_config_value(self, key: str, value: Any):
        value_type = type(value).__name__
        value_str = str(value)
        sql = "INSERT OR REPLACE INTO main_config (key, value, type) VALUES (?, ?, ?)"
        with self._lock, self._conn:
            self._conn.execute(sql, (key, value_str, value_type))

    def getInstance(self, cls: Type[T]) -> T:
        with self._lock:
            self._sync_schema(cls)
            return _SQLiteProxyObject(self, cls)

    def _resolve_db_path(self, filename: str) -> str:
        if os.path.isabs(filename):
            return filename
        return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), filename)

def injectSQLite(manager: SQLiteTracker):
    """
    装饰器工厂: 将一个类转换为 SQLite 支持的配置对象的"工厂"。
    """
    def decorator(cls: Type[T]) -> Callable[..., T]:
        def factory(*args, **kwargs) -> T:
            return manager.getInstance(cls)
        return factory
    return decorator

