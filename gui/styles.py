"""
gui/styles.py — Dark theme QSS stylesheet for HS2 Studio Cleanup.
"""

STYLESHEET = """
QWidget {
    background-color: #1a1a2e;
    color: #e0e0f0;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0f0f1a;
}

/* Header bar */
#headerWidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #16213e, stop:1 #0f3460);
    border-bottom: 2px solid #e94560;
}

#appTitle {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 1px;
}

#appSubtitle {
    font-size: 11px;
    color: #a0a8c0;
}

/* Group boxes */
QGroupBox {
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    color: #8888bb;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background-color: #1a1a2e;
}

/* Buttons */
QPushButton {
    background-color: #16213e;
    color: #c0c8e0;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 7px 16px;
    min-width: 90px;
}

QPushButton:hover {
    background-color: #1e2d5a;
    border-color: #e94560;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #e94560;
    color: #ffffff;
}

QPushButton:disabled {
    background-color: #12121f;
    color: #444466;
    border-color: #1e1e33;
}

QPushButton#btnScan {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #e94560, stop:1 #c73652);
    color: #ffffff;
    font-weight: 700;
    font-size: 13px;
    padding: 9px 24px;
    border: none;
    border-radius: 7px;
}

QPushButton#btnScan:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff5577, stop:1 #e94560);
}

QPushButton#btnMove {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4a90d9, stop:1 #357abd);
    color: #ffffff;
    font-weight: 600;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
}

QPushButton#btnMove:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5aa0e9, stop:1 #4a90d9);
}

QPushButton#btnSortMisplaced {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2ecc71, stop:1 #27ae60);
    color: #ffffff;
    font-weight: 600;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
}

/* Progress bar */
QProgressBar {
    background-color: #0d0d1a;
    border: 1px solid #2a2a4a;
    border-radius: 5px;
    height: 14px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    font-weight: 600;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #e94560, stop:1 #4a90d9);
    border-radius: 4px;
}

/* Tab widget */
QTabWidget::pane {
    border: 1px solid #2a2a4a;
    border-radius: 0 6px 6px 6px;
    background-color: #13131f;
}

QTabBar::tab {
    background-color: #0f0f1a;
    color: #8080aa;
    padding: 7px 16px;
    border: 1px solid #2a2a4a;
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    min-width: 80px;
    font-size: 12px;
}

QTabBar::tab:selected {
    background-color: #13131f;
    color: #e0e0f0;
    border-bottom: 2px solid #e94560;
}

QTabBar::tab:hover {
    color: #c0c8e0;
    background-color: #16162a;
}

/* Tree widget */
QTreeWidget {
    background-color: #13131f;
    border: none;
    alternate-background-color: #16162a;
    show-decoration-selected: 1;
}

QTreeWidget::item {
    padding: 4px 2px;
    border-bottom: 1px solid #1e1e33;
}

QTreeWidget::item:selected {
    background-color: #1e2d5a;
    color: #ffffff;
}

QTreeWidget::item:hover {
    background-color: #1a1a30;
}

QHeaderView::section {
    background-color: #0f0f1a;
    color: #8888bb;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid #2a2a4a;
    border-bottom: 1px solid #2a2a4a;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Line edit / path field */
QLineEdit {
    background-color: #0d0d1a;
    border: 1px solid #2a2a4a;
    border-radius: 5px;
    padding: 6px 10px;
    color: #c0c8e0;
}

QLineEdit:focus {
    border-color: #e94560;
}

/* Scrollbar */
QScrollBar:vertical {
    background: #0f0f1a;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #2a2a4a;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #e94560;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* CheckBox & TreeWidget Indicator */
QCheckBox, QTreeWidget {
    spacing: 8px;
    color: #c0c8e0;
}

QCheckBox::indicator, QTreeWidget::indicator {
    width: 15px;
    height: 15px;
    border-radius: 3px;
    border: 1px solid #3a3a6a;
    background: #0d0d1a;
}

QCheckBox::indicator:checked, QTreeWidget::indicator:checked {
    background: #e94560;
    border-color: #e94560;
    image: url(none);
}

/* ComboBox */
QComboBox {
    background-color: #0d0d1a;
    border: 1px solid #2a2a4a;
    border-radius: 5px;
    padding: 4px 8px;
    color: #c0c8e0;
    min-width: 90px;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox:hover {
    border-color: #e94560;
}

QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 1px solid #e94560;
    selection-background-color: #e94560;
    color: #e0e0f0;
}

/* Labels */
QLabel#statusLabel {
    color: #8888bb;
    font-size: 11px;
    padding: 3px 6px;
}

QLabel#statsLabel {
    color: #e94560;
    font-weight: 700;
    font-size: 13px;
}

/* Splitter */
QSplitter::handle {
    background-color: #2a2a4a;
}

/* Text edit (log) */
QTextEdit {
    background-color: #0a0a14;
    border: 1px solid #2a2a4a;
    border-radius: 5px;
    color: #90d090;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
    padding: 6px;
}

/* Post-scan banner */
#bannerWidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1a3a2a, stop:1 #1a2a3a);
    border: 1px solid #2ecc71;
    border-radius: 7px;
    padding: 4px;
}

/* Folder mode row badges */
#modeBadgeMove    { color: #2ecc71; font-weight: 700; }
#modeBadgeReport  { color: #e74c3c; font-weight: 700; }
#modeBadgeInbox   { color: #4a90d9; font-weight: 700; }

/* Warning badge */
#warnBadge {
    color: #f39c12;
    font-weight: 700;
    font-size: 11px;
}
"""
