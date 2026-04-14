"""
core/movement_engine.py — Non-destructive file moving with manifest logging and undo.
"""

import json
import shutil
import time
from pathlib import Path
from typing import Optional

from core import index_db

_CLEANUP_ROOT_NAME = "_Cleanup"

# Sub-folder names inside _Cleanup
_SUBFOLDER = {
    "duplicate":          "Duplicates",
    "older_version":      "Older_Versions",
    "possible_duplicate": "Possible_Duplicates",
    "misplaced":          "Misplaced",
    "unknown_metadata":   "Unknown_Metadata",
    "orphaned":           "Orphaned",
}


def _get_cleanup_root(hs2_root: Path) -> Path:
    return hs2_root / _CLEANUP_ROOT_NAME


def _make_unique_path(dest: Path) -> Path:
    """
    If dest already exists append .copy_N AFTER the full filename
    (including extension) to avoid confusion with version numbers.
    e.g. hair.zipmod → hair.zipmod.copy_1
    """
    if not dest.exists():
        return dest
    n = 1
    while True:
        candidate = dest.with_name(dest.name + f".copy_{n}")
        if not candidate.exists():
            return candidate
        n += 1


def _manifest_path(folder: Path) -> Path:
    return folder / "_manifest.json"


def _write_manifest_entry(folder: Path, entry: dict) -> None:
    mpath = _manifest_path(folder)
    if mpath.exists():
        with open(mpath, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "app": "HS2 Studio Cleanup",
            "created": _iso_now(),
            "entries": [],
        }
    data["entries"].append(entry)
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# ── Public API ────────────────────────────────────────────────────────────────

def move_to_cleanup(
    filepath: Path,
    hs2_root: Path,
    category: str,          # key in _SUBFOLDER
    reason: str,
    details: str = "",
    related_file: Optional[Path] = None,
    dry_run: bool = False,
) -> Optional[Path]:
    """
    Move a file to the appropriate _Cleanup sub-folder.
    Returns the new path, or None if dry_run or error.
    In dry_run mode nothing is written to disk at all — call write_dry_run_report()
    separately to produce a human-readable summary.
    """
    if dry_run:
        return None

    subfolder_name = _SUBFOLDER.get(category, "Orphaned")
    dest_dir = _get_cleanup_root(hs2_root) / subfolder_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = _make_unique_path(dest_dir / filepath.name)

    try:
        shutil.move(str(filepath), str(dest))
    except Exception:
        return None

    entry = {
        "original_path": str(filepath),
        "moved_to": str(dest),
        "reason": reason,
        "details": details,
        "related_file": str(related_file) if related_file else None,
        "moved_at": _iso_now(),
    }
    index_db.record_movement(str(filepath), str(dest), category, details,
                              str(related_file) if related_file else "")
    _write_manifest_entry(dest_dir, entry)
    return dest


def write_report_entry(
    hs2_root: Path,
    folder_name: str,
    filepath: Path,
    category: str,
    reason: str,
    details: str = "",
    related_file: Optional[Path] = None,
) -> None:
    """
    Report Mode: write finding to _Cleanup/_Reports/<folder>_report.json
    without moving any file.
    """
    report_dir = _get_cleanup_root(hs2_root) / "_Reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"{folder_name}_report.json"

    entry = {
        "path": str(filepath),
        "moved_to": None,
        "category": category,
        "reason": reason,
        "details": details,
        "related_file": str(related_file) if related_file else None,
        "found_at": _iso_now(),
    }

    if report_file.exists():
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "app": "HS2 Studio Cleanup",
            "folder": folder_name,
            "created": _iso_now(),
            "entries": [],
        }
    data["entries"].append(entry)
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    index_db.record_movement(str(filepath), None, category, details,
                              str(related_file) if related_file else "")


def move_to_destination(
    filepath: Path,
    destination_dir: Path,
    reason: str,
    dry_run: bool = False,
) -> Optional[Path]:
    """
    Inbox Mode: move file directly to its correct HS2 destination.
    Creates creator/author subfolders as needed.
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    dest = _make_unique_path(destination_dir / filepath.name)

    if not dry_run:
        try:
            shutil.move(str(filepath), str(dest))
        except Exception:
            return None
        index_db.record_movement(str(filepath), str(dest), "inbox_sort", reason)
        return dest
    return None


def write_dry_run_report(hs2_root: Path, findings: list[dict]) -> Path:
    """
    Write a human-readable HTML dry-run report to _Cleanup/DryRun_Report.html.
    Each entry in findings must have: file, category, reason, keeper (optional).
    Returns the path of the written report.
    """
    report_dir = _get_cleanup_root(hs2_root)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "DryRun_Report.html"

    # Group by category
    by_cat: dict[str, list[dict]] = {}
    for f in findings:
        by_cat.setdefault(f["category"], []).append(f)

    _CAT_LABELS = {
        "duplicate":          ("🔴", "Duplicates"),
        "older_version":      ("🟡", "Older Versions"),
        "possible_duplicate": ("🟠", "Possible Duplicates"),
        "misplaced":          ("🔵", "Misplaced Files"),
        "unknown_metadata":   ("⚪", "Unknown Metadata"),
        "orphaned":           ("⚫", "Orphaned Files"),
    }

    sections = []
    for cat, entries in by_cat.items():
        icon, label = _CAT_LABELS.get(cat, ("", cat.replace("_", " ").title()))
        rows = []
        for e in entries:
            keeper_cell = f'<td class="path">{e["keeper"]}</td>' if e.get("keeper") else "<td>—</td>"
            rows.append(
                f'<tr>'
                f'<td class="path">{e["file"]}</td>'
                f'<td>{e["reason"]}</td>'
                f'{keeper_cell}'
                f'</tr>'
            )
        sections.append(f"""
        <section>
          <h2>{icon} {label} <span class="count">({len(entries)})</span></h2>
          <table>
            <thead><tr><th>File</th><th>Reason</th><th>Keeper / Destination</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
          </table>
        </section>""")

    total = len(findings)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>HS2 Studio Cleanup — Dry Run Report</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; background: #1a1a2e; color: #e0e0f0; margin: 0; padding: 20px; }}
    h1 {{ color: #7b8cde; border-bottom: 2px solid #2a2a4a; padding-bottom: 8px; }}
    h2 {{ color: #aabbff; margin-top: 32px; }}
    .meta {{ color: #888899; font-size: 13px; margin-bottom: 24px; }}
    .count {{ color: #888899; font-size: 14px; font-weight: normal; }}
    .summary {{ background: #0f0f1a; border: 1px solid #2a2a4a; border-radius: 6px;
                padding: 12px 20px; display: inline-block; margin-bottom: 24px; }}
    .summary b {{ color: #e0e0f0; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }}
    th {{ background: #2a2a4a; color: #aaaacc; text-align: left; padding: 6px 10px; }}
    td {{ padding: 5px 10px; border-bottom: 1px solid #2a2a4a; vertical-align: top; }}
    tr:hover td {{ background: #1e1e3a; }}
    td.path {{ font-family: Consolas, monospace; font-size: 11px; color: #99aacc; word-break: break-all; }}
    section {{ margin-bottom: 40px; }}
  </style>
</head>
<body>
  <h1>HS2 Studio Cleanup — Dry Run Report</h1>
  <div class="meta">
    Generated: {_iso_now()} &nbsp;|&nbsp; Root: {hs2_root} &nbsp;|&nbsp; Mode: DRY RUN (no files were moved)
  </div>
  <div class="summary">
    <b>Total findings: {total}</b>
    &nbsp;&nbsp;
    {'&nbsp;&nbsp;'.join(
        f'{_CAT_LABELS.get(c, ("",""))[0]} {_CAT_LABELS.get(c, ("",c))[1]}: <b>{len(v)}</b>'
        for c, v in by_cat.items()
    )}
  </div>
  {''.join(sections)}
</body>
</html>"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    return report_path


def undo_last(hs2_root: Path) -> list[str]:
    """
    Undo the most recent movement batch by reading the DB movements table.
    Returns list of status messages.
    """
    movements = index_db.get_all_movements()
    if not movements:
        return ["Nothing to undo."]
    messages = []
    # Undo in reverse order
    for row in list(movements)[:50]:  # Safety cap — undo last 50 moves
        new_path = row["new_path"]
        orig_path = row["original_path"]
        if new_path is None:
            continue  # report-only entry
        src = Path(new_path)
        dst = Path(orig_path)
        if not src.exists():
            messages.append(f"⚠  Skipped (not found at cleanup location): {src.name}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src), str(dst))
            index_db.delete_movement(row["id"])
            messages.append(f"✓  Restored: {dst}")
        except Exception as e:
            messages.append(f"✗  Failed to restore {src.name}: {e}")
    return messages
