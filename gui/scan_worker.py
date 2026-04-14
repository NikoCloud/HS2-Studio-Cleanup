"""
gui/scan_worker.py — QThread worker that runs the full scan pipeline.
Emits signals so the GUI stays responsive.
"""

from __future__ import annotations

import concurrent.futures
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from core import index_db, settings
from core.scanner import scan, FileEntry
from core.hasher import partial_hash, full_hash
from core.dedup_engine import DedupEngine, DedupResult, CATEGORY_MISPLACED, CATEGORY_UNKNOWN_METADATA
from core.org_engine import detect_misplacement
from handlers.zipmod_handler import parse_zipmod, ZipmodInfo
from handlers.characard_handler import parse_chara_card
from handlers.coord_handler import parse_coord_card, CoordInfo
from handlers.scene_handler import parse_scene


class ScanWorker(QThread):
    # Signals
    progress     = pyqtSignal(str, int, str)   # phase_text, pct, current_file
    file_found   = pyqtSignal(int)             # running total file count
    result_ready = pyqtSignal(object)          # one DedupResult at a time
    finished     = pyqtSignal(int, int, int)   # total_files, total_results, misplaced_count
    error        = pyqtSignal(str)

    def __init__(
        self,
        hs2_root: Path,
        scan_zipmods: bool = True,
        scan_png: bool = True,
        scan_other: bool = True,
        dry_run: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.hs2_root     = hs2_root
        self.scan_zipmods = scan_zipmods
        self.scan_png     = scan_png
        self.scan_other   = scan_other
        self.dry_run      = dry_run
        self._abort       = False

    def abort(self):
        self._abort = True

    def run(self):
        try:
            self._run()
        except Exception as e:
            self.error.emit(str(e))

    def _run(self):
        hs2_root = self.hs2_root
        index_db.init_db(hs2_root)

        # ── Phase 1: Discovery ────────────────────────────────────────────
        self.progress.emit("Discovering files…", 0, "")
        all_entries: list[FileEntry] = []
        known_paths: set[str] = set()

        for entry in scan(hs2_root, self.scan_zipmods, self.scan_png, self.scan_other):
            if self._abort:
                return
            path_str = str(entry.path)
            known_paths.add(path_str)

            # Check index cache
            if not index_db.is_unchanged(path_str, entry.size, entry.mtime):
                index_db.upsert_file(path_str, entry.size, entry.mtime, entry.file_type)

            all_entries.append(entry)
            self.file_found.emit(len(all_entries))

        # Prune stale index entries
        index_db.remove_missing_files(known_paths)

        total = len(all_entries)
        self.progress.emit(f"Found {total:,} files. Parsing metadata…", 5, "")

        # ── Phase: Metadata parsing ───────────────────────────────────────
        zipmod_infos: dict[str, ZipmodInfo] = {}
        misplaced_results: list[DedupResult] = []
        unknown_results:   list[DedupResult] = []

        def _parse_meta(entry: FileEntry):
            chara_info = coord_info = scene_info = zipmod_info = None
            if entry.file_type == "zipmod":
                zipmod_info = parse_zipmod(entry.path)
            elif entry.file_type == "png":
                folder_str = str(entry.path.parent)
                chara_info = parse_chara_card(entry.path, folder_str)
                if not chara_info.is_chara_card:
                    coord_info = parse_coord_card(entry.path, folder_str)
                    if not coord_info.is_coord:
                        scene_info = parse_scene(entry.path)
            return entry, zipmod_info, chara_info, coord_info, scene_info

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(_parse_meta, entry): entry for entry in all_entries}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                if self._abort:
                    return
                entry, zipmod_info, chara_info, coord_info, scene_info = future.result()
                # Update progress less often to avoid GUI flooding
                if i % 100 == 0:
                    pct = 5 + int(20 * i / max(total, 1))
                    self.progress.emit(f"Parsing metadata… ({i:,}/{total:,})", pct, entry.path.name)

                if entry.file_type == "zipmod" and zipmod_info:
                    zi = zipmod_info
                    zipmod_infos[str(entry.path)] = zi

                    fid = index_db.get_file_id(str(entry.path))
                    if fid:
                        index_db.upsert_zipmod_meta(
                            fid, zi.guid, zi.name, zi.version, zi.author, zi.game
                        )

                    if zi.is_corrupt or not zi.has_manifest:
                        unknown_results.append(DedupResult(
                            filepath=entry.path,
                            category=CATEGORY_UNKNOWN_METADATA,
                            mode=entry.mode,
                            reason="No manifest.xml" if not zi.has_manifest else "Corrupt .zipmod archive",
                            zipmod_info=zi,
                        ))
                        continue  # Don't also flag as misplaced

                elif entry.file_type == "png":
                    if scene_info and scene_info.is_scene:
                        si = scene_info
                        fid = index_db.get_file_id(str(entry.path))
                        if fid and si.mod_guids:
                            index_db.upsert_scene_dependencies(fid, si.mod_guids)

                # Misplacement check
                placement = detect_misplacement(
                    entry.path, hs2_root, chara_info, coord_info, scene_info, zipmod_info
                )
                if placement:
                    reason, dest = placement
                    misplaced_results.append(DedupResult(
                        filepath=entry.path,
                        category=CATEGORY_MISPLACED,
                        mode=entry.mode,
                        reason=reason,
                        keeper=dest,  # re-used as "suggested destination"
                        zipmod_info=zipmod_info,
                        chara_info=chara_info,
                        coord_info=coord_info,
                        scene_info=scene_info,
                    ))

        # Emit unknown / misplaced immediately so they show up fast
        for r in unknown_results + misplaced_results:
            self.result_ready.emit(r)

        # ── Phase: Dedup ──────────────────────────────────────────────────
        def _prog(msg: str, pct: int):
            if self._abort:
                return
            mapped_pct = 25 + int(70 * pct / 100)
            self.progress.emit(msg, mapped_pct, "")

        engine = DedupEngine(all_entries, zipmod_infos, _prog)
        results = engine.run()

        for r in results:
            if self._abort:
                return
            self.result_ready.emit(r)

        self.finished.emit(total, len(results) + len(unknown_results) + len(misplaced_results),
                           len(misplaced_results))
