import rate_limit
from rate_limit import LoginRateLimiter
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier


def test_requests_over_limit_are_rejected():
    limiter = LoginRateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("ip-a") is True
    assert limiter.allow("ip-a") is True
    assert limiter.allow("ip-a") is False


def test_sources_have_separate_limits():
    limiter = LoginRateLimiter(limit=1, window_seconds=60)

    assert limiter.allow("ip-a") is True
    assert limiter.allow("ip-a") is False

    # A 用完额度，不应影响 B。
    assert limiter.allow("ip-b") is True


def test_window_resets_at_expiration(monkeypatch):
    current_time = 100.0

    monkeypatch.setattr(
        rate_limit,
        "monotonic",
        lambda: current_time,
    )

    limiter = LoginRateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("ip-a") is True

    current_time = 130.0
    assert limiter.allow("ip-a") is True

    # 距离首次请求还不足 60 秒，额度不能恢复。
    current_time = 159.9
    assert limiter.allow("ip-a") is False

    # 恰好经过 60 秒，开启新窗口。
    current_time = 160.0
    assert limiter.allow("ip-a") is True
    assert limiter.allow("ip-a") is True
    assert limiter.allow("ip-a") is False


def test_concurrent_requests_respect_limit(monkeypatch):
    monkeypatch.setattr(rate_limit, "monotonic", lambda: 100.0)
    limiter = LoginRateLimiter(limit=5, window_seconds=60)
    request_count = 20
    barrier = Barrier(request_count)

    def attempt():
        # 等所有线程准备好，再一起开始检查。
        barrier.wait(timeout=10)
        return limiter.allow("ip-a")

    with ThreadPoolExecutor(max_workers=request_count) as executor:
        futures = [
            executor.submit(attempt)
            for _ in range(request_count)
        ]
        results = [
            future.result(timeout=10)
            for future in futures
        ]

    assert results.count(True) == 5
    assert results.count(False) == 15


def test_rejected_request_reports_wait_time(monkeypatch):
    current_time = 100.0
    monkeypatch.setattr(
        rate_limit,
        "monotonic",
        lambda: current_time,
    )

    limiter = LoginRateLimiter(limit=1, window_seconds=60)

    assert limiter.check("ip-a") == (True, 0)

    current_time = 125.0
    assert limiter.check("ip-a") == (False, 35)

    current_time = 159.8
    assert limiter.check("ip-a") == (False, 1)

    current_time = 160.0
    assert limiter.check("ip-a") == (True, 0)

def test_cleanup_removes_only_expired_sources(monkeypatch):
    current_time = 100.0
    monkeypatch.setattr(
        rate_limit,
        "monotonic",
        lambda: current_time,
    )

    limiter = LoginRateLimiter(limit=1, window_seconds=60)

    assert limiter.check("ip-a") == (True, 0)

    current_time = 130.0
    assert limiter.check("ip-b") == (True, 0)

    # A 已过期，B 尚未过期；C 的请求触发清理。
    current_time = 160.0
    assert limiter.check("ip-c") == (True, 0)

    assert "ip-a" not in limiter._windows
    assert "ip-b" in limiter._windows
    assert "ip-c" in limiter._windows

    # B 的原有额度不能因清理而恢复。
    assert limiter.check("ip-b") == (False, 30)