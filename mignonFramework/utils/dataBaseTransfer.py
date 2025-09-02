"""
cn:
这个dataBase转移组件是用来迁移数据库, 自定义接口并批量迁移,
接口作用仅定义insert和select, 因为需要迁移至目标数据库, 所以需要通过"游标分页"记录上一次的
最末尾的id 通过 id > 来查询, 大大提高查询效率, 并且需要读取目标数据库的表信息,
用来初始化来排除不需要导入的表, 届时跟starter和GenericProcessor类似, 提供可视化模式一键配置
生成exclude_list,导入即可, 同时提供断点续传的功能. 首先insert和select需要原子性, 当且仅当完成后insert再
进行设置末尾id,设计结构如下:
{
    "needToTransferredDataBase":"",
    "userName":"",
    "password":"",
    "host":"",
    "port":"",
    "targetDataBase":"",
    "targetUserName":"",
    "targetPassword":"",
    "targetHost":"",
    "targetPort":"",
    "excludeList":["这里是数据表名,表示被排除"],
    "alreadyFinished":["这里是已完成的表名"],
    "nowTitle":"当前的表名",
    "nowLastId": 1,
    "isInclude":false,
    "includeList"["假设isInclude为True, includeList生效, 假设为False,excludeList生效"]
}
使用JsonConfigManager进行线程安全地读取json以及写入, DI, 并且, 如果使用run()函数启动时,
如果JsonConfigManager不填就默认生成.在工作目录下的./resources/config/dataBaseTransfer.json
并且自动生成json结构并提示填写, 可以指定实现DatabaseTransfer.py的类来实现可插拔的.
默认实现是MySQL的形式.
初次开始时应当默认为id>0,当insert事务成功提交后再设置id
参照BaseWriter批量写入批量读取, 并参照MySQLManager进行重连机制
因为是直接通过DDL copy的表, 因此不需要处理报错, 仅需拿到表名->拿到DDL->运行if not exists 直接覆盖
即可, 因为本模块的目标是迁移, 而不是说干涉转移事件, 仅需处理的只有完整的表迁移.
目前来说限制了非id的迁移, 虽说的确有解决办法, 如降级为offset传统分页,或者创建view等等有相当多的方法
来做到跨越Id的问题, 但是我认为一个没有id的表实际上来说, 并非规范的表, 目的是促进规范
En:
This dataBase migration component is used to migrate databases, customize the interface, and perform batch migrations.
The interface only defines insert and select operations. Because the migration is to the target database, cursor paging is used to record the last id. This is then queried using id > to greatly improve query efficiency. It also requires reading the target database's table information.
This component is used to initialize and exclude tables that do not need to be imported. Similar to the starter and GenericProcessor, it provides visual one-click configuration. Generate an exclude list, then simply import. It also provides resumable downloads. Inserts and selects must be atomic. The last id is set only after the insert is complete. The design structure is as follows:
{
"needToTransferredDataBase":"",
"userName":"",
"password":"",
"host":"",
"port":"",
"targetDataBase":"",
"targetUserName":"",
"targetPassword":"",
"targetHost":"",
"targetPort":"",
"excludeList": ["Here is the table name to exclude"],
"alreadyFinished": ["Here is the completed table name"],
"nowTitle": "Current table name",
"nowLastId": 1,
"isInclude": false,
"includeList" ["If isInclude is True, includeList is in effect; if it is False, excludeList is in effect"]
}
Use JsonConfigManager for thread-safe JSON reading and writing. DI. When starting with the run() function,
If JsonConfigManager is not specified, a default is generated. ./resources/config/dataBaseTransfer.json is in the working directory.
The JSON structure is automatically generated and prompted for. You can specify a class implementing DatabaseTransfer.py to achieve pluggability.
The default implementation is MySQL-style.
When initially started, the default id should be > 0. The id is then set after the insert transaction successfully commits.
Refer to BaseWriter for batch writing and reading, and refer to MySQLManager for the reconnection mechanism.
Because it is directly implemented via DDL Since the table is copied, there's no need to handle errors. Simply get the table name, get the DDL, and run an if not exists command to overwrite the table.
This module focuses on migration, not on intervening in transfers. It only handles complete table migrations.
"""

import sys
import os
import json
from abc import ABC, abstractmethod
from typing import List, Optional, Type, Dict
from datetime import date, datetime
from collections import defaultdict


try:
    from mignonFramework.utils.config.JsonlConfigReader import JsonConfigManager
    from mignonFramework.utils.writer.MySQLManager import MysqlManager
except ImportError:
    sys.exit(1)


try:
    from flask import Flask, render_template_string, request, jsonify, send_from_directory
except ImportError:
    Flask = None


# --- 1. 配置模型定义 ---
# 定义与 JSON 结构严格对应的配置类
class TransferConfig:
    needToTransferredDataBase: str
    userName: str
    password: str
    host: str
    port: int
    targetDataBase: str
    targetUserName: str
    targetPassword: str
    targetHost: str
    targetPort: int
    excludeList: List[str]
    alreadyFinished: List[str]
    nowTitle: str
    nowLastId: int
    isInclude: bool
    includeList: List[str]
    batchSize: int = 1000  # 默认的批量大小
    autoSkipError: bool = False # 新增：是否自动跳过错误行

# --- 2. 抽象的数据库迁移基类 ---
class AbstractDatabaseTransfer(ABC):
    """
    定义数据库迁移器的抽象基类 (ABC)。
    所有具体的迁移实现（如MySQL->MySQL, PG->MySQL等）都应继承此类。
    这确保了“可插拔”的特性。
    """
    def __init__(self, config: TransferConfig):
        self.config = config
        self.source_db = None
        self.target_db = None
        # 初始化一个缓存，用于存储已查询过的表的生成列信息
        self._generated_columns_cache = {}
        print(f"正在初始化迁移配置, 源数据库: {config.needToTransferredDataBase}")

    @abstractmethod
    def connect_dbs(self):
        """建立到源和目标数据库的连接。"""
        pass

    @abstractmethod
    def close_dbs(self):
        """关闭所有数据库连接/资源。"""
        pass

    @abstractmethod
    def get_all_tables(self) -> List[str]:
        """从源数据库获取所有表的名称。"""
        pass

    @abstractmethod
    def get_max_id(self, table_name: str) -> int:
        """获取源数据库中指定表的最大ID。"""
        pass

    @abstractmethod
    def get_table_ddl(self, table_name: str) -> str:
        """获取指定表的 CREATE TABLE DDL 语句。"""
        pass

    @abstractmethod
    def get_table_dependencies(self, db_name: str) -> Dict[str, List[str]]:
        """
        获取指定数据库中所有表的外键依赖关系。
        返回一个字典，键为表名，值为该表依赖的其他表名列表。
        例如: {'table_a': ['table_b', 'table_c']}
        """
        pass

    @abstractmethod
    def create_table_in_target(self, ddl: str):
        """在目标数据库中执行 DDL 创建表。"""
        pass

    @abstractmethod
    def transfer_table_data(self, table_name: str):
        """迁移单个表的数据，并处理断点续传。"""
        pass

    def _filter_tables(self, all_tables: List[str]) -> List[str]:
        """
        根据配置的包含/排除列表过滤需要迁移的表。
        这是通用逻辑，可以在基类中实现。
        """
        if self.config.isInclude:
            filtered = [
                tbl for tbl in all_tables
                if tbl in self.config.includeList and tbl not in self.config.alreadyFinished
            ]
            print(f"包含模式: 根据 includeList 发现 {len(filtered)} 个表需要迁移。")
            return filtered
        else:
            finished_set = set(self.config.alreadyFinished)
            exclude_set = set(self.config.excludeList)
            filtered = [
                tbl for tbl in all_tables
                if tbl not in finished_set and tbl not in exclude_set
            ]
            print(f"排除模式: 应用排除规则后发现 {len(filtered)} 个表需要迁移。")
            return filtered

    def run(self):
        """
        启动数据库迁移的完整流程模板。
        这是一个模板方法，定义了迁移的骨架。
        """
        try:
            self.connect_dbs()
            all_tables = self.get_all_tables()

            # --- 新增: 获取依赖并排序 ---
            print("正在解析数据库表依赖关系...")
            dependencies = self.get_table_dependencies(self.config.needToTransferredDataBase)
            tables_to_transfer = self._filter_tables(all_tables)
            sorted_tables = self._sort_tables_by_dependencies(tables_to_transfer, dependencies)

            if not sorted_tables:
                print("所有表都已迁移或被排除，任务完成。")
                return

            print("已按照依赖关系对迁移顺序进行排序：")
            print(" -> ".join(sorted_tables))

            for table in sorted_tables:
                print("\n" + "-" * 60)
                print(f"正在处理表: {table}")

                ddl = self.get_table_ddl(table)
                self.create_table_in_target(ddl)
                print(f"  - 表结构 '{table}' 已在目标数据库中确认。")

                self.transfer_table_data(table)

                self.config.alreadyFinished.append(table)
                self.config.nowTitle = ""
                self.config.nowLastId = 0
                print(f"\n  - 表 '{table}' 迁移完成并已标记。")

            print("\n" + "=" * 60)
            print("数据库迁移过程已成功完成！")

        except Exception as e:
            print(f"\n[致命错误] 迁移过程中发生异常: {e}")
            print("程序已停止，请检查配置和日志。")
            print(f"最后记录状态: 表='{self.config.nowTitle}', LastID={self.config.nowLastId}")
        finally:
            self.close_dbs()

    def _sort_tables_by_dependencies(self, tables: List[str], dependencies: Dict[str, List[str]]) -> List[str]:
        """
        使用拓扑排序对表进行排序。
        如果存在循环依赖或无法排序，则打印警告并返回原始列表。
        """
        graph = {table: [] for table in tables}
        in_degree = {table: 0 for table in tables}

        # 构建图和入度
        for table in tables:
            if table in dependencies:
                for parent_table in dependencies[table]:
                    if parent_table in graph:
                        graph[parent_table].append(table)
                        in_degree[table] += 1

        queue = [table for table in tables if in_degree[table] == 0]
        sorted_list = []

        while queue:
            node = queue.pop(0)
            sorted_list.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_list) != len(tables):
            print("\n[警告] 无法按照依赖关系对所有表进行排序，可能存在循环依赖或遗漏的表。")
            print("将按照原始顺序继续迁移。")
            return tables

        return sorted_list


# --- 3. 针对 MySQL 的具体迁移实现 ---
class MySQLToMySQLTransfer(AbstractDatabaseTransfer):
    """
    针对 MySQL -> MySQL 迁移的具体实现。
    """
    def connect_dbs(self):
        """使用 MySQLManager 连接池来建立连接。"""
        print("正在使用 MySQLManager 连接到源数据库...")
        self.source_db = MysqlManager(
            host=self.config.host, user=self.config.userName, password=self.config.password,
            database=self.config.needToTransferredDataBase, port=self.config.port
        )
        print("正在使用 MySQLManager 连接到目标数据库...")
        self.target_db = MysqlManager(
            host=self.config.targetHost, user=self.config.targetUserName, password=self.config.targetPassword,
            database=self.config.targetDataBase, port=self.config.targetPort
        )

    def close_dbs(self):
        """关闭 MySQLManager 的连接池。"""
        if self.source_db:
            (self.source_db.close_pool if hasattr(self.source_db, 'pool') else self.source_db.close)()
        if self.target_db:
            (self.target_db.close_pool if hasattr(self.target_db, 'pool') else self.target_db.close)()

    def get_all_tables(self) -> List[str]:
        print("正在从源 MySQL 数据库获取所有表名...")
        tables_dicts= None
        if hasattr(self.source_db, 'pool'):
            tables_dicts = self.source_db.fetch_all("SHOW TABLES;")
        else:
            with self.source_db.connection.cursor() as cursor:
                cursor.execute("SHOW TABLES;")
                tables_dicts = cursor.fetchall()
        return [list(row.values())[0] for row in tables_dicts]

    def get_max_id(self, table_name: str) -> int:
        query = f"SELECT MAX(id) as max_id FROM `{table_name}`;"
        result = ""
        if hasattr(self.source_db, 'pool'):
            result = self.source_db.fetch_one(query)
        else:
            with self.source_db.connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
        return result['max_id'] if result and result['max_id'] is not None else 0

    def get_table_ddl(self, table_name: str) -> str:
        query = f"SHOW CREATE TABLE `{table_name}`;"
        result = None
        if hasattr(self.source_db, 'pool'):
            result = self.source_db.fetch_one(query)
        else:
            with self.source_db.connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
        return result['Create Table']

    def get_table_dependencies(self, db_name: str) -> Dict[str, List[str]]:
        query = """
                SELECT
                    TABLE_NAME,
                    REFERENCED_TABLE_NAME
                FROM
                    INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE
                    TABLE_SCHEMA = %s AND
                    REFERENCED_TABLE_NAME IS NOT NULL;
                """
        dependencies = defaultdict(list)
        results = None
        if hasattr(self.source_db, 'pool'):
            results = self.source_db.fetch_all(query, (db_name,))
        else:
            with self.source_db.connection.cursor() as cursor:
                cursor.execute(query, (db_name,))
                results = cursor.fetchall()

        for row in results:
            dependencies[row['TABLE_NAME']].append(row['REFERENCED_TABLE_NAME'])

        return dict(dependencies)


    def create_table_in_target(self, ddl: str):
        ddl_if_not_exists = ddl.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1)
        if hasattr(self.target_db, 'pool'):
            self.target_db.execute(ddl_if_not_exists, commit=True)
        else:
            with self.target_db.connection.cursor() as cursor:
                cursor.execute(ddl_if_not_exists)
            self.target_db.connection.commit()

    def _clean_zero_dates(self, row_data: dict) -> dict:
        """
        一个内部辅助方法，用于将字典中的无效日期/时间字符串替换为 None。
        """
        for key, value in row_data.items():
            if isinstance(value, (date, datetime)):
                if value.year < 1000: # MySQL DATE/DATETIME 有效年份从 1000 开始
                    row_data[key] = None
            elif isinstance(value, str) and value.startswith('0000-00-00'):
                row_data[key] = None
        return row_data

    def _get_generated_columns(self, db_manager: MysqlManager, db_name: str, table_name: str) -> list:
        """
        查询数据库元数据，获取指定表的所有生成列 (Generated Columns)。
        使用缓存避免对同一个表重复执行查询。
        """
        cache_key = f"{db_name}.{table_name}"
        if cache_key in self._generated_columns_cache:
            return self._generated_columns_cache[cache_key]

        query = """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = %s
                  AND EXTRA LIKE '%%GENERATED%%' \
                """
        params = (db_name, table_name)

        try:
            results = None
            if hasattr(db_manager, 'pool'):
                results = db_manager.fetch_all(query, params)
            else:
                with db_manager.connection.cursor() as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()

            generated_cols = [list(row.values())[0] for row in results]
            self._generated_columns_cache[cache_key] = generated_cols
            return generated_cols
        except Exception as e:
            print(f"\n[警告] 无法获取表 '{table_name}' 的生成列信息。错误: {e}")
            return []

    def transfer_table_data(self, table_name: str):
        self.config.nowTitle = table_name
        try:
            max_id = int(self.get_max_id(table_name) or 0)
        except (TypeError, ValueError) as e:
            print(f"\n[致命错误] 获取表 '{table_name}' 的最大ID失败。错误: {e}")
            print("  - 确保该表有可转换为整数的 'id' 列，且数据类型正确。")
            raise e

        if max_id == 0:
            print(f"  - 表 '{table_name}' 为空或没有 'id' 列，跳过数据迁移。")
            return

        print(f"  - 表 '{table_name}' 最大ID为: {max_id}。开始数据迁移...")

        last_id = self.config.nowLastId
        if last_id > 0:
            print(f"  - 从上次断点恢复, last ID: {last_id}")

        generated_columns = self._get_generated_columns(self.target_db, self.config.targetDataBase, table_name)
        if generated_columns:
            print(f"  [信息] 表 '{table_name}' 包含以下生成列，将从插入数据中自动排除: {', '.join(generated_columns)}")

        while last_id < max_id:
            query = f"SELECT * FROM `{table_name}` WHERE id > %s ORDER BY id ASC LIMIT %s;"
            params = (last_id, self.config.batchSize)

            data_batch = None
            if hasattr(self.source_db, 'pool'):
                data_batch = self.source_db.fetch_all(query, params)
            else:
                with self.source_db.connection.cursor() as cursor:
                    cursor.execute(query, params)
                    data_batch = cursor.fetchall()

            if not data_batch:
                bar = '█' * 40
                sys.stdout.write(f'\r|{bar}| 100.0% ({max_id}/{max_id})  本批: [0]')
                sys.stdout.flush()
                break

            cleaned_data_batch = [self._clean_zero_dates(row) for row in data_batch]

            final_data_batch = []
            if generated_columns:
                for row in cleaned_data_batch:
                    row_copy = row.copy()
                    for col in generated_columns:
                        if col in row_copy:
                            if col in row_copy:
                                del row_copy[col]
                    final_data_batch.append(row_copy)
            else:
                final_data_batch = cleaned_data_batch

            try:
                self.target_db.upsert_batch(data_list=final_data_batch, table_name=table_name)
            except Exception as batch_exception:
                print(f"\n[警告] 批量写入失败 (表: {table_name})。错误: {batch_exception}")
                print("--- 即将进入逐行恢复模式 ---")

                for row_data in final_data_batch:
                    try:
                        self.target_db.upsert_single(row_data, table_name)
                    except Exception as single_exception:
                        row_id = row_data.get('id', 'N/A')
                        print("\n" + "=" * 80)
                        print(f"[错误] 定位到错误行!\n  - 表名: {table_name}\n  - ID: {row_id}\n  - 错误: {single_exception}\n  - 数据: {row_data}")
                        print("=" * 80)

                        if self.config.autoSkipError:
                            print(f"  [信息] 配置了自动跳过，已跳过此行。")
                            continue

                        choice = input("输入 'y' 跳过此行，'s' 跳过本批次剩余所有行，其他任意键将终止程序: ").lower()
                        if choice == 'y':
                            print(f"  [信息] 已跳过此行。")
                            continue
                        elif choice == 's':
                            print(f"  [信息] 已跳过批次中剩余的所有行。")
                            break
                        else:
                            print("  [致命] 用户选择终止程序。")
                            raise single_exception
                print("--- 逐行恢复模式结束 ---")

            last_id_in_batch = data_batch[-1]['id']
            last_id = last_id_in_batch
            self.config.nowLastId = last_id

            percentage = min(1.0, last_id / max_id)
            bar = '█' * int(40 * percentage) + '-' * (40 - int(40 * percentage))
            sys.stdout.write(f'\r|{bar}| {percentage:.1%} ({last_id}/{max_id})  本批: [{len(data_batch)}]')
            sys.stdout.flush()

# --- 4. Eazy Mode Web 应用 ---
class TransferEazyAppRunner:

    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>mignonFramework - 数据库迁移 Eazy Mode</title>
        <style>
            :root { --bg-color: #f4f5f7; --card-bg: #fff; --text-color: #172b4d; --primary: #0052cc; --primary-hover: #0041a3; --border: #dfe1e6; --success: #00875a; --danger: #de350b; --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
            body { font-family: var(--font); background-color: var(--bg-color); margin: 0; padding: 2rem; color: var(--text-color); display: flex; justify-content: center; }
            .container { max-width: 1200px; width: 100%; }
            .header { text-align: center; margin-bottom: 2rem; }
            .header pre { font-family: monospace; color: #505f79; white-space: pre; line-height: 1.2; font-size: 0.9rem; display: inline-block; text-align: left;}
            .card { background: var(--card-bg); border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 2rem; }
            .card-header { padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); font-size: 1.2rem; font-weight: 600; display:flex; align-items:center; gap: 0.5rem;}
            .card-body { padding: 1.5rem; }
            .form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; }
            .form-group { display: flex; flex-direction: column; }
            label { margin-bottom: 0.5rem; font-weight: 500; }
            .form-control { padding: 0.75rem; border: 1px solid var(--border); border-radius: 4px; transition: all 0.2s; }
            .form-control:focus { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(0, 82, 204, 0.2); outline: none; }
            .btn { padding: 0.75rem 1.5rem; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; transition: all 0.2s; display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem; min-width: 120px;}
            .btn.is-loading { cursor: not-allowed; }
            .btn.is-loading::before { content: ''; border: 2px solid rgba(255,255,255,0.5); border-top-color: #fff; border-radius: 50%; width: 1em; height: 1em; animation: spin 0.8s linear infinite; }
            .btn.is-success { background-color: var(--success); color: #fff; }
            .btn.is-danger { background-color: var(--danger); color: #fff; }
            @keyframes spin { to { transform: rotate(360deg); } }
            .btn-primary { background-color: var(--primary); color: #fff; }
            .btn-primary:hover { background-color: var(--primary-hover); }
            .btn-secondary { background: #f4f5f7; color: #42526e; }
            .btn-secondary:hover { background: #e9ebf0; }
            #table-list-wrapper { max-height: 400px; overflow-y: auto; border: 1px solid var(--border); border-radius: 4px; padding: 1rem; background: #fafbfc; }
            .table-item { display: flex; align-items: center; padding: 0.5rem; border-radius: 3px; }
            .table-item:hover { background: #f0f2f5; }
            .table-item input { margin-right: 0.75rem; }
            .table-item .warning { color: var(--danger); margin-left: auto; font-size: 0.8rem; font-weight: 500; cursor: help; user-select: none;}
            .actions { margin-top: 1.5rem; display: flex; justify-content: flex-end; gap: 1rem; }
            .final-action { text-align: center; }
            .hidden { display: none; }
        </style>
    </head>
    <body>
    <div class="container">
        <header class="header"><pre>{{ mignon_logo|safe }}</pre></header>
        <div class="card">
            <div class="card-header">1. 配置数据库连接</div>
            <div class="card-body"><div class="form-grid">
                <fieldset id="source-db-fieldset"><legend>源数据库 (Source)</legend>
                    <div class="form-group"><label>Host</label><input type="text" id="sourceHost" class="form-control" value="localhost"></div>
                    <div class="form-group"><label>Port</label><input type="number" id="sourcePort" class="form-control" value="3306"></div>
                    <div class="form-group"><label>Username</label><input type="text" id="sourceUser" class="form-control" value="root"></div>
                    <div class="form-group"><label>Password</label><input type="password" id="sourcePass" class="form-control"></div>
                    <div class="form-group"><label>Database</label><input type="text" id="sourceDb" class="form-control"></div>
                    <div class="actions"><button id="test-source-btn" class="btn btn-secondary">测试连接</button></div>
                </fieldset>
                <fieldset><legend>目标数据库 (Target)</legend>
                    <div class="form-group"><label>Host</label><input type="text" id="targetHost" class="form-control" value="localhost"></div>
                    <div class="form-group"><label>Port</label><input type="number" id="targetPort" class="form-control" value="3306"></div>
                    <div class="form-group"><label>Username</label><input type="text" id="targetUser" class="form-control" value="root"></div>
                    <div class="form-group"><label>Password</label><input type="password" id="targetPass" class="form-control"></div>
                    <div class="form-group"><label>Database</label><input type="text" id="targetDb" class="form-control"></div>
                    <div class="actions"><button id="test-target-btn" class="btn btn-secondary">测试连接</button></div>
                </fieldset>
            </div></div>
        </div>
        <div class="card hidden" id="tables-card">
            <div class="card-header">2. 选择要迁移的表</div>
            <div class="card-body">
                <button id="fetch-tables-btn" class="btn btn-primary" disabled>首先，请获取表列表</button>
                <div id="table-config-wrapper" class="hidden" style="margin-top:1.5rem;">
                    <div style="display: flex; gap: 1rem; margin-bottom: 1rem; align-items: center;">
                        <div class="form-group" style="flex-grow: 1;"><label>过滤模式</label><select id="filter-mode" class="form-control" style="max-width: 200px;"><option value="include" selected>包含模式 (Include)</option><option value="exclude">排除模式 (Exclude)</option></select></div>
                        <button id="select-all-btn" class="btn btn-secondary" style="min-width: unset;">全选</button>
                        <button id="deselect-all-btn" class="btn btn-secondary" style="min-width: unset;">取消全选</button>
                    </div>
                    <div id="table-list-wrapper"></div>
                </div>
            </div>
        </div>
        <div class="card">
            <div class="card-header">3. 迁移选项与生成</div>
            <div class="card-body">
                <div class="form-group" style="align-items: center; flex-direction: row; gap: 1rem; justify-content: center; margin-bottom: 1.5rem;">
                    <input type="checkbox" id="autoSkipError" style="width: 1.25em; height: 1.25em;">
                    <label for="autoSkipError" style="margin-bottom: 0;">迁移时自动跳过错误行 (Auto Skip Errors)</label>
                </div>
                <div class="final-action">
                    <button id="generate-btn" class="btn btn-primary" disabled>生成 dataBaseTransfer.json 文件</button>
                    <p id="generate-status" style="margin-top:1rem;"></p>
                </div>
            </div>
        </div>
    </div>
    <script>
        const initialConfig = {{ initial_config|tojson|safe }};

        document.addEventListener('DOMContentLoaded', () => {
            const populateForm = (config) => {
                if (!config || Object.keys(config).length === 0) return;
                document.getElementById('sourceHost').value = config.host || 'localhost';
                document.getElementById('sourcePort').value = config.port || 3306;
                document.getElementById('sourceUser').value = config.userName || 'root';
                document.getElementById('sourcePass').value = config.password || '';
                document.getElementById('sourceDb').value = config.needToTransferredDataBase || '';
                document.getElementById('targetHost').value = config.targetHost || 'localhost';
                document.getElementById('targetPort').value = config.targetPort || 3306;
                document.getElementById('targetUser').value = config.targetUserName || 'root';
                document.getElementById('targetPass').value = config.targetPassword || '';
                document.getElementById('targetDb').value = config.targetDataBase || '';
                document.getElementById('autoSkipError').checked = config.autoSkipError === true;
                 if (config.isInclude === false) {
                    document.getElementById('filter-mode').value = 'exclude';
                }
            };
            populateForm(initialConfig);

            const fetchTablesBtn = document.getElementById('fetch-tables-btn');
            const generateBtn = document.getElementById('generate-btn');
            const tablesCard = document.getElementById('tables-card');
            const selectAllBtn = document.getElementById('select-all-btn');
            const deselectAllBtn = document.getElementById('deselect-all-btn');
            
            const testConnection = async (type) => {
                const btn = document.getElementById(`test-${type}-btn`);
                const originalHTML = btn.innerHTML;
                
                btn.innerHTML = '连接中...';
                btn.classList.add('is-loading');
                btn.disabled = true;

                const host = document.getElementById(`${type}Host`).value, port = document.getElementById(`${type}Port`).value, user = document.getElementById(`${type}User`).value, pass = document.getElementById(`${type}Pass`).value, db = document.getElementById(`${type}Db`).value;
                
                const response = await fetch('/test_connection', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ host, port, user, pass, db }) });
                const result = await response.json();
                
                btn.classList.remove('is-loading');
                btn.innerHTML = result.message;

                if (result.success) {
                    btn.classList.add('is-success');
                    if (type === 'source') {
                        fetchTablesBtn.disabled = false;
                        tablesCard.classList.remove('hidden');
                    }
                } else {
                    btn.classList.add('is-danger');
                }

                setTimeout(() => {
                    btn.innerHTML = originalHTML;
                    btn.classList.remove('is-success', 'is-danger');
                    btn.disabled = false;
                }, 3000);
            };

            document.getElementById('test-source-btn').addEventListener('click', () => testConnection('source'));
            document.getElementById('test-target-btn').addEventListener('click', () => testConnection('target'));

            fetchTablesBtn.addEventListener('click', async () => {
                fetchTablesBtn.disabled = true;
                fetchTablesBtn.classList.add('is-loading');
                const host = document.getElementById('sourceHost').value, port = document.getElementById('sourcePort').value, user = document.getElementById('sourceUser').value, pass = document.getElementById('sourcePass').value, db = document.getElementById('sourceDb').value;
                const response = await fetch('/get_tables', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ host, port, user, pass, db }) });
                const result = await response.json();
                const listWrapper = document.getElementById('table-list-wrapper');

                fetchTablesBtn.classList.remove('is-loading');
                fetchTablesBtn.disabled = false;

                if (result.success) {
                    listWrapper.innerHTML = result.tables.map(table => {
                        const isChecked = table.isValid ? 'checked' : '';
                        const warningHTML = !table.isValid 
                            ? `<span class="warning" title="${table.reason}">⚠️ id 不兼容</span>` 
                            : '';
                        
                        return `
                            <div class="table-item">
                                <input type="checkbox" id="table_${table.name}" value="${table.name}" ${isChecked}>
                                <label for="table_${table.name}">${table.name}</label>
                                ${warningHTML}
                            </div>`;
                    }).join('');
                    document.getElementById('table-config-wrapper').classList.remove('hidden');
                    generateBtn.disabled = false;
                } else { 
                    alert('获取表列表失败: ' + result.error); 
                }
            });
            
            // 新增全选/取消全选按钮的事件监听器
            selectAllBtn.addEventListener('click', () => {
                const checkboxes = document.querySelectorAll('#table-list-wrapper input[type="checkbox"]');
                checkboxes.forEach(cb => cb.checked = true);
            });
            
            deselectAllBtn.addEventListener('click', () => {
                const checkboxes = document.querySelectorAll('#table-list-wrapper input[type="checkbox"]');
                checkboxes.forEach(cb => cb.checked = false);
            });

            generateBtn.addEventListener('click', async () => {
                const config = {
                    needToTransferredDataBase: document.getElementById('sourceDb').value, userName: document.getElementById('sourceUser').value, password: document.getElementById('sourcePass').value, host: document.getElementById('sourceHost').value, port: parseInt(document.getElementById('sourcePort').value),
                    targetDataBase: document.getElementById('targetDb').value, targetUserName: document.getElementById('targetUser').value, targetPassword: document.getElementById('targetPass').value, targetHost: document.getElementById('targetHost').value, targetPort: parseInt(document.getElementById('targetPort').value),
                    isInclude: document.getElementById('filter-mode').value === 'include', excludeList: [], includeList: [],
                    autoSkipError: document.getElementById('autoSkipError').checked
                };
                const tableCheckboxes = document.querySelectorAll('#table-list-wrapper input[type="checkbox"]');
                const selectedTables = Array.from(tableCheckboxes).filter(cb => cb.checked).map(cb => cb.value);
                const unselectedTables = Array.from(tableCheckboxes).filter(cb => !cb.checked).map(cb => cb.value);
                if (config.isInclude) { config.includeList = selectedTables; } else { config.excludeList = unselectedTables; }
                const response = await fetch('/generate_config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(config) });
                const result = await response.json();
                const statusEl = document.getElementById('generate-status');
                if(result.success) { statusEl.textContent = `成功! 配置文件已保存到: ${result.path}`; statusEl.style.color = 'var(--success)'; } else { statusEl.textContent = `错误: ${result.error}`; statusEl.style.color = 'var(--danger)'; }
            });
        });
    </script>
    </body>
    </html>
    """

    def __init__(self, config_path):
        if not Flask:
            raise ImportError("Eazy Mode requires Flask. Please run 'pip install Flask'.")
        self.app = Flask(__name__)
        self.config_path = config_path
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.mignon_logo = """         
                                                        
   __     __)                  
  (, /|  /|   ,                
    / | / |     _  __   _____  
 ) /  |/  |__(_(_/_/ (_(_) / (_
(_/   '       .-/              
             (_/               
                             v 0.5 mignonFramework
"""
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            initial_config = {}
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        initial_config = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass
            return render_template_string(self.HTML_TEMPLATE,
                                          mignon_logo=self.mignon_logo,
                                          initial_config=initial_config)

        @self.app.route('/test_connection', methods=['POST'])
        def test_connection():
            data = request.json
            db_manager = None
            try:
                db_manager = MysqlManager(
                    host=data['host'], user=data['user'], password=data['pass'],
                    database=data['db'], port=int(data['port'])
                )
                with db_manager.connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                return jsonify({'success': True, 'message': '连接成功!'})
            except Exception as e:
                return jsonify({'success': False, 'message': f'连接失败: {e}'})
            finally:
                if db_manager:
                    (db_manager.close_pool if hasattr(db_manager, 'pool') else db_manager.close)()

        @self.app.route('/favicon.ico')
        def favicon():
            static_folder = os.path.join(self.current_dir, 'starterUtil', "static/ico")
            return send_from_directory(static_folder, 'favicon.ico')


        @self.app.route('/get_tables', methods=['POST'])
        def get_tables():
            data = request.json
            db_manager = None
            try:
                db_manager = MysqlManager(
                    host=data['host'], user=data['user'], password=data['pass'],
                    database=data['db'], port=int(data['port'])
                )
                with db_manager.connection.cursor() as cursor:
                    cursor.execute("SHOW TABLES;")
                    tables_dicts = cursor.fetchall()
                    table_names = [list(row.values())[0] for row in tables_dicts]

                    validated_tables = []
                    integer_types = ['int', 'bigint', 'mediumint', 'smallint', 'tinyint']

                    for table_name in table_names:
                        validation_result = {
                            "name": table_name,
                            "isValid": False,
                            "reason": "未找到名为 'id' 的列。"
                        }

                        query = """
                                SELECT DATA_TYPE
                                FROM INFORMATION_SCHEMA.COLUMNS
                                WHERE TABLE_SCHEMA = %s
                                  AND TABLE_NAME = %s
                                  AND COLUMN_NAME = 'id' \
                                """
                        cursor.execute(query, (data['db'], table_name))
                        column_info = cursor.fetchone()

                        if column_info:
                            data_type = column_info.get('DATA_TYPE', '').lower()
                            if data_type in integer_types:
                                validation_result["isValid"] = True
                                validation_result["reason"] = ""
                            else:
                                validation_result["reason"] = f"'id' 列不是整数类型 (当前: {data_type})。"

                        validated_tables.append(validation_result)

                return jsonify({'success': True, 'tables': validated_tables})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
            finally:
                if db_manager:
                    (db_manager.close_pool if hasattr(db_manager, 'pool') else db_manager.close)()

        @self.app.route('/generate_config', methods=['POST'])
        def generate_config():
            data_from_frontend = request.json
            final_config = {**data_from_frontend}
            final_config["alreadyFinished"] = []
            final_config["nowTitle"] = ""
            final_config["nowLastId"] = 0
            existing_config = {}
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        existing_config = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass
            final_config["batchSize"] = existing_config.get("batchSize", 1000)

            try:
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(final_config, f, indent=4, ensure_ascii=False)
                return jsonify({'success': True, 'path': self.config_path})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

    def run(self, host='127.0.0.1', port=5001):
        print(f" * mignonFramework 数据库迁移 Eazy Mode 已启动，请访问 http://{host}:{port}")
        print(" * (配置完成后按 CTRL+C 退出服务器)")
        self.app.run(host=host, port=port, debug=False)

# --- 5. 运行器和配置初始化 (集成 Eazy Mode) ---
class DatabaseTransferRunner:
    """
    负责初始化配置并运行迁移任务的类。
    """
    DEFAULT_CONFIG_PATH = "./resources/config/dataBaseTransfer.json"

    def __init__(self, config_path: Optional[str] = None, eazy: bool = False):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.eazy = eazy

        if not self.eazy:
            self.config_manager = JsonConfigManager(self.config_path)
            self._ensure_config_file_exists()

    def _ensure_config_file_exists(self):
        if not hasattr(self, 'config_manager') or not self.config_manager.data:
            print(f"配置文件未找到或为空。正在于 '{self.config_path}' 创建模板。")
            default_config = {
                "needToTransferredDataBase": "source_db_name", "userName": "root", "password": "password",
                "host": "localhost", "port": 3306, "targetDataBase": "target_db_name",
                "targetUserName": "root", "targetPassword": "password", "targetHost": "localhost",
                "targetPort": 3306, "excludeList": ["some_log_table"], "alreadyFinished": [],
                "nowTitle": "", "nowLastId": 0, "isInclude": True, "includeList": [],
                "batchSize": 1000, "autoSkipError": False
            }
            temp_manager = JsonConfigManager(self.config_path)
            temp_manager.data = default_config
            temp_manager._save()
            print("配置模板已创建。请填写您的数据库信息后再次运行。")
            sys.exit(0)

    def run(self, transfer_class: Type[AbstractDatabaseTransfer] = MySQLToMySQLTransfer):
        """
        加载配置，实例化指定的迁移类，并执行迁移。
        如果 eazy=True，则启动 Eazy Mode Web UI。
        """
        if self.eazy:
            if not Flask:
                print("[错误] Eazy Mode 需要 Flask。请运行 'pip install Flask'。")
                return
            try:
                eazy_runner = TransferEazyAppRunner(config_path=self.config_path)
                eazy_runner.run()
            except ImportError as e:
                print(f"[错误] 无法启动Eazy Mode，请确保 'flask' 已安装 (pip install flask). 错误: {e}")
            except Exception as e:
                print(f"[错误] 启动 Eazy Mode 失败: {e}")
            return

        if not hasattr(self, 'config_manager'):
            self.config_manager = JsonConfigManager(self.config_path)
            self._ensure_config_file_exists()

        config_proxy = self.config_manager.getInstance(TransferConfig)

        if config_proxy.needToTransferredDataBase == "source_db_name":
            print(f"请更新 '{self.config_path}' 中的数据库信息，或使用 '--eazy' 标志启动 Eazy Mode 生成配置。")
            return

        print(f"配置已加载。正在使用 '{transfer_class.__name__}' 开始迁移...")
        transfer_instance = transfer_class(config_proxy)
        transfer_instance.run()


if __name__ == '__main__':
    is_eazy_mode = '--eazy' in sys.argv

    runner = DatabaseTransferRunner(eazy=is_eazy_mode)
    runner.run()


