from django.core.cache import cache

def get_slot_lock_key(barber_id: int, date_time_str: str) -> str:
    """
    Returns the cache key for a specific slot.
    Format: slot_lock:<barber_id>:<YYYY-MM-DDTHH:MM:SS>
    """
    return f"slot_lock:{barber_id}:{date_time_str}"

def lock_slot(barber_id: int, date_time_str: str, ttl: int = 900) -> bool:
    """
    Attempts to lock a slot for `ttl` seconds (default 15 minutes).
    Returns True if successful, False if already locked.
    Uses SET NX EX under the hood in Redis via Django's cache.add.
    """
    key = get_slot_lock_key(barber_id, date_time_str)
    # cache.add only sets the key if it does not exist (atomic)
    return cache.add(key, 'locked', ttl)

def unlock_slot(barber_id: int, date_time_str: str):
    """
    Releases a locked slot.
    """
    key = get_slot_lock_key(barber_id, date_time_str)
    cache.delete(key)

def is_slot_locked(barber_id: int, date_time_str: str) -> bool:
    """
    Checks if a slot is currently locked.
    """
    key = get_slot_lock_key(barber_id, date_time_str)
    return cache.get(key) is not None
