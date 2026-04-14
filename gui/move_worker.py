"""
gui/move_worker.py — Background worker for file move and sort-misplaced operations.

Runs entirely off the main thread; communicates via signals.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from core import movement_engine
from core.dedup_engine import DedupResult


class MoveWorker(QThread):
    """
    Moves a list of checked DedupResults to the _Cleanup directory
    (or writes report entries) off the main thread.

    Signals:
        progress(phase, pct, current_file)
        log(message)
        finished(moved_count, reported_count)
        error(message)
    """

    progress       = pyqtSignal(str, int, str)   # phase, pct, current filename
    log            = pyqtSignal(str)             # log line for the console
    file_processed = pyqtSignal(str, str)        # filepath, status ("moved"|"reported")
    finished       = pyqtSignal(int, int)        # moved_count, reported_count
    error          = pyqtSignal(str)

    def __init__(
        self,
        results: list[DedupResult],
        hs2_root: Path,
        dry_run: bool,
        parent=None,
    ):
        super().__init__(parent)
        self._results  = results
        self._hs2_root = hs2_root
        self._dry_run  = dry_run
        self._abort    = False

    def abort(self):
        self._abort = True

    def run(self):
        try:
            total = len(self._results)
            moved = reported = 0
            dry_run_findings: list[dict] = []

            for i, r in enumerate(self._results):
                if self._abort:
                    break

                pct = int(100 * i / max(total, 1))
                self.progress.emit("Moving files…", pct, r.filepath.name)

                if r.mode == "report":
                    subfolder = r.filepath.parts[-2] if len(r.filepath.parts) > 1 else "unknown"
                    movement_engine.write_report_entry(
                        self._hs2_root, subfolder,
                        r.filepath, r.category, r.reason,
                    )
                    self.log.emit(f"[REPORT] {r.filepath.name} — {r.reason}")
                    self.file_processed.emit(str(r.filepath), "reported")
                    reported += 1
                elif self._dry_run:
                    dry_run_findings.append({
                        "file":     str(r.filepath),
                        "category": r.category,
                        "reason":   r.reason,
                        "keeper":   str(r.keeper) if r.keeper else None,
                    })
                    self.log.emit(f"[DRY RUN] Would move: {r.filepath.name} ({r.category})")
                    # Dry run: no file_processed emitted — nothing actually happened
                else:
                    dest = movement_engine.move_to_cleanup(
                        r.filepath, self._hs2_root, r.category, r.reason,
                        related_file=r.keeper,
                    )
                    if dest:
                        self.log.emit(f"[{r.category.upper()}] Moved: {r.filepath.name}")
                        self.file_processed.emit(str(r.filepath), "moved")
                        moved += 1
                    else:
                        self.log.emit(f"[ERROR] Failed to move: {r.filepath.name}")

            if self._dry_run and dry_run_findings:
                report_path = movement_engine.write_dry_run_report(
                    self._hs2_root, dry_run_findings
                )
                self.log.emit(f"[DRY RUN] Report written → {report_path}")

            self.progress.emit("Done.", 100, "")
            self.finished.emit(moved, reported)

        except Exception as exc:
            self.error.emit(str(exc))


class SortMisplacedWorker(QThread):
    """
    Runs the Sort Misplaced pass: iterates _Cleanup/Misplaced/ and moves
    each file to its correct HS2 destination off the main thread.

    Signals:
        progress(phase, pct, current_file)
        log(message)
        finished(sorted_count)
        error(message)
    """

    progress = pyqtSignal(str, int, str)
    log      = pyqtSignal(str)
    finished = pyqtSignal(int)
    error    = pyqtSignal(str)

    def __init__(self, hs2_root: Path, dry_run: bool, parent=None):
        super().__init__(parent)
        self._hs2_root = hs2_root
        self._dry_run  = dry_run
        self._abort    = False

    def abort(self):
        self._abort = True

    def run(self):
        try:
            from handlers.zipmod_handler import parse_zipmod
            from handlers.characard_handler import parse_chara_card
            from handlers.coord_handler import parse_coord_card
            from handlers.scene_handler import parse_scene
            from core.org_engine import (
                get_zipmod_destination, get_chara_destination, get_coord_destination, get_scene_destination
            )

            misplaced_dir = self._hs2_root / "_Cleanup" / "Misplaced"
            if not misplaced_dir.exists():
                self.finished.emit(0)
                return

            files = [
                fp for fp in misplaced_dir.rglob("*")
                if fp.is_file() and not fp.name.startswith("_manifest")
            ]
            total = len(files)
            sorted_count = 0

            for i, fp in enumerate(files):
                if self._abort:
                    break

                pct = int(100 * i / max(total, 1))
                self.progress.emit("Sorting misplaced files…", pct, fp.name)

                ext = fp.suffix.lower()
                dest_dir = None

                if ext == ".zipmod":
                    zi = parse_zipmod(fp)
                    dest_dir = get_zipmod_destination(self._hs2_root, zi.author)

                elif ext == ".png":
                    ci = parse_chara_card(fp)
                    if ci.is_chara_card:
                        dest_dir = get_chara_destination(fp, self._hs2_root, ci.gender)
                    else:
                        coord_info = parse_coord_card(fp)
                        if coord_info.is_coord:
                            dest_dir = get_coord_destination(fp, self._hs2_root, coord_info.gender)
                        else:
                            si = parse_scene(fp)
                            if si.is_scene:
                                dest_dir = get_scene_destination(self._hs2_root)

                if dest_dir:
                    movement_engine.move_to_destination(
                        fp, dest_dir, "sorted from misplaced", dry_run=self._dry_run
                    )
                    verb = "Would sort" if self._dry_run else "Sorted"
                    self.log.emit(f"[SORT] {verb}: {fp.name} → {dest_dir}")
                    sorted_count += 1

            self.progress.emit("Done.", 100, "")
            self.finished.emit(sorted_count)

        except Exception as exc:
            self.error.emit(str(exc))
