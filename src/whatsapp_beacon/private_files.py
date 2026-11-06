"""Owner-only creation helpers for files that hold monitored contacts' presence history."""
import os
from pathlib import Path


def make_private_dir(path) -> None:
    """Create a directory (and parents); a directory created here is owner-only (0700).

    Existing directories are left alone: the path may be operator-chosen and shared.
    """
    Path(path).mkdir(parents=True, exist_ok=True, mode=0o700)


def create_private_file(path) -> None:
    """Make sure the file exists and is owner-only (0600) before any data is written to it.

    The file is created with 0600 so there is no window where it is readable by others, and a
    file left over from an earlier run with a wider mode is tightened. Callers then write to
    the path normally; overwriting an existing file keeps its mode.
    """
    path = Path(path)
    os.close(os.open(path, os.O_WRONLY | os.O_CREAT, 0o600))
    try:
        path.chmod(0o600)
    except OSError:
        # Some mounted filesystems do not support chmod; not fatal for operation.
        pass
