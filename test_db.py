import sys
sys.path.append(r'C:\Users\mizua\OneDrive\Desktop\StudioCLeanup')
from handlers.scene_handler import parse_scene
from core import index_db
import sqlite3
from pathlib import Path

index_db.init_db(Path(r'C:\HS2'))
path_str = r'C:\HS2\UserData\Studio\scene\upai_scene_0000001.png'
p = Path(path_str)

si = parse_scene(p)
print(f"is_scene: {si.is_scene}, mod_guids: {len(si.mod_guids)}")

fid = index_db.get_file_id(path_str)
print(f"fid: {fid}")

if fid and si.mod_guids:
    print("Upserting!")
    index_db.upsert_scene_dependencies(fid, si.mod_guids)
else:
    print("Failed to upsert")

with index_db._conn() as con:
    print("Count in db:", con.execute('SELECT COUNT(*) FROM scene_dependencies').fetchone()[0])
