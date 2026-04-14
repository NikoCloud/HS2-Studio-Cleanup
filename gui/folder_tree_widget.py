"""
gui/folder_tree_widget.py — Dynamic, lazy-loading folder mode tree.

Scans the HS2 root directory on demand and presents each subfolder
as a tree node with a per-folder mode dropdown. Supports up to 6
levels of depth (loaded lazily when the user expands a node).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QComboBox, QHeaderView,
    QWidget, QHBoxLayout, QLabel, QSizePolicy,
)

from core import settings

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_LAZY_DEPTH = 6          # Maximum folder depth we'll ever load
INITIAL_EXPAND_DEPTH = 0    # Depth visible on first load (top-level only)

# Folders that even at top level must never be Inbox
_NEVER_INBOX = {
    "abdata", "bepinex", "userdata", "mods",
    "sideloader modpack", "sideloader modpack - studio",
    "sideloader modpack - maps",
}

# Folders to skip entirely (our own output + OS junk)
_SKIP_DIRS = {"_cleanup", "$recycle.bin", "system volume information", ".git"}

_MODE_OPTIONS = ["inherit", "move", "report", "inbox", "ignore"]
_MODE_DISPLAY = {
    "inherit": "⬆ Inherit",
    "move":    "✅ Move",
    "report":  "🔒 Report",
    "inbox":   "📥 Inbox",
    "ignore":  "⛔ Ignore",
}
_MODE_COLOURS = {
    "inherit": QColor("#666688"),
    "move":    QColor("#2ecc71"),
    "report":  QColor("#e74c3c"),
    "inbox":   QColor("#4a90d9"),
    "ignore":  QColor("#444455"),
}

# Sentinel child used to mark nodes as "not yet loaded"
_PLACEHOLDER_TEXT = "__placeholder__"


# ── Tree item helper ──────────────────────────────────────────────────────────

class FolderItem(QTreeWidgetItem):
    """A tree item representing a single folder in the HS2 tree."""

    def __init__(
        self,
        abs_path: Path,
        hs2_root: Path,
        depth: int,
        parent_item=None,
    ):
        super().__init__()
        self.abs_path = abs_path
        self.hs2_root = hs2_root
        self.depth = depth
        self._children_loaded = False

        # Display text: folder name only
        self.setText(0, abs_path.name + "/")

        # Relative path for settings key
        try:
            self._rel = str(abs_path.relative_to(hs2_root))
        except ValueError:
            self._rel = abs_path.name

        # Resolved mode (may be 'inherit' if not explicitly set)
        stored = settings.get("folder_modes", {}).get(
            self._rel.replace("\\", "/").lower(), None
        )
        self._mode = stored if stored else "inherit"

        # Add placeholder child so Qt shows the expand arrow (if depth allows)
        if depth < MAX_LAZY_DEPTH and self._has_subdirs():
            placeholder = QTreeWidgetItem(self)
            placeholder.setText(0, _PLACEHOLDER_TEXT)

    def _has_subdirs(self) -> bool:
        try:
            for entry in os.scandir(self.abs_path):
                if entry.is_dir() and entry.name.lower() not in _SKIP_DIRS:
                    return True
        except PermissionError:
            pass
        return False

    def rel_key(self) -> str:
        """Relative path key normalised for settings lookup."""
        return self._rel.replace("\\", "/").lower()

    def effective_mode(self) -> str:
        """The mode that actually applies (resolving inheritance)."""
        return settings.get_folder_mode(self._rel)

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        settings.set_folder_mode(self._rel, mode)
        settings.save()  # Persist changes to config.json immediately
        self._update_colour()

    def _update_colour(self) -> None:
        effective = self.effective_mode()
        colour = _MODE_COLOURS.get(effective, _MODE_COLOURS["move"])
        self.setForeground(0, QBrush(colour))


# ── Background dir scanner ────────────────────────────────────────────────────

class DirScanner(QThread):
    """Scan a single directory for immediate children in background thread."""
    done = pyqtSignal(object, list)  # (parent_item, [Path, ...])

    def __init__(self, item: FolderItem, parent=None):
        super().__init__(parent)
        self._item = item

    def run(self):
        children: list[Path] = []
        try:
            entries = sorted(
                (e for e in os.scandir(self._item.abs_path)
                 if e.is_dir() and e.name.lower() not in _SKIP_DIRS),
                key=lambda e: e.name.lower(),
            )
            children = [Path(e.path) for e in entries]
        except PermissionError:
            pass
        self.done.emit(self._item, children)


# ── Main widget ───────────────────────────────────────────────────────────────

class FolderTreeWidget(QTreeWidget):
    """
    Folder mode tree for the HS2 root.

    - Top-level folders appear immediately after populate().
    - Children load lazily on expand (background thread).
    - Each node has a mode combo (Inherit / Move / Report / Inbox).
    - Combo changes persist to settings immediately.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hs2_root: Optional[Path] = None
        self._scanners: list[DirScanner] = []

        self.setColumnCount(2)
        self.setHeaderLabels(["Folder", "Mode"])
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.header().setDefaultSectionSize(145)
        self.setColumnWidth(1, 145)
        self.setIndentation(16)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setUniformRowHeights(True)
        self.setAnimated(True)

        # Readable row height and font
        self.setStyleSheet("""
            QTreeWidget {
                font-size: 12px;
            }
            QTreeWidget::item {
                padding-top: 6px;
                padding-bottom: 6px;
                min-height: 26px;
            }
            QTreeWidget QHeaderView::section {
                padding: 6px 6px;
                font-size: 11px;
            }
        """)

        self.itemExpanded.connect(self._on_expand)

    # ── Public API ────────────────────────────────────────────────────────

    def populate(self, hs2_root: Path) -> None:
        """Clear and re-scan top-level folders from hs2_root."""
        self._hs2_root = hs2_root
        self.clear()

        if not hs2_root.exists():
            return

        try:
            top_dirs = sorted(
                (e for e in os.scandir(hs2_root)
                 if e.is_dir() and e.name.lower() not in _SKIP_DIRS),
                key=lambda e: e.name.lower(),
            )
        except PermissionError:
            return

        for entry in top_dirs:
            item = FolderItem(Path(entry.path), hs2_root, depth=1)
            item._update_colour()
            self.addTopLevelItem(item)
            self._attach_combo(item)

    def expand_populated(self) -> None:
        """Expand all nodes that have an explicit (non-inherit) mode set."""
        modes = settings.get("folder_modes", {})

        def expand_item(item: FolderItem):
            if item.rel_key() in modes:
                parent = item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
            for i in range(item.childCount()):
                child = item.child(i)
                if isinstance(child, FolderItem):
                    expand_item(child)

        for i in range(self.topLevelItemCount()):
            top = self.topLevelItem(i)
            if isinstance(top, FolderItem):
                expand_item(top)

    # ── Lazy loading ──────────────────────────────────────────────────────

    def _on_expand(self, item: QTreeWidgetItem) -> None:
        if not isinstance(item, FolderItem):
            return
        if item._children_loaded:
            return
        item._children_loaded = True

        # Remove placeholder
        for i in range(item.childCount() - 1, -1, -1):
            child = item.child(i)
            if child and child.text(0) == _PLACEHOLDER_TEXT:
                item.removeChild(child)

        # Kick off background scan
        scanner = DirScanner(item, self)
        scanner.done.connect(self._on_scan_done)
        self._scanners.append(scanner)
        scanner.start()

    def _on_scan_done(self, parent_item: FolderItem, children: list[Path]) -> None:
        for child_path in children:
            child = FolderItem(
                child_path, self._hs2_root, parent_item.depth + 1
            )
            child._update_colour()
            parent_item.addChild(child)
            self._attach_combo(child)

    # ── Combo attachment ──────────────────────────────────────────────────

    def _attach_combo(self, item: FolderItem) -> None:
        combo = QComboBox()
        combo.setFrame(False)
        combo.setMinimumHeight(28)

        # Restrict Inbox option for system folders
        options = list(_MODE_OPTIONS)
        if item.abs_path.name.lower() in _NEVER_INBOX:
            options = [o for o in options if o != "inbox"]

        for opt in options:
            combo.addItem(_MODE_DISPLAY[opt], opt)

        # Select saved value
        stored_idx = combo.findData(item._mode)
        combo.setCurrentIndex(stored_idx if stored_idx >= 0 else 0)

        # Show effective mode colour immediately
        self._update_combo_colour(combo, item.effective_mode())

        combo.currentIndexChanged.connect(
            lambda _, c=combo, it=item: self._on_combo_changed(c, it)
        )
        self.setItemWidget(item, 1, combo)

    def _on_combo_changed(self, combo: QComboBox, item: FolderItem) -> None:
        mode = combo.currentData()
        item.set_mode(mode)
        self._update_combo_colour(combo, item.effective_mode())
        # Propagate colour update to visible children
        self._refresh_child_colours(item)

    def _refresh_child_colours(self, item: FolderItem) -> None:
        for i in range(item.childCount()):
            child = item.child(i)
            if isinstance(child, FolderItem):
                child._update_colour()
                w = self.itemWidget(child, 1)
                if isinstance(w, QComboBox):
                    self._update_combo_colour(w, child.effective_mode())
                self._refresh_child_colours(child)

    @staticmethod
    def _update_combo_colour(combo: QComboBox, effective_mode: str) -> None:
        colour = _MODE_COLOURS.get(effective_mode, _MODE_COLOURS["move"])
        combo.setStyleSheet(
            f"QComboBox {{ color: {colour.name()}; font-weight: 600; font-size: 12px; }}"
        )
