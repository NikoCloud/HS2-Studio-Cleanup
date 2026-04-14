import os
import sqlite3

con = sqlite3.connect(r'C:\HS2\_StudioCleanup.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

def dump_tail(name):
    cur.execute("SELECT path FROM files WHERE path LIKE ? LIMIT 1", ('%' + name + '%',))
    res = cur.fetchone()
    if not res:
        print(f"Not found: {name}")
        return
    path = res['path']
    with open(path, 'rb') as f:
        data = f.read()
    idx = data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')
    if idx != -1:
        tail = data[idx+12:]
        print(f"[{name}] -> {repr(tail[:60])}")
    else:
        print(f"[{name}] -> No IEND")

dump_tail("Bod 1.png")
dump_tail("Blow job sofa 1.png")
dump_tail("Dildo bed 1.png")
dump_tail("BR-Chan HS2 Rev2.png")
