"""
gui/results_panel.py — Tabbed results view with checkboxes, badges, details.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QHBoxLayout, QPushButton, QLabel, QMenu, QSizePolicy
)

from core.dedup_engine import DedupResult


_CATEGORY_LABELS = {
    "duplicate":          ("🔴", "Duplicates"),
    "older_version":      ("🟡", "Older Versions"),
    "possible_duplicate": ("🟠", "Possible Dups"),
    "misplaced":          ("🔵", "Misplaced"),
    "unknown_metadata":   ("⚪", "Unknown"),
    "orphaned":           ("⚫", "Orphaned"),
}

_MODE_COLOUR = {
    "move":   QColor("#2ecc71"),
    "report": QColor("#e74c3c"),
    "inbox":  QColor("#4a90d9"),
}


def _short(path: Optional[Path], max_len: int = 70) -> str:
    if path is None:
        return ""
    s = str(path)
    return ("…" + s[-(max_len-1):]) if len(s) > max_len else s


class ResultsPanel(QWidget):
    ignore_requested = pyqtSignal(str)   # abs path
    result_selected  = pyqtSignal(object)  # DedupResult or None
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: list[DedupResult] = []
        self._item_by_path: dict[str, QTreeWidgetItem] = {}   # O(1) lookup for mark_processed
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Top toolbar
        toolbar = QHBoxLayout()
        self._lbl_total = QLabel("No results yet.")
        self._lbl_total.setObjectName("statsLabel")
        toolbar.addWidget(self._lbl_total)
        toolbar.addStretch()

        self._btn_select_all = QPushButton("Select All")
        self._btn_select_all.setFixedWidth(90)
        self._btn_select_all.clicked.connect(self._select_all)
        toolbar.addWidget(self._btn_select_all)

        self._btn_deselect = QPushButton("Deselect All")
        self._btn_deselect.setFixedWidth(95)
        self._btn_deselect.clicked.connect(self._deselect_all)
        toolbar.addWidget(self._btn_deselect)

        layout.addLayout(toolbar)

        # Tab widget
        self._tabs = QTabWidget()
        self._trees: dict[str, QTreeWidget] = {}

        for cat, (icon, label) in _CATEGORY_LABELS.items():
            tree = self._make_tree()
            self._trees[cat] = tree
            self._tabs.addTab(tree, f"{icon} {label} (0)")

        layout.addWidget(self._tabs)

    def _make_tree(self) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setColumnCount(5)
        tree.setHeaderLabels(["✓", "File", "Reason", "Mode", "Size"])
        tree.setIndentation(0)
        tree.setColumnWidth(0, 40)
        tree.setColumnWidth(1, 340)
        tree.setColumnWidth(2, 330)
        tree.setColumnWidth(3, 70)
        tree.setColumnWidth(4, 70)
        tree.setAlternatingRowColors(True)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(
            lambda pos, t=tree: self._context_menu(t, pos)
        )
        tree.currentItemChanged.connect(
            lambda cur, _prev: self._on_selection_changed(cur)
        )
        return tree

    def _on_selection_changed(self, item):
        if item is None:
            self.result_selected.emit(None)
            return
        result = item.data(0, Qt.ItemDataRole.UserRole)
        self.result_selected.emit(result)

    def add_result(self, result: DedupResult):
        self._results.append(result)
        cat = result.category
        tree = self._trees.get(cat)
        if tree is None:
            return

        warn = f" ⚠️ {result.scene_warning_count} scenes" if result.scene_warning_count else ""
        size_str = self._fmt_size(result.filepath.stat().st_size if result.filepath.exists() else 0)

        item = QTreeWidgetItem(tree)
        item.setCheckState(0, Qt.CheckState.Checked if cat not in ("possible_duplicate",) else Qt.CheckState.Unchecked)
        item.setText(1, result.filepath.name + warn)
        item.setToolTip(1, str(result.filepath))
        item.setText(2, result.reason)
        item.setToolTip(2, result.reason + (
            f"\n\nKeeper: {result.keeper}" if result.keeper else ""
        ))
        item.setText(3, result.mode.upper())
        item.setText(4, size_str)
        item.setForeground(3, QBrush(_MODE_COLOUR.get(result.mode, QColor("#ffffff"))))
        item.setData(0, Qt.ItemDataRole.UserRole, result)
        self._item_by_path[str(result.filepath)] = item

        if cat == "possible_duplicate":
            item.setForeground(1, QBrush(QColor("#e67e22")))
        elif cat == "older_version":
            item.setForeground(1, QBrush(QColor("#f1c40f")))
        elif cat == "duplicate":
            item.setForeground(1, QBrush(QColor("#e74c3c")))
        elif cat == "misplaced":
            item.setForeground(1, QBrush(QColor("#3498db")))

        self._update_tab_title(cat, tree)

    def _update_tab_title(self, cat: str, tree: QTreeWidget):
        idx = list(self._trees.keys()).index(cat)
        icon, label = _CATEGORY_LABELS[cat]
        self._tabs.setTabText(idx, f"{icon} {label} ({tree.topLevelItemCount()})")
        total = sum(t.topLevelItemCount() for t in self._trees.values())
        self._lbl_total.setText(f"{total:,} findings")

    def get_checked_results(self) -> list[DedupResult]:
        results = []
        for tree in self._trees.values():
            for i in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(i)
                if item and item.checkState(0) == Qt.CheckState.Checked:
                    r = item.data(0, Qt.ItemDataRole.UserRole)
                    if r:
                        results.append(r)
        return results

    def clear_all(self):
        self._results.clear()
        self._item_by_path.clear()
        for cat, tree in self._trees.items():
            tree.clear()
            idx = list(self._trees.keys()).index(cat)
            icon, label = _CATEGORY_LABELS[cat]
            self._tabs.setTabText(idx, f"{icon} {label} (0)")
        self._lbl_total.setText("No results yet.")

    def mark_processed(self, filepath: str, status: str):
        """Dim and uncheck a row after it has been moved or reported."""
        item = self._item_by_path.get(filepath)
        if not item:
            return
        colour = QColor("#4a5a4a") if status == "moved" else QColor("#5a4a2a")
        brush = QBrush(colour)
        for col in range(item.columnCount()):
            item.setForeground(col, brush)
        item.setCheckState(0, Qt.CheckState.Unchecked)

    def _select_all(self):
        current_tree = self._tabs.currentWidget()
        if isinstance(current_tree, QTreeWidget):
            for i in range(current_tree.topLevelItemCount()):
                item = current_tree.topLevelItem(i)
                if item:
                    item.setCheckState(0, Qt.CheckState.Checked)

    def _deselect_all(self):
        current_tree = self._tabs.currentWidget()
        if isinstance(current_tree, QTreeWidget):
            for i in range(current_tree.topLevelItemCount()):
                item = current_tree.topLevelItem(i)
                if item:
                    item.setCheckState(0, Qt.CheckState.Unchecked)

    def _context_menu(self, tree: QTreeWidget, pos):
        item = tree.itemAt(pos)
        if not item:
            return
        result: DedupResult = item.data(0, Qt.ItemDataRole.UserRole)
        if not result:
            return
        menu = QMenu(self)
        open_act = menu.addAction("📂 Open containing folder")
        ignore_act = menu.addAction("🚫 Ignore in future scans")
        action = menu.exec(tree.viewport().mapToGlobal(pos))
        if action == open_act:
            import subprocess
            subprocess.Popen(f'explorer /select,"{result.filepath}"')
        elif action == ignore_act:
            self.ignore_requested.emit(str(result.filepath))
            idx = tree.indexOfTopLevelItem(item)
            tree.takeTopLevelItem(idx)

    @staticmethod
    def _fmt_size(b: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} TB"

    def get_all_results(self) -> list[DedupResult]:
        """Return every result across all tabs (for export)."""
        results = []
        for tree in self._trees.values():
            for i in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(i)
                if item:
                    r = item.data(0, Qt.ItemDataRole.UserRole)
                    if r:
                        results.append(r)
        return results

    def misplaced_count(self) -> int:
        return self._trees["misplaced"].topLevelItemCount()

    def swap_keeper(self, active_result: DedupResult, hs2_root: Path):
        """
        Swaps the keeper and filepath of active_result in-memory, updates mode,
        and repoints any other dupes sharing the old_keeper to the new_keeper.
        Updates the UI to reflect changes instantly.
        """
        if not active_result.keeper:
            return

        from core.settings import get_folder_mode

        old_keeper = active_result.keeper
        new_keeper = active_result.filepath

        # 1. Update the active result's internal state
        active_result.filepath = old_keeper
        active_result.keeper = new_keeper
        
        try:
            rel = active_result.filepath.relative_to(hs2_root)
        except ValueError:
            rel = active_result.filepath
        active_result.mode = get_folder_mode(str(rel))

        # 2. Iterate over the tree to update UI and other items in the dupe group
        tree = self._trees.get(active_result.category)
        if not tree:
            return

        active_item = None
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            res: DedupResult = item.data(0, Qt.ItemDataRole.UserRole)
            if not res:
                continue

            # If it's another duplicate pointing to the old keeper, repoint it
            if res is not active_result and res.keeper == old_keeper:
                res.keeper = new_keeper
                item.setToolTip(2, res.reason + f"\n\nKeeper: {res.keeper}")

            # Find the tree item for the active result itself to redraw
            if res is active_result:
                active_item = item

        # 3. Redraw the active item's UI row
        if active_item:
            warn = f" ⚠️ {active_result.scene_warning_count} scenes" if active_result.scene_warning_count else ""
            active_item.setText(1, active_result.filepath.name + warn)
            active_item.setToolTip(1, str(active_result.filepath))
            active_item.setText(3, active_result.mode.upper())
            active_item.setToolTip(2, active_result.reason + f"\n\nKeeper: {active_result.keeper}")
            active_item.setForeground(3, QBrush(_MODE_COLOUR.get(active_result.mode, QColor("#ffffff"))))
            
            # Re-trigger selection to refresh the DetailPanel with the new values
            self._on_selection_changed(active_item)
