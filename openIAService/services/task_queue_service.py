import threading
import queue
import logging
from typing import Callable, Any
from decouple import config

# Optional Redis RQ support
_rq_queue = None
try:
    from redis import Redis
    from rq import Queue
    REDIS_URL = config('REDIS_URL', default='')
    if REDIS_URL:
        _rq_queue = Queue(connection=Redis.from_url(REDIS_URL))
        logging.info("[TASK-QUEUE] Using Redis RQ queue")
except Exception as e:
    logging.info(f"[TASK-QUEUE] Redis RQ not available: {e}")

# Fallback in-memory queue
_tasks: "queue.Queue[tuple[Callable, tuple, dict]]" = queue.Queue()
_started = False
_lock = threading.Lock()


def _worker():
    while True:
        try:
            func, args, kwargs = _tasks.get()
            try:
                func(*args, **kwargs)
            except Exception as e:
                logging.error(f"[TASK-QUEUE] Error executing task {getattr(func, '__name__', str(func))}: {e}")
            finally:
                _tasks.task_done()
        except Exception as e:
            logging.error(f"[TASK-QUEUE] Worker error: {e}")


def start_worker():
    global _started
    if _rq_queue is not None:
        # Redis-based, external worker recommended, no local thread needed
        logging.info("[TASK-QUEUE] Redis RQ mode: external worker expected")
        return
    with _lock:
        if _started:
            return
        t = threading.Thread(target=_worker, name="task-worker", daemon=True)
        t.start()
        _started = True
        logging.info("[TASK-QUEUE] In-memory worker started")


def is_distributed() -> bool:
    return _rq_queue is not None


def submit_task_by_name(func_path: str, *args: Any, **kwargs: Any) -> None:
    """Enqueue a task by import path 'module.sub:function'."""
    if _rq_queue is not None:
        # For RQ, use string path but ensure it's importable format
        try:
            # Convert colon format to dot format for RQ
            if ":" in func_path:
                module_name, func_name = func_path.split(":")
                rq_func_path = f"{module_name}.{func_name}"
            else:
                rq_func_path = func_path
            
            job = _rq_queue.enqueue(rq_func_path, *args, **kwargs)
            logging.info(f"[TASK-QUEUE] Enqueued RQ job func={rq_func_path} job_id={getattr(job, 'id', None)} args_len={len(args)} kwargs_keys={list(kwargs.keys())}")
        except Exception as e:
            logging.error(f"[TASK-QUEUE] Failed to enqueue RQ job func={func_path}: {e}")
        return
    # Fallback: resolve and run via in-memory queue
    module_name, func_name = func_path.split(":")
    mod = __import__(module_name, fromlist=[func_name])
    func = getattr(mod, func_name)
    submit_task(func, *args, **kwargs)


def submit_task(func: Callable, *args: Any, **kwargs: Any) -> None:
    if _rq_queue is not None:
        # Enqueue function directly to RQ
        try:
            job = _rq_queue.enqueue(func, *args, **kwargs)
            logging.info(f"[TASK-QUEUE] Enqueued RQ job func={func.__module__}.{func.__name__} job_id={getattr(job, 'id', None)} args_len={len(args)} kwargs_keys={list(kwargs.keys())}")
        except Exception as e:
            logging.error(f"[TASK-QUEUE] Failed to enqueue RQ job func={func.__module__}.{func.__name__}: {e}")
        return
    if not _started:
        start_worker()
    logging.info(f"[TASK-QUEUE] Queued in-memory task func={getattr(func, '__name__', str(func))} args_len={len(args)} kwargs_keys={list(kwargs.keys())}")
    _tasks.put((func, args, kwargs))
