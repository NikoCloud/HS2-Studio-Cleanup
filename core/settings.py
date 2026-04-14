"""
core/settings.py — Persistent settings via config.json.
"""

import json
import sys
from pathlib import Path
from typing import Any

# When bundled by PyInstaller, __file__ resolves to a TEMP extraction directory
# that is destroyed when the app exits (hence settings never persisted).
# We must write config.json alongside the actual EXE (sys.executable),
# or next to main.py when running as a plain Python script.
if getattr(sys, "frozen", False):
    # Running as compiled EXE — use the folder containing the EXE
    _CONFIG_PATH = Path(sys.executable).parent / "config.json"
else:
    # Running as a normal Python script — use the project root
    _CONFIG_PATH = Path(__file__).parent.parent / "config.json"

_DEFAULTS: dict[str, Any] = {
    "hs2_root": "C:\\HS2",
    "first_run": True,
    "dry_run": False,
    "scan_options": {
        "zipmods": True,
        "chara_cards": True,
        "scenes": True,
        "other": True,
    },
    # Keys are relative paths from HS2 root in lowercase using forward slashes.
    # e.g. "bepinex", "bepinex/plugins", "userdata/studio/scene"
    # Values: "move" | "report" | "inbox" | "ignore"
    # Lookup walks up the path tree until a match is found, then falls back to "move".
    "folder_modes": {
        # -- Report: scan but never move -----------------------------------
        "abdata":                                  "report",
        "bepinex":                                 "report",
        "sideloader modpack":                      "report",
        "sideloader modpack - studio":             "report",
        "sideloader modpack - maps":               "report",
        "sideloader modpack - maps (hs2 game)":    "report",
        "sideloader modpack - exclusives":         "report",
        "sideloader modpack - exclusive hs2":      "report",
        "sideloader modpack - hs2pe":              "report",
        "sideloader modpack - bleeding edge":      "report",
        "sideloader modpack - uncensor selector":  "report",
        # -- Move: duplicates flagged and moveable -------------------------
        "mods/mymods":                             "move",
        "userdata":                                "move",
        # -- Ignore: skip entirely - no scan, no report -------------------
        "honeyselectstar2_data":                   "ignore",
        "honeyselectstar2vr_data":                 "ignore",
        "studioneostar2_data":                     "ignore",
        "monobleddingedge":                        "ignore",
        "defaultdata":                             "ignore",
        "temp":                                    "ignore",
        "manual":                                  "ignore",
        "manual_s":                                "ignore",
        "manual_v":                                "ignore",
        "bepinex_shim_backup":                     "ignore",
    },

    "inbox_folders": [],          # Absolute paths to treat as Inbox
    "ignored_files": [],          # Absolute paths to never flag
    "last_scan_root": "",
    "last_export_dir": "",
    "window_geometry": None,
}

_settings: dict[str, Any] = {}


def load() -> dict[str, Any]:
    global _settings
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            _settings = {**_DEFAULTS, **saved}
            # Deep-merge nested dicts
            for key in ("scan_options", "folder_modes"):
                _settings[key] = {**_DEFAULTS[key], **saved.get(key, {})}
        except Exception:
            _settings = dict(_DEFAULTS)
    else:
        _settings = dict(_DEFAULTS)
    return _settings


def save() -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(_settings, f, indent=2, ensure_ascii=False)


def get(key: str, default: Any = None) -> Any:
    return _settings.get(key, default)


def set(key: str, value: Any) -> None:
    _settings[key] = value


# ── Folder mode with full path inheritance ────────────────────────────────────

def _normalise_rel(rel_path: str) -> str:
    """Normalise a relative path to lowercase forward-slash format."""
    return rel_path.replace("\\", "/").strip("/").lower()


def get_folder_mode(rel_path: str) -> str:
    """
    Return the protection mode for a relative path.
    Walks up the directory tree until an explicit match is found.
    Falls back to 'move' if nothing is configured.

    rel_path: path relative to HS2 root (any separator, any case).
    """
    modes: dict = _settings.get("folder_modes", {})
    parts = _normalise_rel(rel_path).split("/")

    # Walk from most-specific to least-specific
    while parts:
        candidate = "/".join(parts)
        if candidate in modes:
            val = modes[candidate]
            if val != "inherit":
                return val
        parts.pop()

    return "move"  # global default


def set_folder_mode(rel_path: str, mode: str) -> None:
    """Set the mode for a relative path. Use 'inherit' to clear an override."""
    modes = _settings.setdefault("folder_modes", {})
    key = _normalise_rel(rel_path)
    if mode == "inherit":
        modes.pop(key, None)
    else:
        modes[key] = mode


def get_effective_mode_for_path(abs_path: str, hs2_root: str) -> str:
    """
    Full mode resolution for a file:
      1. Check if it's under an inbox folder → "inbox"
      2. Walk up the relative path tree looking for explicit mode assignments
      3. Fall back to "move"
    """
    abs_p = Path(abs_path)
    root = Path(hs2_root)

    # Inbox folders have highest priority
    for ib in _settings.get("inbox_folders", []):
        try:
            abs_p.relative_to(ib)
            return "inbox"
        except ValueError:
            pass

    try:
        rel = abs_p.relative_to(root)
        return get_folder_mode(str(rel.parent))
    except ValueError:
        return "move"


# ── Ignored file helpers ──────────────────────────────────────────────────────

def is_ignored(abs_path: str) -> bool:
    return abs_path in _settings.get("ignored_files", [])


def add_ignored(abs_path: str) -> None:
    lst = _settings.setdefault("ignored_files", [])
    if abs_path not in lst:
        lst.append(abs_path)
    save()


def remove_ignored(abs_path: str) -> None:
    lst = _settings.get("ignored_files", [])
    if abs_path in lst:
        lst.remove(abs_path)
    save()
