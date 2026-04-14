"""
handlers/zipmod_handler.py — Parse .zipmod files via manifest.xml.
"""

import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ZipmodInfo:
    path: Path
    guid: str = ""
    name: str = ""
    version: str = ""
    author: str = ""
    game: str = ""
    has_manifest: bool = False
    is_corrupt: bool = False

    @property
    def unknown(self) -> bool:
        return not self.has_manifest or not self.guid


def parse_zipmod(filepath: Path) -> ZipmodInfo:
    """Open a .zipmod, read manifest.xml, return metadata."""
    info = ZipmodInfo(path=filepath)
    try:
        with zipfile.ZipFile(filepath, "r") as zf:
            names_lower = {n.lower(): n for n in zf.namelist()}
            manifest_key = names_lower.get("manifest.xml")
            if manifest_key is None:
                return info  # has_manifest stays False
            info.has_manifest = True
            data = zf.read(manifest_key)
            root = ET.fromstring(data.decode("utf-8", errors="replace"))
            info.guid    = (root.findtext("guid")    or "").strip()
            info.name    = (root.findtext("name")    or "").strip()
            info.version = (root.findtext("version") or "").strip()
            info.author  = (root.findtext("author")  or "").strip()
            info.game    = (root.findtext("game")    or "").strip()
    except zipfile.BadZipFile:
        info.is_corrupt = True
    except Exception:
        info.is_corrupt = True
    return info
