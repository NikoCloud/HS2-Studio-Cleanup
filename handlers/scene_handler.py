"""
handlers/scene_handler.py — Detect HS2 studio scene files and extract mod dependencies.

Scene files are PNG files with HS2 scene data embedded after IEND.
They embed Sideloader mod GUIDs via ExtensibleSaveFormat.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_PNG_IEND = b"\x00\x00\x00\x00IEND\xaeB`\x82"

# Markers that identify a scene PNG (not a character card)
_SCENE_MARKERS = (
    b"Studio00",
    b"KStudio",
    b"studioVersion",
    b"SceneInfo",
    b"H2Studio",
)

# Rough GUID pattern used by Sideloader: uuid4-like or dotted namespace
_GUID_PATTERN = re.compile(
    rb'(?:'
    rb'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'  # uuid4
    rb'|'
    rb'[\w][\w.\-]{4,64}'   # dotted namespace GUID like "com.author.modname"
    rb')'
)


@dataclass
class SceneInfo:
    path: Path
    is_scene: bool = False
    mod_guids: list[str] = field(default_factory=list)


def parse_scene(filepath: Path) -> SceneInfo:
    info = SceneInfo(path=filepath)
    try:
        with open(filepath, "rb") as f:
            content = f.read()
    except OSError:
        return info

    iend_pos = content.rfind(_PNG_IEND)
    if iend_pos == -1:
        return info

    tail = content[iend_pos + len(_PNG_IEND):]
    if len(tail) < 8:
        return info

    # Check for scene markers
    for marker in _SCENE_MARKERS:
        if marker in tail:
            info.is_scene = True
            break

    # If standard scene markers are missing, check for embedded character data.
    # Because true characards are caught by parse_chara_card earlier in the pipeline,
    # any file reaching here that still has a chara marker MUST be a scene/pose/coordinate.
    if not info.is_scene:
        for embedded_marker in (b"AIS_Chara", b"HS2_Chara", b"HS2CharaHeader"):
            if embedded_marker in tail:
                info.is_scene = True
                break

    if not info.is_scene:
        return info

    # Try to extract GUIDs from the embedded data
    # Sideloader stores mod GUIDs as strings in the save data
    # We scan for ascii-printable regions and apply GUID pattern
    guids: set[str] = set()

    # Extract GUID-like strings from the binary blob
    # First look for uuid4 style
    uuid4_pat = re.compile(
        rb'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
    )
    for m in uuid4_pat.finditer(tail):
        guids.add(m.group().decode("ascii"))

    # Also look for dotted namespace GUIDs surrounded by null bytes or quotes
    ns_pat = re.compile(rb'[\x22\x00]([\w][\w.\-]{5,63})[\x22\x00]')
    for m in ns_pat.finditer(tail):
        candidate = m.group(1).decode("ascii", errors="ignore")
        if "." in candidate and not candidate.startswith("Unity") and not candidate.startswith("System"):
            guids.add(candidate)

    info.mod_guids = list(guids)
    return info
