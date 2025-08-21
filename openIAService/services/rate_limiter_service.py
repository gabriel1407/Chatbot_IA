import time
import threading
from collections import defaultdict, deque

# Simple in-memory sliding window rate limiter
# Not suitable for multi-process or distributed setups.

_lock = threading.Lock()
_events: dict[str, deque] = defaultdict(deque)


def is_allowed(key: str, limit: int = 20, window_seconds: int = 60) -> bool:
    """
    Returns True if the action is allowed for the given key under the limit/window.
    Sliding window using deque of timestamps.
    """
    now = time.time()
    cutoff = now - window_seconds
    with _lock:
        dq = _events[key]
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) < limit:
            dq.append(now)
            return True
        return False


def remaining(key: str, limit: int, window_seconds: int) -> int:
    now = time.time()
    cutoff = now - window_seconds
    with _lock:
        dq = _events[key]
        while dq and dq[0] < cutoff:
            dq.popleft()
        return max(0, limit - len(dq))
