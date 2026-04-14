"""
core/hasher.py — Fast file hashing using xxhash (XXH3_128).
"""

import xxhash
from pathlib import Path

PARTIAL_CHUNK = 65_536   # 64 KB for quick pre-filter
FULL_CHUNK    = 1_048_576  # 1 MB for full hash


def partial_hash(filepath: Path) -> str:
    """Hash only the first 64 KB — fast pre-filter before full hash."""
    h = xxhash.xxh3_128()
    try:
        with open(filepath, "rb") as f:
            data = f.read(PARTIAL_CHUNK)
            if data:
                h.update(data)
    except OSError:
        return ""
    return h.hexdigest()


def full_hash(filepath: Path) -> str:
    """Hash the entire file in 1 MB chunks."""
    h = xxhash.xxh3_128()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(FULL_CHUNK):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()
