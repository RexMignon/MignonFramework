import random
import threading
from typing import Optional, Union, List, Callable, Any, Dict, Tuple, Type

# 假设 mignonFramework.utils.ConfigReader.ConfigManager 存在
from mignonFramework.utils.ConfigReader import ConfigManager

def target(queue_instance, attr_name, attr_value):
    def decorator(cls):
        if not hasattr(queue_instance, 'add_finalization_task'):
            raise TypeError("传递给 @target 的对象必须是支持 add_finalization_task 的 QueueIter 实例。")
        queue_instance.add_finalization_task(cls, attr_name, attr_value)
        return cls
    return decorator


class QueueIter:
    """
    一个最终整合版的、灵活、可重用、支持装饰器配置和随机种子的爬取队列生成器。
    ConfigManager 在使用 @target 功能时才是必需的。
    所有核心属性 (pages, current_index, callback) 均支持动态修改。
    """
    def __init__(self,
                 config_manager: Optional[Any] = None,
                 shuffle: bool = True,
                 callback: Optional[Callable[["QueueIter"], None]] = None,
                 pages: Union[List[int], range] = range(0, 1),
                 current_index: Optional[int] = 0,
                 seed: Optional[int] = 114514
                 ):
        self._lock = threading.Lock()
        self.config_manager = config_manager
        self._finalization_tasks: Dict[Type, List[Tuple[str, Any]]] = {}
        self.shuffle = shuffle
        self.seed = seed
        self.pages = pages
        self.current_index = current_index
        self.callback = callback # <<< MODIFICATION: 现在通过 setter 初始化

    def add_finalization_task(self, target_class: Type, attr_name: str, attr_value: Any):
        with self._lock:
            if target_class not in self._finalization_tasks:
                self._finalization_tasks[target_class] = []
            self._finalization_tasks[target_class].append((attr_name, attr_value))

    @property
    def pages(self) -> List[Any]:
        with self._lock:
            return self._pages

    @pages.setter
    def pages(self, new_pages: Union[List[int], range]):
        if not isinstance(new_pages, (list, range)):
            raise TypeError("pages 必须是一个列表或 range 对象。")
        with self._lock:
            self._pages = list(new_pages)
            if self.shuffle:
                if self.seed is not None:
                    random.seed(self.seed)
                random.shuffle(self._pages)
            self._current_index = 0
            self._finalized = False

    @property
    def current_index(self) -> int:
        with self._lock:
            return self._current_index

    @current_index.setter
    def current_index(self, new_index: int):
        if not isinstance(new_index, int):
            raise TypeError("current_index 必须是一个整数。")
        with self._lock:
            if not (0 <= new_index <= len(self._pages)):
                raise ValueError(f"索引 {new_index} 超出有效范围 0 到 {len(self._pages)}。")
            self._current_index = new_index

    # <<< NEW: callback 的 getter 和 setter >>>
    @property
    def callback(self) -> Optional[Callable[["QueueIter"], None]]:
        """获取当前的回调函数。"""
        with self._lock:
            return self._callback

    @callback.setter
    def callback(self, new_callback: Optional[Callable[["QueueIter"], None]]):
        """动态设置或清空回调函数。"""
        if new_callback is not None and not callable(new_callback):
            raise TypeError("callback 必须是一个可调用对象或 None。")
        with self._lock:
            self._callback = new_callback

    def __iter__(self):
        return self

    def __next__(self):
        with self._lock:
            if self._current_index >= len(self._pages):
                raise StopIteration
            page_to_return = self._pages[self._current_index]
            self._current_index += 1
            return page_to_return

    def hasNext(self) -> bool:
        with self._lock:
            has_next = self._current_index < len(self._pages)
            if not has_next and not self._finalized:
                if self._finalization_tasks:
                    if not self.config_manager:
                        raise ValueError("已使用 @target 装饰器注册任务，但在 QueueIter 初始化时未提供有效的 config_manager。")
                    for target_class, tasks in self._finalization_tasks.items():
                        instance_to_modify = self.config_manager.getInstance(target_class)
                        for attr_name, value_or_func in tasks:
                            if callable(value_or_func):
                                old_value = getattr(instance_to_modify, attr_name, None)
                                new_value = value_or_func(old_value)
                                setattr(instance_to_modify, attr_name, new_value)
                            else:
                                setattr(instance_to_modify, attr_name, value_or_func)
                self._finalized = True
            return has_next

    def call(self):
        """
        手动触发回调函数。
        这是一个线程安全的操作。
        """
        callback_to_run = self.callback

        if callback_to_run:
            # 在锁外执行
            callback_to_run(self)