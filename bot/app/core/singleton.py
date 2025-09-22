import os
import fcntl

def acquire_singleton_lock(lock_path: str) -> int:
    """Acquire a non-blocking exclusive file lock. Returns FD to keep process-held.
    Raises SystemExit if already locked by another process.
    """
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("Another bot instance is already running (singleton lock).")
    os.ftruncate(fd, 0)
    os.write(fd, str(os.getpid()).encode())
    os.fsync(fd)
    return fd


