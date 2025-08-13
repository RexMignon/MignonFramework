import sqlite3
import os
import shutil
import asyncio
from typing import List, Optional
import queue
import threading
import time

# 假设 BaseStateTracker 在这个路径
from mignonFramework.utils.BaseStateTracker import BaseStateTracker

class SQLiteStateTracker(BaseStateTracker):
    """
    使用SQLite数据库来跟踪文件处理状态的具体实现。
    内部使用一个专用的写入线程，并通过批量写入和PRAGMA调优来获得高性能。
    """
    def __init__(self, db_path: str, table_name: str = 'file_status', exception_dir: Optional[str] = None, batch_size: int = 1000):
        self.db_path = db_path
        self.table_name = table_name
        self.exception_dir = exception_dir
        self.batch_size = batch_size # 批处理大小

        self.db_queue = queue.Queue()
        self.writer_thread = None

        if os.path.dirname(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if self.exception_dir:
            os.makedirs(self.exception_dir, exist_ok=True)

    def _db_writer_loop(self):
        """
        这是专用的数据库写入线程的目标函数。
        它在此线程中创建连接，并以批处理方式写入数据。
        """
        conn = sqlite3.connect(self.db_path)

        # --- PRAGMA 调优 ---
        # 1. WAL模式: 提升并发写入性能
        conn.execute("PRAGMA journal_mode = WAL;")
        # 2. 关闭同步: 大幅提升写入速度，代价是系统崩溃时可能丢失最后几笔写入。对我们的场景非常适用。
        conn.execute("PRAGMA synchronous = OFF;")
        # 3. 增加缓存大小 (例如64MB)
        conn.execute("PRAGMA cache_size = -64000;")

        # 创建表
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS "{self.table_name}" (
            filename TEXT PRIMARY KEY, status TEXT NOT NULL,
            error_message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        conn.execute(create_table_sql)
        conn.commit()

        batch = []
        while True:
            try:
                # 尝试从队列获取数据，设置一个短暂的超时
                item = self.db_queue.get(timeout=0.1)

                if item is None: # 收到退出信号
                    if batch: # 提交最后一批数据
                        self._execute_batch(conn, batch)
                    break

                batch.append(item)

                # 当批次达到规模时，执行写入
                if len(batch) >= self.batch_size:
                    self._execute_batch(conn, batch)
                    batch = [] # 清空批次

            except queue.Empty:
                # 队列暂时为空，这是一个提交当前批次的好时机
                if batch:
                    self._execute_batch(conn, batch)
                    batch = []

        conn.close()

    def _execute_batch(self, conn, batch: List):
        """使用 executemany 执行批量写入。"""
        try:
            sql = f"""
            INSERT INTO "{self.table_name}" (filename, status, error_message)
            VALUES (?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                status=excluded.status,
                error_message=excluded.error_message,
                timestamp=CURRENT_TIMESTAMP;
            """
            conn.executemany(sql, batch)
            conn.commit()
        except Exception as e:
            print(f"[数据库批量写入错误] {e}")


    # --- 其他方法 (initialize, get_unprocessed_files, mark_*, close) 无需修改 ---
    # ... (为了简洁，这里省略了其他未变动的方法，它们和上一版完全一样) ...
    def initialize(self):
        """启动数据库写入线程。"""
        if self.writer_thread is None:
            self.writer_thread = threading.Thread(target=self._db_writer_loop, daemon=True)
            self.writer_thread.start()

    def get_unprocessed_files(self, all_input_files: List[str]) -> List[str]:
        # get 操作可以安全地使用临时连接，因为它不与写入线程冲突
        conn = sqlite3.connect(self.db_path)
        try:
            all_basenames = {os.path.basename(p): p for p in all_input_files}
            cursor = conn.cursor()
            cursor.execute(f'SELECT filename FROM "{self.table_name}"')
            processed_filenames = {row[0] for row in cursor.fetchall()}
            unprocessed_basenames = set(all_basenames.keys()) - processed_filenames
            return [all_basenames[bn] for bn in unprocessed_basenames]
        finally:
            conn.close()

    def mark_as_finished(self, file_path: str):
        """将“成功”任务放入队列。这是一个快速的同步操作。"""
        self.db_queue.put((os.path.basename(file_path), 'processed', None))

    def mark_as_exception(self, file_path: str, error_message: str):
        """
        将“失败”任务放入队列，并同步移动文件。
        """
        self.db_queue.put((os.path.basename(file_path), 'error', error_message))

        if self.exception_dir:
            try:
                # 移动文件是IO操作，但在这里可以接受同步执行，因为它只在出错时发生
                dst = os.path.join(self.exception_dir, os.path.basename(file_path))
                shutil.move(file_path, dst)
            except Exception as e:
                print(f"\n[警告] 移动异常文件失败: 从 {file_path} 到 {self.exception_dir} - {e}")


    def close(self):
        """
        向队列发送停止信号，并等待写入线程结束。
        增加了用户提示。
        """
        if self.writer_thread:
            print("\n文件扫描和解析已完成。正在等待所有状态记录写入数据库...")

            self.db_queue.put(None)
            self.writer_thread.join()

            print("数据库写入完成，所有任务结束。程序退出。")