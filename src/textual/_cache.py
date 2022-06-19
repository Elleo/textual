import sys
from collections import deque
from functools import wraps
from threading import Lock
from typing import (
    Callable,
    Deque,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
    overload,
)

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

CacheKey = TypeVar("CacheKey")
CacheValue = TypeVar("CacheValue")
DefaultValue = TypeVar("DefaultValue")


class LRUCache(Generic[CacheKey, CacheValue]):
    """
    A dictionary-like container that stores a given maximum items.

    If an additional item is added when the LRUCache is full, the least
    recently used key is discarded to make room for the new item.

    The implementation is similar to functools.lru_cache, which uses a linked
    list to keep track of the most recently used items.

    Each entry is stored as [PREV, NEXT, KEY, VALUE] where PREV is a reference
    to the previous entry, and NEXT is a reference to the next value.

    """

    def __init__(self, maxsize: int) -> None:
        self.maxsize = maxsize
        self.cache: Dict[CacheKey, List[object]] = {}
        self.full = False
        self.root: List[object] = []
        self._lock = Lock()
        super().__init__()

    def __len__(self) -> int:
        return len(self.cache)

    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self.cache.clear()
            self.full = False
            self.root = []

    def set(self, key: CacheKey, value: CacheValue) -> None:
        """Set a value.

        Args:
            key (CacheKey): Key.
            value (CacheValue): Value.
        """
        with self._lock:
            link = self.cache.get(key)
            if link is None:
                root = self.root
                if not root:
                    self.root[:] = [self.root, self.root, key, value]
                else:
                    self.root = [root[0], root, key, value]
                    root[0][1] = self.root  # type: ignore[index]
                    root[0] = self.root
                self.cache[key] = self.root

                if self.full or len(self.cache) > self.maxsize:
                    self.full = True
                    root = self.root
                    last = root[0]
                    last[0][1] = root  # type: ignore[index]
                    root[0] = last[0]  # type: ignore[index]
                    del self.cache[last[2]]  # type: ignore[index]

    __setitem__ = set

    @overload
    def get(self, key: CacheKey) -> Optional[CacheValue]:
        ...

    @overload
    def get(
        self, key: CacheKey, default: DefaultValue
    ) -> Union[CacheValue, DefaultValue]:
        ...

    def get(
        self, key: CacheKey, default: Optional[DefaultValue] = None
    ) -> Union[CacheValue, Optional[DefaultValue]]:
        """Get a value from the cache, or return a default if the key is not present.

        Args:
            key (CacheKey): Key
            default (Optional[DefaultValue], optional): Default to return if key is not present. Defaults to None.

        Returns:
            Union[CacheValue, Optional[DefaultValue]]: Either the value or a default.
        """
        link = self.cache.get(key)
        if link is None:
            return default
        if link is not self.root:
            with self._lock:
                link[0][1] = link[1]  # type: ignore[index]
                link[1][0] = link[0]  # type: ignore[index]
                root = self.root
                link[0] = root[0]
                link[1] = root
                root[0][1] = link  # type: ignore[index]
                root[0] = link
                self.root = link
        return link[3]  # type: ignore[return-value]

    def __getitem__(self, key: CacheKey) -> CacheValue:
        link = self.cache[key]
        if link is not self.root:
            with self._lock:
                link[0][1] = link[1]  # type: ignore[index]
                link[1][0] = link[0]  # type: ignore[index]
                root = self.root
                link[0] = root[0]
                link[1] = root
                root[0][1] = link  # type: ignore[index]
                root[0] = link
                self.root = link
        return link[3]  # type: ignore[return-value]

    def __contains__(self, key: CacheKey) -> bool:
        return key in self.cache


P = ParamSpec("P")
T = TypeVar("T")


def fifo_cache(maxsize: int) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """A First In First Out cache.

    Args:
        maxsize (int): Maximum size of the cache

    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        queue: Deque[object] = deque()
        cache: Dict[object, T] = {}

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return cache[args]
            except KeyError:
                assert not kwargs, "Will not work with keyword arguments!"
                cache[args] = result = func(*args)
                queue.append(args)
                if len(queue) > maxsize:
                    del cache[queue.popleft()]
                return result

        return wrapper

    return decorator


@fifo_cache(10)
def double(n: int) -> int:
    return n * n


print(double(1))
print(double(2))
print(double(2))
print(double(3))
print(double(4))