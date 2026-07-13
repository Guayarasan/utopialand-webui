"""
Caché TTL en memoria de proceso.

Para agregados costosos (conteos, distribuciones, listas de valores
distintos) sobre una tabla de millones de filas, recalcular en cada
request es innecesario: los datos de logging no exigen consistencia al
segundo. Un caché simple con expiración reduce drásticamente la carga
sobre MySQL.

No es un caché distribuido (no usa Redis) a propósito: el proyecto corre
en Render como uno o pocos workers, así que un dict con lock es
suficiente y no agrega infraestructura extra.
"""

import threading
import time
from functools import wraps

_store = {}
_lock = threading.Lock()


def cache_get(key):
    with _lock:
        entry = _store.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if expires_at < time.monotonic():
            _store.pop(key, None)
            return None
        return value


def cache_set(key, value, ttl_seconds):
    with _lock:
        _store[key] = (value, time.monotonic() + ttl_seconds)


def cache_clear(prefix=None):
    with _lock:
        if prefix is None:
            _store.clear()
            return
        for key in [k for k in _store if k.startswith(prefix)]:
            _store.pop(key, None)


def cached(ttl_seconds, key_fn=None):
    """Decorador para memoizar el resultado de una función con TTL."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            cache_key = key_fn(*args, **kwargs) if key_fn else _default_key(fn, args, kwargs)
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                return cached_value
            result = fn(*args, **kwargs)
            cache_set(cache_key, result, ttl_seconds)
            return result

        wrapper.cache_clear_all = cache_clear
        return wrapper

    return decorator


def _default_key(fn, args, kwargs):
    return f"{fn.__module__}.{fn.__qualname__}:{args}:{sorted(kwargs.items())}"
