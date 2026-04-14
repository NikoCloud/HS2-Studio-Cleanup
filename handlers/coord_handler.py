"""
handlers/coord_handler.py — Detect and classify HS2 coordinate (clothing) cards.

Coordinate cards are PNG files with game data appended after the PNG IEND chunk.
The embedded data contains clothing customisation info including gender.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from handlers.characard_handler import detect_gender_from_msgpack, _PNG_IEND

# Known coordinate card markers
_COORD_MARKERS = (
    b"\xe3\x80\x90AIS_Clothes\xe3\x80\x91",     # 【AIS_Clothes】
    b"\xe3\x80\x90KoiKatuClothes\xe3\x80\x91",  # 【KoiKatuClothes】
    b"AIS_Clothes",
    b"KoiKatuClothes",
)


@dataclass
class CoordInfo:
    path: Path
    is_coord: bool = False
    gender: str = "unknown"   # 'female', 'male', 'unknown'


def detect_gender_from_filename(filename: str) -> Optional[str]:
    """Check filename for standard M/F coord patterns."""
    name = filename.lower()
    
    if "coordef" in name or name.startswith("f_") or name.startswith("f "):
        return "female"
    if "coordem" in name or name.startswith("m_") or name.startswith("m "):
        return "male"
        
    return None


def is_hs2_coord_card(filepath: Path) -> tuple[bool, bytes]:
    """
    Returns (is_coord_card, embedded_data_bytes).
    Reads the PNG tail to find IEND and then looks for Coord markers after it.
    """
    try:
        with open(filepath, "rb") as f:
            content = f.read(1024 * 1024 * 5) # 5MB max read to be safe, coords are usually small
    except OSError:
        return False, b""

    iend_pos = content.rfind(_PNG_IEND)
    if iend_pos == -1:
        return False, b""

    tail = content[iend_pos + len(_PNG_IEND):]
    if len(tail) < 4:
        return False, b""

    # A true coordinate card has its marker near the start of the embedded data block.
    for marker in _COORD_MARKERS:
        pos = tail.find(marker)
        if pos != -1 and pos < 64:
            return True, tail

    return False, b""


def parse_coord_card(filepath: Path, current_folder: str = "") -> CoordInfo:
    info = CoordInfo(path=filepath)

    is_card, embedded = is_hs2_coord_card(filepath)
    if not is_card:
        return info

    info.is_coord = True

    # Multi-signal gender detection (priority order defined by user)
    gender: Optional[str] = None

    # 1. Try Exact Binary Parsing directly from MessagePack map
    gender = detect_gender_from_msgpack(embedded)
    
    # 2. Filename standard markers
    if gender == "unknown":
        gender = detect_gender_from_filename(filepath.name)

    # 3. Current folder context
    if gender is None or gender == "unknown":
        folder_lower = current_folder.lower()
        if "female" in folder_lower or "f_" in folder_lower:
            gender = "female"
        elif "male" in folder_lower or "m_" in folder_lower:
            gender = "male"

    # 4. Default fallback (majority of cards are female)
    info.gender = gender or "female"
    return info
