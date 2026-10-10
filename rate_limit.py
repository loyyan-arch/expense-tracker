from time import monotonic
from threading import Lock
from math import ceil


class LoginRateLimiter:
    def __init__(self, limit: int = 5, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds

        # 来源标识 -> (窗口开始时间, 已允许的请求次数)
        self._windows: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    def check(self, key: str) -> tuple[bool, int]:
        with self._lock:
            now = monotonic()

            # 先收集过期来源，再删除。
            expired_keys = [
                source
                for source, (started_at, _) in self._windows.items()
                if now - started_at >= self.window_seconds
            ]

            for source in expired_keys:
                del self._windows[source]

            window = self._windows.get(key)

            # 过期记录已清理；不存在就开启新窗口。
            if window is None:
                self._windows[key] = (now, 1)
                return True, 0

            started_at, count = window

            if count >= self.limit:
                remaining = self.window_seconds - (now - started_at)
                return False, ceil(remaining)

            self._windows[key] = (started_at, count + 1)
            return True, 0

    def allow(self, key: str) -> bool:
        allowed, _ = self.check(key)
        return allowed