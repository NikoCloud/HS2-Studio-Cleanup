<p align="center">
  <img src="docs/screenshots/banner.png" alt="HS2 Studio Cleanup banner" width="700"/>
</p>

<h1 align="center">HS2 Studio Cleanup</h1>

<p align="center">
  High-performance deduplication &amp; organiser for large Honey Select 2 installations
</p>

<p align="center">
  <a href="https://github.com/NikoCloud/HS2-Studio-Cleanup/releases/latest"><img src="https://img.shields.io/github/v/release/NikoCloud/HS2-Studio-Cleanup?label=Download&style=for-the-badge&color=2ecc71" alt="Download"/></a>
  <img src="https://img.shields.io/badge/Platform-Windows-informational?style=for-the-badge" alt="Platform"/>
  <img src="https://img.shields.io/badge/Python-3.12+-blue?style=for-the-badge" alt="Python"/>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-green?style=for-the-badge" alt="License"/></a>
</p>

---

> **Part of the Persona Workflow toolkit** — see also:
> | Tool | Purpose |
> |---|---|
> | [Persona Asset Forge](https://github.com/NikoCloud/Persona-Asset-Forge) | Background removal & sprite grid slicing |
> | [Persona Packager Studio](https://github.com/NikoCloud/Persona-Packager-Studio) | Character card editor & .charx packager |
> | [KenzatoTool](https://github.com/NikoCloud/KenzatoTool) | Bulk card downloader from kenzato.uk |

---

## Screenshots

<p align="center"><em>Screenshots coming soon</em></p>

---

## Features

### Performance & Scale
- **Handles 1.5TB+ / 300K+ files** with SQLite-backed scan caching — re-scans only modified files
- **Multi-phase dedup**: size grouping → partial hash → full XXH3 hash → metadata → version analysis

### Intelligent Organisation
- **3-Mode Folder Protection**
  - **Move** — deduplicates and moves to `_Cleanup/`
  - **Report** — audit mode, flags without touching files
  - **Inbox** — auto-sorts new files into gender/category subfolders
- **Scene Dependency Awareness** — warns before moving mods referenced by Studio scenes
- **Misplacement Detection** — routes files to their canonical game folder

### Safety
- **Non-destructive** — every move is logged in `_manifest.json` with full undo support
- **Dry Run** — preview the entire cleanup pipeline without touching a file
- **Interactive Keeper Swap** — choose which duplicate copy to keep via the GUI

---

## Installation

### Portable EXE *(Recommended)*
1. Go to the **[Latest Release](https://github.com/NikoCloud/HS2-Studio-Cleanup/releases/latest)**
2. Download `HS2_Studio_Cleanup.exe`
3. Run directly — no Python or installation required

### Installer
1. Download `HS2StudioCleanup_Setup.exe` from the **[Latest Release](https://github.com/NikoCloud/HS2-Studio-Cleanup/releases/latest)**
2. Run the installer — adds a Start Menu entry and optional desktop shortcut

### From Source
```bash
git clone https://github.com/NikoCloud/HS2-Studio-Cleanup.git
cd HS2-Studio-Cleanup
pip install -r requirements.txt
python main.py
```

---

## Usage

1. **Set HS2 Root** — point to your Honey Select 2 directory
2. **Configure Folder Modes** — right-click folders in the tree to set Move / Report / Inbox
3. **Scan** — let the engine analyse your library
4. **Review** — check results across the Duplicates, Older Versions, and Misplaced tabs
5. **Execute** — click "Move Selected" to apply cleanup

---

## License

Apache 2.0 — see [LICENSE](LICENSE) for full terms.  
Copyright 2025 NikoCloud

---

*Powered by PyQt6 and xxhash. Designed for the HS2 community.*
