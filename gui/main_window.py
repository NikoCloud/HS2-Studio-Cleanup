"""
gui/main_window.py — Main application window for HS2 Studio Cleanup.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QAction
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QGroupBox, QCheckBox, QProgressBar,
    QSplitter, QTextEdit, QComboBox, QScrollArea, QFrame, QSizePolicy,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout,
)

from core import settings, movement_engine, index_db
from gui.results_panel import ResultsPanel
from gui.detail_panel import DetailPanel
from gui.scan_worker import ScanWorker
from gui.move_worker import MoveWorker, SortMisplacedWorker
from gui.folder_tree_widget import FolderTreeWidget
from core.org_engine import get_zipmod_destination, get_chara_destination, get_scene_destination


_FOLDER_MODE_OPTIONS = ["move", "report", "inbox"]
_MODE_ICONS = {"move": "✅", "report": "🔒", "inbox": "📥"}

# Hardcoded list removed — folders are now loaded dynamically from HS2 root.


class FirstRunDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚠️  First Run Safety Warning")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        lbl = QLabel(
            "<h3 style='color:#e94560'>Before you scan, please back up important folders.</h3>"
            "<p>This is your first time running HS2 Studio Cleanup on this folder. "
            "While the app is non-destructive (nothing is deleted, files are moved to "
            "<code>_Cleanup/</code>), we strongly recommend backing up these folders first:</p>"
            "<ul><li><b>UserData/</b> — Character cards and scenes</li>"
            "<li><b>mods/MyMods/</b> — Your manually organised mods</li></ul>"
            "<p>You can always undo moves from the <b>Undo Last</b> button.</p>"
        )
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(lbl)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        settings.load()
        self.setWindowTitle("HS2 Studio Cleanup v0.01b1")
        self.setMinimumSize(1100, 760)

        # Restore geometry
        geom = settings.get("window_geometry")
        if geom:
            try:
                self.restoreGeometry(bytes.fromhex(geom))
            except Exception:
                pass

        self._worker: Optional[ScanWorker] = None
        self._scan_start_time: float = 0.0
        self._total_files_found: int = 0
        self._last_misplaced_count: int = 0

        self._build_ui()
        self._apply_saved_settings()

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Header
        root_layout.addWidget(self._make_header())

        # ── Horizontal splitter: left sidebar | right results ─────────────
        body_splitter = QSplitter(Qt.Orientation.Horizontal)
        body_splitter.setChildrenCollapsible(False)
        body_splitter.setContentsMargins(10, 10, 10, 10)

        # Left sidebar — scrollable so content never gets clipped
        left_inner = QWidget()
        left_inner.setMinimumWidth(240)
        left_inner.setMaximumWidth(500)
        left_layout = QVBoxLayout(left_inner)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(8)
        left_layout.addWidget(self._make_folder_picker())
        left_layout.addWidget(self._make_scan_options())
        left_layout.addWidget(self._make_folder_modes(), 1)   # stretch=1 → grows
        left_layout.addWidget(self._make_scan_controls())
        left_layout.addWidget(self._make_progress_panel())

        left_scroll = QScrollArea()
        left_scroll.setWidget(left_inner)
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setMinimumWidth(255)
        left_scroll.setMaximumWidth(500)
        body_splitter.addWidget(left_scroll)

        # Right panel — results/detail horizontal splitter + log stacked vertically
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Results + Detail horizontal split
        results_detail_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._results_panel = ResultsPanel()
        self._results_panel.ignore_requested.connect(self._on_ignore_requested)
        results_detail_splitter.addWidget(self._results_panel)

        self._detail_panel = DetailPanel()
        results_detail_splitter.addWidget(self._detail_panel)
        results_detail_splitter.setStretchFactor(0, 1)  # Results gets extra space
        results_detail_splitter.setStretchFactor(1, 0)  # Detail is fixed-preference
        results_detail_splitter.setSizes([700, 300])

        # Wire selection signal
        self._results_panel.result_selected.connect(self._detail_panel.show_result)
        self._detail_panel.swap_keeper_requested.connect(
            lambda res: self._results_panel.swap_keeper(res, self.hs2_root())
        )

        right_splitter.addWidget(results_detail_splitter)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(130)
        right_splitter.addWidget(self._log)
        right_splitter.setSizes([600, 130])
        body_splitter.addWidget(right_splitter)

        # Give the right panel all the stretch (left sidebar is fixed-preference)
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)
        body_splitter.setSizes([300, 800])

        root_layout.addWidget(body_splitter, 1)

        # Action bar (bottom)
        root_layout.addWidget(self._make_action_bar())
        # Post-scan banner (hidden by default)
        self._banner = self._make_post_scan_banner()
        self._banner.hide()
        root_layout.addWidget(self._banner)

    def _make_header(self) -> QWidget:
        w = QWidget()
        w.setObjectName("headerWidget")
        w.setFixedHeight(64)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(16, 8, 16, 8)
        title = QLabel("HS2 Studio Cleanup v0.01b1")
        title.setObjectName("appTitle")
        sub = QLabel("Deduplicator & Organiser")
        sub.setObjectName("appSubtitle")
        vl = QVBoxLayout()
        vl.setSpacing(0)
        vl.addWidget(title)
        vl.addWidget(sub)
        layout.addLayout(vl)
        layout.addStretch()
        return w

    def _make_folder_picker(self) -> QGroupBox:
        grp = QGroupBox("HS2 Root Folder")
        layout = QHBoxLayout(grp)
        layout.setContentsMargins(8, 16, 8, 8)
        self._path_edit = QLineEdit(settings.get("hs2_root", "C:\\HS2"))
        self._path_edit.setPlaceholderText("C:\\HS2")
        self._path_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Refresh folder tree when path changes (with a small delay to avoid
        # refreshing on every keystroke — we wait for the user to stop typing)
        self._path_edit.editingFinished.connect(self._refresh_folder_tree)
        layout.addWidget(self._path_edit, 1)
        btn = QPushButton("\u2026")
        btn.setFixedWidth(32)
        btn.clicked.connect(self._browse_folder)
        layout.addWidget(btn)
        return grp

    def _make_scan_options(self) -> QGroupBox:
        grp = QGroupBox("Scan Options")
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(4)
        opts = settings.get("scan_options", {})
        self._chk_zipmods = QCheckBox("Zipmod files (.zipmod)")
        self._chk_zipmods.setChecked(opts.get("zipmods", True))
        self._chk_png = QCheckBox("Character cards & scenes (.png)")
        self._chk_png.setChecked(opts.get("chara_cards", True))
        self._chk_other = QCheckBox("Other files")
        self._chk_other.setChecked(opts.get("other", True))
        self._chk_dry_run = QCheckBox("🔍 Dry Run (preview only — no files moved)")
        self._chk_dry_run.setChecked(settings.get("dry_run", False))
        for chk in (self._chk_zipmods, self._chk_png, self._chk_other, self._chk_dry_run):
            layout.addWidget(chk)
        return grp

    def _make_folder_modes(self) -> QGroupBox:
        grp = QGroupBox("Folder Modes")
        outer = QVBoxLayout(grp)
        outer.setContentsMargins(4, 14, 4, 4)
        outer.setSpacing(4)

        # Toolbar: Refresh + Expand populated
        toolbar = QHBoxLayout()
        lbl_hint = QLabel("Expand ▶ to set sub-folder modes. Children inherit parent unless overridden.")
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet("color: #666688; font-size: 10px;")
        outer.addWidget(lbl_hint)

        btn_refresh = QPushButton("\u27f3 Refresh Folders")
        btn_refresh.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn_refresh.clicked.connect(self._refresh_folder_tree)
        toolbar.addWidget(btn_refresh)

        btn_expand = QPushButton("\u25bc Show Saved")
        btn_expand.setToolTip("Expand folders that have an explicit mode set")
        btn_expand.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn_expand.clicked.connect(lambda: self._folder_tree.expand_populated())
        toolbar.addWidget(btn_expand)
        outer.addLayout(toolbar)

        # Tree — grows to fill available vertical space
        self._folder_tree = FolderTreeWidget()
        self._folder_tree.setMinimumHeight(160)
        self._folder_tree.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        outer.addWidget(self._folder_tree, 1)  # stretch=1

        # Add inbox folder button
        btn_add_inbox = QPushButton("\u2795 Add Inbox Folder\u2026")
        btn_add_inbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn_add_inbox.clicked.connect(self._add_inbox_folder)
        outer.addWidget(btn_add_inbox)

        # Make the whole group box expand vertically
        grp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return grp

    def _make_scan_controls(self) -> QWidget:
        w = QWidget()
        # Two-row layout: Start Scan on its own row, Pause+Stop below
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        self._btn_scan = QPushButton("▶  Start Scan")
        self._btn_scan.setObjectName("btnScan")
        self._btn_scan.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_scan.clicked.connect(self._start_scan)
        outer.addWidget(self._btn_scan)

        row2 = QHBoxLayout()
        row2.setSpacing(4)
        self._btn_pause = QPushButton("⏸  Pause")
        self._btn_pause.setEnabled(False)
        self._btn_pause.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_pause.clicked.connect(self._pause_scan)
        self._btn_stop = QPushButton("⏹  Stop")
        self._btn_stop.setEnabled(False)
        self._btn_stop.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_stop.clicked.connect(self._stop_scan)
        row2.addWidget(self._btn_pause)
        row2.addWidget(self._btn_stop)
        outer.addLayout(row2)
        return w

    def _make_progress_panel(self) -> QGroupBox:
        grp = QGroupBox("Progress")
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(8, 14, 8, 8)
        layout.setSpacing(4)
        self._lbl_phase = QLabel("Ready.")
        self._lbl_phase.setObjectName("statusLabel")
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._lbl_current = QLabel("")
        self._lbl_current.setObjectName("statusLabel")
        self._lbl_current.setWordWrap(True)
        self._lbl_eta = QLabel("")
        self._lbl_eta.setObjectName("statusLabel")
        for w in (self._lbl_phase, self._progress_bar, self._lbl_current, self._lbl_eta):
            layout.addWidget(w)
        return grp

    def _make_action_bar(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("QWidget { background-color: #0f0f1a; border-top: 1px solid #2a2a4a; }")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        self._btn_move = QPushButton("✓  Move Selected to Cleanup")
        self._btn_move.setObjectName("btnMove")
        self._btn_move.setEnabled(False)
        self._btn_move.clicked.connect(self._move_selected)
        self._btn_undo = QPushButton("↩  Undo Last")
        self._btn_undo.clicked.connect(self._undo_last)
        self._btn_export = QPushButton("📋  Export Report")
        self._btn_export.clicked.connect(self._export_report)
        layout.addWidget(self._btn_move)
        layout.addWidget(self._btn_undo)
        layout.addWidget(self._btn_export)
        layout.addStretch()
        self._lbl_status = QLabel("Ready.")
        self._lbl_status.setObjectName("statusLabel")
        layout.addWidget(self._lbl_status)
        return w

    def _make_post_scan_banner(self) -> QWidget:
        w = QWidget()
        w.setObjectName("bannerWidget")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(12, 8, 12, 8)
        self._lbl_banner = QLabel("")
        self._lbl_banner.setStyleSheet("color: #2ecc71; font-weight: 600;")
        layout.addWidget(self._lbl_banner)
        layout.addStretch()
        self._btn_sort_misplaced = QPushButton("📥  Sort Misplaced to Correct Folders")
        self._btn_sort_misplaced.setObjectName("btnSortMisplaced")
        self._btn_sort_misplaced.clicked.connect(self._sort_misplaced)
        layout.addWidget(self._btn_sort_misplaced)
        btn_dismiss = QPushButton("Dismiss")
        btn_dismiss.clicked.connect(w.hide)
        layout.addWidget(btn_dismiss)
        return w

    def hs2_root(self) -> Path:
        """Return the current HS2 root path from the UI field."""
        return Path(self._path_edit.text().strip())

    # ── Settings application ──────────────────────────────────────────────

    def _apply_saved_settings(self):
        # Populate the folder tree from whatever HS2 root is saved
        self._refresh_folder_tree()

    def _save_ui_settings(self):
        settings.set("hs2_root", self._path_edit.text().strip())
        settings.set("dry_run", self._chk_dry_run.isChecked())
        settings.set("scan_options", {
            "zipmods": self._chk_zipmods.isChecked(),
            "chara_cards": self._chk_png.isChecked(),
            "other": self._chk_other.isChecked(),
        })
        # Folder modes are already saved live via FolderTreeWidget combos
        settings.set("window_geometry", bytes(self.saveGeometry()).hex())
        settings.save()

    # ── Actions ───────────────────────────────────────────────────────────

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select HS2 Root Folder", self._path_edit.text()
        )
        if path:
            self._path_edit.setText(path)
            self._refresh_folder_tree()

    def _refresh_folder_tree(self) -> None:
        """Repopulate the folder tree from the current HS2 root path."""
        root = Path(self._path_edit.text().strip())
        self._folder_tree.populate(root)
        # Re-expand any nodes that already have explicit modes saved
        self._folder_tree.expand_populated()

    def _add_inbox_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Inbox Folder", self._path_edit.text()
        )
        if path:
            inboxes = settings.get("inbox_folders", [])
            if path not in inboxes:
                inboxes.append(path)
                settings.set("inbox_folders", inboxes)
                settings.save()
                self._log_msg(f"Added inbox folder: {path}")
                # Refresh so the folder shows up in the tree
                self._refresh_folder_tree()

    def _start_scan(self):
        hs2_root_str = self._path_edit.text().strip()
        hs2_root = Path(hs2_root_str)
        if not hs2_root.exists():
            QMessageBox.warning(self, "Invalid Path", f"Folder does not exist:\n{hs2_root_str}")
            return

        # First run warning
        if settings.get("first_run", True):
            dlg = FirstRunDialog(self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            settings.set("first_run", False)
            settings.save()

        self._save_ui_settings()
        self._results_panel.clear_all()
        self._banner.hide()
        self._log.clear()
        self._btn_scan.setEnabled(False)
        self._btn_pause.setEnabled(True)
        self._btn_stop.setEnabled(True)
        self._btn_move.setEnabled(False)
        self._total_files_found = 0
        self._scan_start_time = time.time()

        dry_run = self._chk_dry_run.isChecked()
        self._worker = ScanWorker(
            hs2_root=hs2_root,
            scan_zipmods=self._chk_zipmods.isChecked(),
            scan_png=self._chk_png.isChecked(),
            scan_other=self._chk_other.isChecked(),
            dry_run=dry_run,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.file_found.connect(self._on_file_found)
        self._worker.result_ready.connect(self._on_result)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _pause_scan(self):
        # Toggle pause via aborting (simple approach for v1)
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._btn_pause.setText("(paused — restart to resume)")
            self._btn_pause.setEnabled(False)

    def _stop_scan(self):
        if self._worker and self._worker.isRunning():
            self._worker.abort()
        self._btn_scan.setEnabled(True)
        self._btn_pause.setEnabled(False)
        self._btn_stop.setEnabled(False)
        self._lbl_status.setText("Scan stopped.")

    def _move_selected(self):
        results = self._results_panel.get_checked_results()
        if not results:
            QMessageBox.information(self, "Nothing selected", "No items are checked for cleanup.")
            return
        hs2_root = self.hs2_root()
        dry_run = self._chk_dry_run.isChecked()

        # Disable controls while moving
        self._btn_move.setEnabled(False)
        self._btn_scan.setEnabled(False)
        self._lbl_status.setText(f"Moving {len(results)} files…")

        self._move_worker = MoveWorker(results, hs2_root, dry_run)
        self._move_worker.progress.connect(self._on_progress)
        self._move_worker.log.connect(self._log_msg)
        self._move_worker.file_processed.connect(self._results_panel.mark_processed)
        self._move_worker.finished.connect(self._on_move_finished)
        self._move_worker.error.connect(lambda msg: (
            self._log_msg(f"[ERROR] Move failed: {msg}"),
            self._on_move_done()
        ))
        self._move_worker.start()

    def _on_move_finished(self, moved: int, reported: int):
        dry_run = self._chk_dry_run.isChecked()
        tag = " (DRY RUN)" if dry_run else ""
        self._lbl_status.setText(f"{moved} files moved, {reported} reported{tag}.")
        self._on_move_done()

        mp_count = self._results_panel.misplaced_count()
        self._last_misplaced_count = mp_count
        if mp_count > 0:
            self._lbl_banner.setText(
                f"📥  {mp_count} misplaced files were moved to _Cleanup/Misplaced/. "
                "Sort them to their correct HS2 locations?"
            )
            self._banner.show()

    def _on_move_done(self):
        self._btn_move.setEnabled(True)
        self._btn_scan.setEnabled(True)
        self._progress_bar.setValue(0)

    def _undo_last(self):
        hs2_root = self.hs2_root()
        msgs = movement_engine.undo_last(hs2_root)
        for m in msgs:
            self._log_msg(m)
        self._lbl_status.setText(f"Undo complete. {len(msgs)} operations.")

    def _export_report(self):
        last_dir = settings.get("last_export_dir", "")
        if not last_dir or not Path(last_dir).exists():
            last_dir = str(Path.home())
            
        default_path = str(Path(last_dir) / "hs2_cleanup_report.json")

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Report", default_path,
            "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        results = [
            {
                "file": str(r.filepath),
                "category": r.category,
                "reason": r.reason,
                "mode": r.mode,
                "keeper": str(r.keeper) if r.keeper else None,
                "scene_warning_count": r.scene_warning_count,
            }
            for r in self._results_panel.get_all_results()
        ]
        report = {
            "app": "HS2 Studio Cleanup",
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "hs2_root": self._path_edit.text(),
            "total_findings": len(results),
            "results": results,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        settings.set("last_export_dir", str(Path(path).parent))
        settings.save()

        self._log_msg(f"Report exported: {path}")
        QMessageBox.information(self, "Exported", f"Report saved to:\n{path}")

    def _sort_misplaced(self):
        """Run _Cleanup/Misplaced/ through Inbox Mode — non-blocking."""
        hs2_root = self.hs2_root()
        misplaced_dir = hs2_root / "_Cleanup" / "Misplaced"
        if not misplaced_dir.exists():
            QMessageBox.information(self, "Nothing to sort", "No _Cleanup/Misplaced/ folder found.")
            return
        dry_run = self._chk_dry_run.isChecked()

        self._banner.hide()
        self._btn_scan.setEnabled(False)
        self._btn_move.setEnabled(False)
        self._lbl_status.setText("Sorting misplaced files…")

        self._sort_worker = SortMisplacedWorker(hs2_root, dry_run)
        self._sort_worker.progress.connect(self._on_progress)
        self._sort_worker.log.connect(self._log_msg)
        self._sort_worker.finished.connect(self._on_sort_finished)
        self._sort_worker.error.connect(lambda msg: (
            self._log_msg(f"[ERROR] Sort failed: {msg}"),
            self._on_move_done()
        ))
        self._sort_worker.start()

    def _on_sort_finished(self, sorted_count: int):
        dry_run = self._chk_dry_run.isChecked()
        tag = " (DRY RUN)" if dry_run else ""
        self._lbl_status.setText(f"Sorted {sorted_count} misplaced files{tag}.")
        self._log_msg(f"[SORT] Complete — {sorted_count} files sorted.")
        self._on_move_done()

    def _on_ignore_requested(self, abs_path: str):
        settings.add_ignored(abs_path)
        self._log_msg(f"[IGNORE] {Path(abs_path).name} added to ignore list.")

    # ── Worker callbacks ──────────────────────────────────────────────────

    def _on_progress(self, phase: str, pct: int, current: str):
        self._lbl_phase.setText(phase)
        self._progress_bar.setValue(pct)
        if current:
            self._lbl_current.setText(current)
        elapsed = time.time() - self._scan_start_time
        if pct > 5:
            eta_sec = elapsed * (100 - pct) / max(pct, 1)
            self._lbl_eta.setText(
                f"Elapsed: {self._fmt_time(elapsed)}  |  ETA: ~{self._fmt_time(eta_sec)}"
            )

    def _on_file_found(self, count: int):
        self._total_files_found = count
        self._lbl_current.setText(f"Discovered {count:,} files…")

    def _on_result(self, result):
        self._results_panel.add_result(result)
        self._btn_move.setEnabled(True)

    def _on_finished(self, total: int, result_count: int, misplaced: int):
        self._btn_scan.setEnabled(True)
        self._btn_pause.setEnabled(False)
        self._btn_stop.setEnabled(False)
        self._progress_bar.setValue(100)
        elapsed = time.time() - self._scan_start_time
        dry_tag = " [DRY RUN]" if self._chk_dry_run.isChecked() else ""
        msg = (f"Scan complete{dry_tag}. {total:,} files scanned, "
               f"{result_count:,} findings. Time: {self._fmt_time(elapsed)}")
        self._lbl_status.setText(msg)
        self._lbl_phase.setText("Scan complete.")
        self._log_msg(msg)

        # Modpack update reminder
        self._maybe_show_modpack_reminder()

    def _on_error(self, msg: str):
        self._log_msg(f"[ERROR] {msg}")
        self._btn_scan.setEnabled(True)
        self._btn_pause.setEnabled(False)
        self._btn_stop.setEnabled(False)
        self._lbl_status.setText("Scan failed — see log.")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _log_msg(self, text: str):
        self._log.append(text)

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        s = int(seconds)
        if s < 60:
            return f"{s}s"
        return f"{s // 60}m {s % 60}s"

    def _has_modpack_results(self) -> bool:
        """Return True if any scanned result involves the Sideloader Modpack path."""
        return any(
            "sideloader modpack" in str(r.filepath).lower()
            for r in self._results_panel.get_all_results()
        )

    def _maybe_show_modpack_reminder(self):
        """Log a tip at scan-end if modpack duplicates were found."""
        if self._has_modpack_results():
            self._log_msg(
                "💡 Tip: Duplicates found involving the Sideloader Modpack. "
                "Re-scan after modpack updates to catch new overlaps."
            )

    # ── Window close ─────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._save_ui_settings()
        # Modpack reminder popup
        self._on_close_reminder()
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait(2000)
        super().closeEvent(event)

    def _on_close_reminder(self):
        """Show a popup reminder about modpack updates when closing if relevant."""
        if self._has_modpack_results():
            QMessageBox.information(
                self, "💡 Tip — Modpack Update Reminder",
                "Your scan found duplicates between MyMods and the Sideloader Modpack.\n\n"
                "Consider re-scanning after future modpack updates to catch new overlaps."
            )
