"""
handlers/characard_handler.py — Detect and classify HS2 character cards.

HS2 character cards are PNG files with game data appended after the PNG IEND chunk.
The embedded data contains character customisation info including gender.
"""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# HS2/AI character card marker strings found in embedded data
_HS2_MARKERS = (
    b"HS2CharaHeader",
    b"AIS_Chara",
    b"HS2_Chara",
    b"KoiKatuCharaHead",   # Koikatsu cards (not compatible but don't crash)
)

# PNG IEND chunk signature
_PNG_IEND = b"\x00\x00\x00\x00IEND\xaeB`\x82"


@dataclass
class CharaCardInfo:
    path: Path
    is_chara_card: bool = False
    gender: str = "unknown"   # 'female', 'male', 'unknown'
    game: str = "unknown"


def detect_gender_from_msgpack(tail_data: bytes) -> str:
    """
    Extracts the gender definitively from the MessagePack serialized 'Parameter' block.
    In the Illusion block structure, ChaFileParameter is a Map containing the key "sex", 
    which is serialized as 0xA3 0x73 0x65 0x78 (A3 = str of length 3, "sex").
    The value immediately following is the integer for sex (0x00=Male, 0x01=Female).
    """
    # Look for the exact MessagePack serialization of key "sex" (varstr length 3 "sex")
    sex_idx = tail_data.find(b'\xa3sex')
    if sex_idx != -1 and (sex_idx + 4) < len(tail_data):
        sex_val = tail_data[sex_idx + 4]
        if sex_val == 0x00:
            return "male"
        elif sex_val == 0x01:
            return "female"
            
    return "unknown"

def detect_gender_from_filename(filename: str) -> Optional[str]:
    """Check filename for M_/F_ and ChaF/ChaM patterns used by HS2/AI saves."""
    name = filename.lower()
    
    # Check for strong female indicators
    if "chaf" in name or "female" in name or name.startswith("f_") or name.startswith("f "):
        return "female"
        
    # Check for strong male indicators
    if "cham" in name or "male" in name or name.startswith("m_") or name.startswith("m "):
        return "male"
        
    return None


def is_hs2_chara_card(filepath: Path) -> tuple[bool, bytes]:
    """
    Returns (is_chara_card, embedded_data_bytes).
    Reads the PNG tail to find IEND and then looks for HS2 markers after it.
    """
    try:
        with open(filepath, "rb") as f:
            content = f.read()
    except OSError:
        return False, b""

    # Find IEND — the PNG end marker
    iend_pos = content.rfind(_PNG_IEND)
    if iend_pos == -1:
        return False, b""

    tail = content[iend_pos + len(_PNG_IEND):]
    if len(tail) < 4:
        return False, b""

    # A true character card has its marker immediately at the start of the embedded data block.
    # Usually at offset < 32. Anything deeper is a scene/pose/plugin data embedding a character card.
    for marker in _HS2_MARKERS:
        pos = tail.find(marker)
        if pos != -1 and pos < 64:
            game = "HS2" if b"HS2" in marker or b"AIS" in marker else "KKP"
            return True, tail

    return False, b""


def parse_chara_card(filepath: Path, current_folder: str = "") -> CharaCardInfo:
    info = CharaCardInfo(path=filepath)

    is_card, embedded = is_hs2_chara_card(filepath)
    if not is_card:
        return info

    info.is_chara_card = True

    # Multi-signal gender detection (priority order)
    gender: Optional[str] = None

    # 1. Try Exact Binary Parsing directly from MessagePack map
    gender = detect_gender_from_msgpack(embedded)
    if gender == "unknown": # If not found by MessagePack, try other methods
        # 2. Filename tags (HS2ChaF, AISChaM, etc)
        gender = detect_gender_from_filename(filepath.name)

    # 3. Current folder context
    if gender is None or gender == "unknown":
        folder_lower = current_folder.lower()
        if "female" in folder_lower:
            gender = "female"
        elif "male" in folder_lower:
            gender = "male"

    # 4. Default fallback (overwhelming majority of cards are female)
    info.gender = gender or "female"
    return info
