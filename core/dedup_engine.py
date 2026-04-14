"""
core/dedup_engine.py — Multi-phase duplicate detection with keeper selection.
"""

from __future__ import annotations

import concurrent.futures
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from natsort import natsorted

from core import hasher, index_db, settings
from core.scanner import FileEntry
from handlers.zipmod_handler import ZipmodInfo
from handlers.characard_handler import CharaCardInfo
from handlers.coord_handler import CoordInfo
from handlers.scene_handler import SceneInfo


# ── Result types ─────────────────────────────────────────────────────────────

CATEGORY_DUPLICATE        = "duplicate"
CATEGORY_OLDER_VERSION    = "older_version"
CATEGORY_POSSIBLE_DUP     = "possible_duplicate"   # same GUID+ver, different hash
CATEGORY_MISPLACED        = "misplaced"
CATEGORY_UNKNOWN_METADATA = "unknown_metadata"
CATEGORY_ORPHANED         = "orphaned"


@dataclass
class DedupResult:
    filepath: Path
    category: str
    mode: str                         # move / report / inbox
    reason: str                       # human-readable description
    keeper: Optional[Path] = None     # which file is kept (if duplicate/old ver)
    scene_warning_count: int = 0      # number of scenes referencing this mod
    zipmod_info: Optional[ZipmodInfo] = None  # populated for zipmods
    chara_info: Optional[CharaCardInfo] = None  # populated for character cards
    coord_info: Optional[CoordInfo] = None      # populated for coordinate cards
    scene_info: Optional[SceneInfo] = None      # populated for studio scenes
    full_hash: str = ""


# ── Keeper selection helpers ─────────────────────────────────────────────────

def _keeper_score(entry: FileEntry, path: Path) -> tuple:
    """
    Lower score = higher priority keeper.
    Priority:
      1. Protected/report folder → highest priority (always kept)
      2. Depth of path within HS2 root (deeper = more organised = better)
      3. Newer mtime = better
    """
    mode_score = 0 if entry.mode == "report" else 1
    depth = len(path.parts)
    return (mode_score, -depth, -entry.mtime)


def _pick_keeper(entries: list[FileEntry]) -> FileEntry:
    """Return the entry that should be kept (lowest score = winner)."""
    return min(entries, key=lambda e: _keeper_score(e, e.path))


# ── Version comparison ────────────────────────────────────────────────────────

def _newest_version_index(versions: list[str]) -> int:
    """Return index of the newest version using natsort."""
    if not versions:
        return 0
    sorted_desc = natsorted(enumerate(versions), key=lambda x: x[1], reverse=True)
    return sorted_desc[0][0]


# ── Main engine ───────────────────────────────────────────────────────────────

class DedupEngine:
    def __init__(
        self,
        files: list[FileEntry],
        zipmod_infos: dict[str, ZipmodInfo],   # path str → ZipmodInfo
        progress_callback=None,
    ):
        self.files = files
        self.zipmod_infos = zipmod_infos
        self.progress_callback = progress_callback or (lambda msg, pct: None)
        self.results: list[DedupResult] = []

    def _emit(self, msg: str, pct: int):
        self.progress_callback(msg, pct)

    def run(self) -> list[DedupResult]:
        self.results = []
        files = [f for f in self.files if not settings.is_ignored(str(f.path))]

        # Phase 2 — Size grouping
        self._emit("Grouping by file size…", 10)
        by_size: dict[int, list[FileEntry]] = defaultdict(list)
        for f in files:
            by_size[f.size].append(f)
        candidates = {sz: lst for sz, lst in by_size.items() if len(lst) > 1}

        # Phase 3 — Partial hash
        self._emit("Computing partial hashes…", 25)
        by_partial: dict[str, list[FileEntry]] = defaultdict(list)
        
        p3_entries = []
        for lst in candidates.values():
            p3_entries.extend(lst)

        # 1. Pre-check cache on main thread to avoid SQLite concurrent locks
        tasks_p3 = []
        for entry in p3_entries:
            ph = index_db.get_partial_hash(str(entry.path))
            if ph:
                by_partial[ph].append(entry)
            else:
                tasks_p3.append(entry)

        # 2. Hash remaining files concurrently
        if tasks_p3:
            total_p3 = len(tasks_p3)
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Map yields results in order, which is perfectly fine here.
                # Hashing releases the GIL, so this will saturate disk I/O.
                results = executor.map(lambda e: (e, hasher.partial_hash(e.path)), tasks_p3)
                for i, (entry, ph) in enumerate(results):
                    if ph:
                        index_db.update_hashes(str(entry.path), ph, "")
                        by_partial[ph].append(entry)
                    if i % 50 == 0:
                        self._emit(f"Computing partial hashes ({i}/{total_p3})…", 25 + int(20 * i / max(1, total_p3)))

        candidates2 = {h: lst for h, lst in by_partial.items() if len(lst) > 1}

        # Phase 4 — Full hash
        self._emit("Computing full hashes…", 45)
        by_full: dict[str, list[FileEntry]] = defaultdict(list)
        
        p4_entries = []
        for lst in candidates2.values():
            p4_entries.extend(lst)

        # 1. Pre-check cache sequentially
        tasks_p4 = []
        for entry in p4_entries:
            fh = index_db.get_full_hash(str(entry.path))
            if fh and fh != "":
                by_full[fh].append(entry)
                entry._full_hash = fh  # type: ignore[attr-defined]
            else:
                tasks_p4.append(entry)

        # 2. Compute full hashes concurrently
        if tasks_p4:
            total_p4 = len(tasks_p4)
            with concurrent.futures.ThreadPoolExecutor() as executor:
                results = executor.map(lambda e: (e, hasher.full_hash(e.path)), tasks_p4)
                for i, (entry, fh) in enumerate(results):
                    if fh:
                        ph_cached = index_db.get_partial_hash(str(entry.path)) or ""
                        index_db.update_hashes(str(entry.path), ph_cached, fh)
                        by_full[fh].append(entry)
                        entry._full_hash = fh  # type: ignore[attr-defined]
                    if i % 10 == 0:
                        self._emit(f"Computing full hashes ({i}/{total_p4})…", 45 + int(15 * i / max(1, total_p4)))

        # Exact duplicates
        self._emit("Identifying exact duplicates…", 60)
        exact_dup_results = self._resolve_exact_duplicates(by_full)
        self.results.extend(exact_dup_results)

        # Phase 5 — Zipmod version analysis (all zipmods, not just dup candidates)
        self._emit("Analysing zipmod versions…", 75)
        already_flagged = {str(r.filepath) for r in self.results}
        version_results = self._resolve_zipmod_versions(already_flagged)
        self.results.extend(version_results)

        # Scene dependency warning counts
        self._emit("Cross-referencing scene dependencies…", 88)
        for r in self.results:
            if r.zipmod_info and r.zipmod_info.guid:
                r.scene_warning_count = index_db.get_scene_count_for_guid(r.zipmod_info.guid)

        self._emit("Complete.", 100)
        return self.results

    def _resolve_exact_duplicates(
        self, by_full: dict[str, list[FileEntry]]
    ) -> list[DedupResult]:
        results = []
        for fh, group in by_full.items():
            if len(group) < 2:
                continue

            keeper = _pick_keeper(group)
            for entry in group:
                if entry is keeper:
                    continue
                zi = self.zipmod_infos.get(str(entry.path))
                results.append(DedupResult(
                    filepath=entry.path,
                    category=CATEGORY_DUPLICATE,
                    mode=entry.mode,
                    reason=f"Byte-identical copy of {keeper.path.name}",
                    keeper=keeper.path,
                    zipmod_info=zi,
                    full_hash=fh,
                ))
        return results

    def _resolve_zipmod_versions(self, already_flagged: set[str]) -> list[DedupResult]:
        """Find older versions by grouping all zipmods by GUID."""
        results = []
        by_guid: dict[str, list[tuple[FileEntry, ZipmodInfo]]] = defaultdict(list)
        same_guid_diff_hash: dict[str, list[tuple[FileEntry, ZipmodInfo]]] = defaultdict(list)

        for entry in self.files:
            if entry.file_type != "zipmod":
                continue
            if str(entry.path) in already_flagged:
                continue
            zi = self.zipmod_infos.get(str(entry.path))
            if not zi or not zi.guid:
                continue
            by_guid[zi.guid].append((entry, zi))

        for guid, items in by_guid.items():
            if len(items) < 2:
                continue

            # Check if all have same version
            versions = [zi.version for _, zi in items]
            hashes = [
                index_db.get_full_hash(str(e.path)) or ""
                for e, _ in items
            ]
            unique_versions = set(versions)
            unique_hashes = set(h for h in hashes if h)

            if len(unique_versions) == 1 and len(unique_hashes) > 1:
                # Same GUID, same version, different hash → possible duplicate
                keeper_entry, keeper_zi = max(
                    items, key=lambda x: _keeper_score(x[0], x[0].path)
                )
                for entry, zi in items:
                    if entry is keeper_entry:
                        continue
                    results.append(DedupResult(
                        filepath=entry.path,
                        category=CATEGORY_POSSIBLE_DUP,
                        mode=entry.mode,
                        reason=f"Same GUID+version ({zi.version}) but different file hash — possible repackage",
                        keeper=keeper_entry.path,
                        zipmod_info=zi,
                    ))
                continue

            # Different versions — flag older ones
            newest_idx = _newest_version_index(versions)
            keeper_entry, keeper_zi = items[newest_idx]

            for i, (entry, zi) in enumerate(items):
                if i == newest_idx:
                    continue
                results.append(DedupResult(
                    filepath=entry.path,
                    category=CATEGORY_OLDER_VERSION,
                    mode=entry.mode,
                    reason=(
                        f"Older version {zi.version or '?'} — "
                        f"v{keeper_zi.version or '?'} exists at {keeper_entry.path.name}"
                    ),
                    keeper=keeper_entry.path,
                    zipmod_info=zi,
                ))
        return results
