import random
import threading
from typing import Optional, Union, List, Callable


class QueueRandomIterator:
    """
    一个灵活的爬取队列生成器，支持多种初始化方式，并支持线程安全。

    回调函数现在需要通过公共方法 call_callback() 手动触发。
    """

    def __init__(self,
                 pages: Union[List[int], range],
                 seed: Optional[int] = 114514,
                 current_index: Optional[int] = None,
                 shuffle: bool = True,
                 callback: Optional[Callable[["QueueRandomIterator"], None]] = None):
        """
        初始化 QueueRandomIterator 实例。

        Args:
            pages (Union[List[int], range]): 待爬取的页码列表或 range 对象。
            seed (Optional[int]): 用于打乱顺序的随机数种子。
            current_index (Optional[int]): 断点续爬的起始索引。
            shuffle (bool): 是否打乱列表顺序。默认为 True。
            callback (Optional[Callable[[QueueRandomIterator], None]]): 可选的回调函数。

        Raises:
            ValueError: 如果参数组合不正确或断点索引无效。
        """
        if not isinstance(pages, (list, range)):
            raise ValueError("`pages` 参数必须是一个列表或 range 对象。")

        self._pages = list(pages)

        if shuffle:
            if seed is not None:
                random.seed(seed)
            random.shuffle(self._pages)

        self._current_index = 0
        if current_index is not None:
            if not (0 <= current_index < len(self._pages)):
                raise ValueError(f"断点索引不在有效爬取范围内: 0 到 {len(self._pages) - 1}。")
            self._current_index = current_index

        self._lock = threading.Lock()

        self.callback = callback

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
            return self._current_index < len(self._pages)

    def get_current_index(self) -> int:
        with self._lock:
            return self._current_index

    def call(self):
        """
        手动触发回调函数，如果它已被设置。
        回调函数会接收 QueueRandomIterator 实例自身作为参数。
        """
        if self.callback:
            self.callback(self)

