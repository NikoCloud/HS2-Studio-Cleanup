"""
core/org_engine.py — File organisation rules and misplacement detection.
Determines correct HS2 destination for a given file type.
"""

from pathlib import Path
from typing import Optional

from handlers.zipmod_handler import ZipmodInfo
from handlers.characard_handler import CharaCardInfo
from handlers.coord_handler import CoordInfo
from handlers.scene_handler import SceneInfo


# Known HS2 folder rules (relative to hs2_root, lowercase)
_ZIPMOD_ROOTS_LOWER = {"mods"}
_CHARA_ROOTS_LOWER  = {"userdata\\chara", "userdata/chara"}
_SCENE_ROOTS_LOWER  = {"userdata\\studio\\scene", "userdata/studio/scene",
                        "userdata\\studio", "userdata/studio"}
_COORD_ROOTS_LOWER  = {"userdata\\coordinate", "userdata/coordinate"}


def _rel_lower(filepath: Path, hs2_root: Path) -> str:
    try:
        return str(filepath.relative_to(hs2_root)).lower()
    except ValueError:
        return str(filepath).lower()


def is_zipmod_misplaced(filepath: Path, hs2_root: Path) -> bool:
    rel = _rel_lower(filepath, hs2_root)
    return not any(rel.startswith(r) for r in _ZIPMOD_ROOTS_LOWER)


def is_chara_card_misplaced(filepath: Path, hs2_root: Path) -> bool:
    rel = _rel_lower(filepath, hs2_root)
    return not any(rel.startswith(r) for r in _CHARA_ROOTS_LOWER)


def is_scene_misplaced(filepath: Path, hs2_root: Path) -> bool:
    rel = _rel_lower(filepath, hs2_root)
    return not any(rel.startswith(r) for r in _SCENE_ROOTS_LOWER)


def is_coord_misplaced(filepath: Path, hs2_root: Path) -> bool:
    rel = _rel_lower(filepath, hs2_root)
    return not any(rel.startswith(r) for r in _COORD_ROOTS_LOWER)


def get_zipmod_destination(hs2_root: Path, author: str) -> Path:
    """Return the correct destination folder for a zipmod given its author."""
    safe_author = _sanitise_folder_name(author) if author else "Unknown_Author"
    return hs2_root / "mods" / "MyMods" / safe_author


def get_community_subpath(filepath: Path, hs2_root: Path, canonical_base: str) -> Path:
    """
    Extracts the author/community folder name (the parent of UserData) and any nested subdirectories
    after the canonical base, merging them into a single relative Path object.
    """
    try:
        parts_lower = [p.lower() for p in filepath.parts]
        
        # 1. Extract Author (Parent directory of 'UserData')
        author = None
        if 'userdata' in parts_lower:
            ud_idx = parts_lower.index('userdata')
            parent_idx = len(filepath.parts) - 1 - ud_idx
            parent_path = filepath.parents[parent_idx]
            
            # Ensure the parent is not the root of the drive or the HS2 root itself
            if parent_path != hs2_root and hs2_root in parent_path.parents:
                author = parent_path.name

        # 2. Extract Suffix (Any subdirectories after the canonical base, before the filename)
        base_parts = [p.lower() for p in Path(canonical_base).parts]
        match_idx = -1
        # Find exactly where the canonical base sequence appears in the filepath
        for i in range(len(parts_lower) - len(base_parts) + 1):
            if parts_lower[i:i+len(base_parts)] == base_parts:
                match_idx = i
                break
                
        suffix_path = Path()
        if match_idx != -1:
            suffix_parts = filepath.parts[match_idx + len(base_parts) : -1]
            if suffix_parts:
                suffix_path = Path(*suffix_parts)

        # 3. Assemble the relative extra path
        extra = Path()
        if author:
            if 'community' not in author.lower() and 'mods' not in author.lower():
                extra = extra / '[Community]' / author
            else:
                extra = extra / author
                
        if suffix_path != Path():
            extra = extra / suffix_path
            
        return extra
    except Exception:
        return Path()


def get_chara_destination(filepath: Path, hs2_root: Path, gender: str) -> Path:
    """Return destination for a character card, preserving author and subfolders."""
    gender = gender if gender in ("female", "male") else "unsorted"
    base_dest = hs2_root / "UserData" / "chara" / gender
    
    subpath = get_community_subpath(filepath, hs2_root, f"userdata/chara/{gender}")
    if str(subpath) == ".":
        return base_dest
    return base_dest / subpath


def get_coord_destination(filepath: Path, hs2_root: Path, gender: str) -> Path:
    """
    Return destination for a coordinate card, preserving author and subfolders.
    If it's sitting inside a subfolder inside chara or coordinate, preserve it.
    """
    gender = gender if gender in ("female", "male") else "unsorted"
    base_dest = hs2_root / "UserData" / "coordinate" / gender
    
    # Check if it was in the chara folder previously (extract its subpath from there)
    subpath = get_community_subpath(filepath, hs2_root, f"userdata/chara/{gender}")
    if str(subpath) != ".":
        return base_dest / subpath
        
    # Check if it was in the coordinate folder previously
    subpath = get_community_subpath(filepath, hs2_root, f"userdata/coordinate/{gender}")
    if str(subpath) != ".":
        return base_dest / subpath
        
    return base_dest


def get_scene_destination(hs2_root: Path) -> Path:
    return hs2_root / "UserData" / "studio" / "scene"


def get_coordinate_destination(hs2_root: Path) -> Path:
    return hs2_root / "UserData" / "coordinate"


def detect_misplacement(
    filepath: Path,
    hs2_root: Path,
    chara_info: Optional[CharaCardInfo] = None,
    coord_info: Optional[CoordInfo] = None,
    scene_info: Optional[SceneInfo] = None,
    zipmod_info: Optional[ZipmodInfo] = None,
) -> Optional[tuple[str, Path]]:
    """
    Returns (reason_text, correct_destination) if misplaced, else None.
    """
    # Zipmod in wrong place
    if zipmod_info and not zipmod_info.is_corrupt:
        if is_zipmod_misplaced(filepath, hs2_root):
            dest = get_zipmod_destination(hs2_root, zipmod_info.author)
            return (f".zipmod found outside mods/ — belongs in mods/MyMods/{_sanitise_folder_name(zipmod_info.author) or 'Unknown_Author'}/", dest)

    # Character card in wrong place
    if chara_info and chara_info.is_chara_card:
        if is_chara_card_misplaced(filepath, hs2_root):
            dest = get_chara_destination(filepath, hs2_root, chara_info.gender)
            return (f"Character card found outside UserData/chara/ — belongs in {dest.relative_to(hs2_root)}", dest)

    # Coordinate card in wrong place
    if coord_info and coord_info.is_coord:
        if is_coord_misplaced(filepath, hs2_root):
            dest = get_coord_destination(filepath, hs2_root, coord_info.gender)
            return (f"Coordinate card found outside UserData/coordinate/ — belongs in {dest.relative_to(hs2_root)}", dest)

    # Scene in wrong place
    if scene_info and scene_info.is_scene:
        if is_scene_misplaced(filepath, hs2_root):
            dest = get_scene_destination(hs2_root)
            return ("Studio scene found outside UserData/studio/scene/", dest)

    return None


def _sanitise_folder_name(name: str) -> str:
    """Make a name safe for use as a Windows folder name."""
    bad_chars = r'\/:*?"<>|'
    result = "".join(c if c not in bad_chars else "_" for c in name.strip())
    return result[:64] or "Unknown"
