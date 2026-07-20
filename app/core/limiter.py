from slowapi import Limiter
from slowapi.util import get_remote_address

# Instantiate rate limiter using remote address as default throttle key
limiter = Limiter(key_func=get_remote_address)
