import sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\mizua\OneDrive\Desktop\StudioCLeanup")

from handlers.characard_handler import parse_chara_card
import sqlite3

def run_test(name):
    con = sqlite3.connect(r'C:\HS2\_StudioCleanup.db')
    cur = con.cursor()
    cur.execute("SELECT path FROM files WHERE path LIKE ? LIMIT 1", ('%' + name + '%',))
    res = cur.fetchone()
    if not res: return
    info = parse_chara_card(Path(res[0]), "C:\\HS2\\UserData\\chara\\test")
    if info:
        print(f"[{name}] Detected Gender: {info.gender}")
    else:
        print(f"[{name}] Not a characard")

run_test("BR-Chan HS2 Rev2.png")
run_test("HS2ChaM")
run_test("Zeff Gunnoff")
