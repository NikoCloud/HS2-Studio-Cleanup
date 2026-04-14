import os
import sqlite3

con = sqlite3.connect(r'C:\HS2\_StudioCleanup.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

def check_offset(name):
    cur.execute("SELECT path FROM files WHERE path LIKE ? LIMIT 1", ('%' + name + '%',))
    res = cur.fetchone()
    if not res: return
    with open(res['path'], 'rb') as f:
        data = f.read()
    idx = data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')
    if idx == -1: return
    tail = data[idx+12:]
    
    pos = -1
    for m in (b"HS2CharaHeader", b"AIS_Chara", b"HS2_Chara", b"KoiKatuCharaHead"):
        p = tail.find(m)
        if p != -1:
            if pos == -1 or p < pos:
                pos = p
    print(f"[{name}] -> Marker at offset {pos}")
    if pos > 0:
        print(f"  First 20 bytes: {repr(tail[:20])}")

check_offset("Bod 1.png")
check_offset("Blow job sofa 1.png")
check_offset("BR-Chan HS2 Rev2.png")
check_offset("2025_0305_2110_09_601.png")
check_offset("Isabela.png")
