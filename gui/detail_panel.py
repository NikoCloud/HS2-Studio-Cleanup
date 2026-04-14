"""
gui/detail_panel.py — Right-side detail panel for the Results view.

Shows full paths, file metadata, and type-specific info for the
selected result row. Embedded PNG preview for character cards and scenes.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
    QSizePolicy, QHBoxLayout, QPushButton
)

from core.dedup_engine import DedupResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_size(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def _fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d  %H:%M")


def _stat(path: Path):
    try:
        return path.stat()
    except OSError:
        return None


# ── Section / Row helpers ─────────────────────────────────────────────────────

def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "color: #888899; font-size: 10px; font-weight: 700; "
        "letter-spacing: 1px; margin-top: 10px; margin-bottom: 2px;"
    )
    return lbl


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #333344;")
    return line


def _row_widget(label: str, value: str, selectable: bool = False,
                tooltip: str = "") -> QWidget:
    """A two-line label / value row."""
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 2)
    layout.setSpacing(0)

    lbl = QLabel(label)
    lbl.setStyleSheet("color: #888899; font-size: 10px;")

    val = QLabel(value)
    val.setWordWrap(True)
    val.setStyleSheet("color: #e0e0f0; font-size: 11px;")
    if selectable:
        val.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
    if tooltip:
        val.setToolTip(tooltip)

    layout.addWidget(lbl)
    layout.addWidget(val)
    return w


# ── Main widget ───────────────────────────────────────────────────────────────

class DetailPanel(QWidget):
    """
    Right-side panel populated when the user clicks a result row.
    Contains:
      · PNG thumbnail (character cards / scenes)
      · Full Found At + Keeper paths
      · Filesystem metadata
      · Type-specific sections (zipmod / chara / scene)
    """
    swap_keeper_requested = pyqtSignal(DedupResult)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(260)
        self.setMaximumWidth(420)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._build_ui()
        self._show_placeholder()

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        self._content = QWidget()
        self._content.setStyleSheet("background: #1a1a2e;")
        scroll.setWidget(self._content)

        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(12, 10, 12, 16)
        self._layout.setSpacing(2)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    def _clear(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_placeholder(self):
        self._clear()
        ph = QLabel("Select a result row\nto see details.")
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph.setStyleSheet("color: #555566; font-size: 12px; padding: 40px 0;")
        self._layout.addWidget(ph)

    # ── Public API ────────────────────────────────────────────────────────

    def show_result(self, result: Optional[DedupResult]):
        if result is None:
            self._show_placeholder()
            return

        self._clear()
        path = result.filepath

        # ── Image preview (PNG only) ──────────────────────────────────────
        if path.suffix.lower() == ".png" and path.exists():
            pm = QPixmap(str(path))
            if not pm.isNull():
                img_lbl = QLabel()
                img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                scaled = pm.scaled(
                    220, 220,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                img_lbl.setPixmap(scaled)
                img_lbl.setStyleSheet("margin-bottom: 6px;")
                self._layout.addWidget(img_lbl)

        # ── Header ───────────────────────────────────────────────────────
        name_lbl = QLabel(path.name)
        name_lbl.setWordWrap(True)
        f = QFont()
        f.setBold(True)
        f.setPointSize(11)
        name_lbl.setFont(f)
        name_lbl.setStyleSheet("color: #e0e0f0; margin-bottom: 2px;")
        self._layout.addWidget(name_lbl)

        # Category + Mode badges
        cat_map = {
            "duplicate": ("🔴", "#e74c3c"),
            "older_version": ("🟡", "#f1c40f"),
            "possible_duplicate": ("🟠", "#e67e22"),
            "misplaced": ("🔵", "#3498db"),
            "unknown_metadata": ("⚪", "#888899"),
            "orphaned": ("⚫", "#555566"),
        }
        icon, colour = cat_map.get(result.category, ("⚪", "#888899"))
        cat_label = result.category.replace("_", " ").title()
        badge = QLabel(f"{icon} {cat_label}  ·  {result.mode.upper()}")
        badge.setStyleSheet(f"color: {colour}; font-size: 10px; font-weight: 600;")
        self._layout.addWidget(badge)

        self._layout.addWidget(_separator())

        # ── Paths ─────────────────────────────────────────────────────────
        self._layout.addWidget(_section_label("Paths"))
        self._layout.addWidget(_row_widget(
            "Found At", str(path.parent), selectable=True
        ))

        if result.category in ("duplicate", "possible_duplicate", "older_version") and result.keeper:
            btn_swap = QPushButton("⭐ Keep this file instead")
            btn_swap.setToolTip(
                f"Promote this file to Keeper.\n"
                f"The current Keeper will be flagged as the duplicate instead."
            )
            btn_swap.setFixedWidth(180)
            btn_swap.setStyleSheet("""
                QPushButton { padding: 4px 8px; margin-top: 4px; background: #2a2a3e; border: 1px solid #444455; color: #ccddff; }
                QPushButton:hover { background: #33334d; border-color: #555566; color: #ffffff; }
            """)
            btn_swap.clicked.connect(lambda _, r=result: self.swap_keeper_requested.emit(r))
            self._layout.addWidget(btn_swap)

        if result.keeper:
            keeper_label = "Destination" if result.category == "misplaced" else "Keeper Path"
            self._layout.addWidget(_row_widget(
                keeper_label, str(result.keeper), selectable=True
            ))

        self._layout.addWidget(_separator())

        # ── File Info ─────────────────────────────────────────────────────
        self._layout.addWidget(_section_label("File Info"))
        st = _stat(path)
        if st:
            self._layout.addWidget(_row_widget("Size", _fmt_size(st.st_size)))
            self._layout.addWidget(_row_widget("Modified", _fmt_ts(st.st_mtime)))
            self._layout.addWidget(_row_widget("Created", _fmt_ts(st.st_ctime)))

        if result.full_hash:
            short_hash = result.full_hash[:16] + "…"
            self._layout.addWidget(_row_widget(
                "SHA-256", short_hash,
                selectable=True,
                tooltip=result.full_hash
            ))

        # ── Zipmod Info ───────────────────────────────────────────────────
        zi = result.zipmod_info
        if zi:
            self._layout.addWidget(_separator())
            self._layout.addWidget(_section_label("Zipmod Info"))
            if zi.name:
                self._layout.addWidget(_row_widget("Name", zi.name))
            if zi.guid:
                self._layout.addWidget(_row_widget("GUID", zi.guid, selectable=True))
            if zi.version:
                self._layout.addWidget(_row_widget("Version", zi.version))
            if zi.author:
                self._layout.addWidget(_row_widget("Author", zi.author))
            if zi.game:
                self._layout.addWidget(_row_widget("Game", zi.game))

            manifest_status = "✅ Valid" if zi.has_manifest else "❌ Missing"
            corrupt_status = "⚠️ Corrupt" if zi.is_corrupt else ""
            status_str = manifest_status + (f"  {corrupt_status}" if corrupt_status else "")
            self._layout.addWidget(_row_widget("Manifest", status_str))

            if result.scene_warning_count:
                self._layout.addWidget(_row_widget(
                    "Scene Dependencies",
                    f"⚠️ {result.scene_warning_count} scene(s) reference this mod"
                ))

        # ── Character Card Info ───────────────────────────────────────────
        ci = result.chara_info
        if ci and ci.is_chara_card:
            self._layout.addWidget(_separator())
            self._layout.addWidget(_section_label("Character Card"))
            gender_icon = {"female": "♀", "male": "♂"}.get(ci.gender, "?")
            self._layout.addWidget(_row_widget(
                "Gender", f"{gender_icon} {ci.gender.title()}"
            ))
            if ci.game and ci.game != "unknown":
                self._layout.addWidget(_row_widget("Game", ci.game))

        # ── Coordinate Card Info ──────────────────────────────────────────
        coi = result.coord_info
        if coi and coi.is_coord:
            self._layout.addWidget(_separator())
            self._layout.addWidget(_section_label("Coordinate Card"))
            gender_icon = {"female": "♀", "male": "♂"}.get(coi.gender, "?")
            self._layout.addWidget(_row_widget(
                "Gender", f"{gender_icon} {coi.gender.title()}"
            ))

        # ── Scene Info ────────────────────────────────────────────────────
        si = result.scene_info
        if si and si.is_scene:
            self._layout.addWidget(_separator())
            self._layout.addWidget(_section_label("Studio Scene"))
            count = len(si.mod_guids)
            self._layout.addWidget(_row_widget(
                "Mod Dependencies", f"{count} GUID(s)"
            ))
            if result.scene_warning_count:
                self._layout.addWidget(_row_widget(
                    "Conflicts",
                    f"⚠️ {result.scene_warning_count} conflicting mod(s)"
                ))
            if si.mod_guids:
                self._layout.addWidget(_section_label("GUID List"))
                for guid in si.mod_guids:
                    g = QLabel(guid)
                    g.setStyleSheet(
                        "color: #aaaacc; font-size: 10px; font-family: monospace;"
                        "padding: 1px 0;"
                    )
                    g.setTextInteractionFlags(
                        Qt.TextInteractionFlag.TextSelectableByMouse
                    )
                    self._layout.addWidget(g)

        self._layout.addStretch()
