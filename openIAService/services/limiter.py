from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from decouple import config

# Configure storage at construction. If REDIS_URL is not set, fallback to in-memory.
_REDIS_URL = config('REDIS_URL', default='')
_STORAGE_URI = _REDIS_URL if _REDIS_URL else 'memory://'

# Limiter singleton to be initialized in main.py via limiter.init_app(app)
limiter = Limiter(key_func=get_remote_address, default_limits=[], storage_uri=_STORAGE_URI)
