# HS2 Studio Cleanup

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)

**HS2 Studio Cleanup** is a high-performance deduplication and organization tool designed specifically for large Honey Select 2 installations. It intelligently handles zipmods, character cards, coordinates, and studio scenes to keep your setup clean and optimized.

---

## 🌟 Key Features

### 🚀 Performance & Scale
- **Optimized Scanning**: Handles libraries exceeding 1.5TB and 300K+ files with ease.
- **Smart Indexing**: SQLite-backed caching for incredibly fast re-scans by only checking modified files.
- **Multi-Phase Deduplication**: Fast size-grouping → partial hashing → full cryptographic hashing → metadata verification.

### 🍱 Intelligent Organization
- **3-Mode Protection**:
  - **Move**: Standard deduplication (moves files to `_Cleanup/Duplicates`).
  - **Report**: Only flags issues without moving files (audit mode).
  - **📥 Inbox**: Automatically sorts new files into gendered/category subfolders.
- **Gender Detection**: Extracts gender markers from filename tags, embedded metadata bytes, and folder context.
- **Coordinate Support**: Recognizes clothing cards (`.png`) and preserves creator subfolder hierarchies (e.g., `Kenzato/kittylord`).
- **Misplacement Detection**: Flags files in incorrect directories and routes them to their rightful place.

### 🛡️ Safety & Manual Control
- **Scene Dependency Awareness**: Warns you if a duplicate mod is referenced by your Studio scenes before you move it.
- **Interactive Keeper Swap**: Choose exactly which copy you want to keep directly from the GUI.
- **Non-Destructive Operations**: Every move is logged in a `_manifest.json` for full auditability.
- **Dry Run Support**: Test your entire cleanup pipeline without touching a single file.

---

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/NikoCloud/HS2-Studio-Cleanup.git
   cd HS2-Studio-Cleanup
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

---

## 🖥️ Usage

1. **Set your HS2 Root**: Point the application to your main Honey Select 2 directory.
2. **Configure Folder Modes**: Right-click folders in the tree to set them as `Move`, `Report`, or `Inbox`.
3. **Scan**: Let the engine analyze your library.
4. **Review**: Check the tabbed results (Duplicates, Older Versions, Misplaced).
5. **Execute**: Use "Move Selected" to apply the organization rules.

---

## ⚖️ License

Distributed under the **Apache License 2.0**. See `LICENSE` for more information.

## 🙏 Acknowledgements
- Powered by `PyQt6` and `xxhash`.
- Designed for the HS2 community.
