"""
core/scanner.py — File discovery with folder protection mode tagging.
"""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

from core import settings

# Extensions we actively care about for deep parsing
ZIPMOD_EXT  = {".zipmod"}
PNG_EXT     = {".png"}
DLL_EXT     = {".dll"}

# Always skip our own output folders
SKIP_NAMES_LOWER = {"_cleanup", "_studiocleanup.db", "_studiocleanup.log"}


@dataclass
class FileEntry:
    path: Path
    size: int
    mtime: float
    extension: str
    file_type: str        # 'zipmod' | 'png' | 'dll' | 'other'
    mode: str             # 'move' | 'report' | 'inbox'
    top_folder: str       # top-level HS2 subfolder name


def classify_extension(ext: str) -> str:
    ext = ext.lower()
    if ext in ZIPMOD_EXT:
        return "zipmod"
    if ext in PNG_EXT:
        return "png"
    if ext in DLL_EXT:
        return "dll"
    return "other"


def scan(
    hs2_root: Path,
    scan_zipmods: bool = True,
    scan_png: bool = True,
    scan_other: bool = True,
) -> Generator[FileEntry, None, None]:
    """
    Walk hs2_root recursively. Yields FileEntry for every relevant file.
    Skips _Cleanup/ and our own DB/log. Tags each file with its folder mode.
    """
    root_str = str(hs2_root)

    for dirpath, dirnames, filenames in os.walk(hs2_root):
        dir_path = Path(dirpath)

        # Prune skip dirs AND ignored dirs in place (modifies the walk)
        def _keep(d: str, dp: Path = dir_path) -> bool:
            if d.lower() in SKIP_NAMES_LOWER:
                return False
            try:
                rel = (dp / d).relative_to(hs2_root)
                if settings.get_folder_mode(str(rel)) == "ignore":
                    return False
            except ValueError:
                pass
            return True

        dirnames[:] = [d for d in dirnames if _keep(d)]

        # Determine top-level folder relative to root
        try:
            rel = dir_path.relative_to(hs2_root)
            top_folder = rel.parts[0] if rel.parts else ""
        except ValueError:
            top_folder = ""

        for filename in filenames:
            if filename.lower() in SKIP_NAMES_LOWER:
                continue
            filepath = dir_path / filename
            ext = filepath.suffix.lower()
            ftype = classify_extension(ext)

            # Apply scan options
            if ftype == "zipmod" and not scan_zipmods:
                continue
            if ftype == "png" and not scan_png:
                continue
            if ftype not in ("zipmod", "png") and not scan_other:
                continue

            try:
                stat = filepath.stat()
            except OSError:
                continue

            mode = settings.get_effective_mode_for_path(str(filepath), root_str)

            yield FileEntry(
                path=filepath,
                size=stat.st_size,
                mtime=stat.st_mtime,
                extension=ext,
                file_type=ftype,
                mode=mode,
                top_folder=top_folder,
            )
