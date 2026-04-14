import sqlite3
import re

con = sqlite3.connect(r'C:\HS2\_StudioCleanup.db')
cur = con.cursor()

def test_guids(name):
    cur.execute("SELECT path FROM files WHERE path LIKE ? LIMIT 1", ('%' + name + '%',))
    res = cur.fetchone()
    if not res: return
    with open(res[0], 'rb') as f: data = f.read()
    idx = data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')
    if idx == -1: return
    tail = data[idx+12:]
    guids = set()
    for m in re.finditer(rb'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', tail):
        guids.add(m.group().decode())
    for m in re.finditer(rb'[\x22\x00]([\w]{3,}[\w.\-]{2,61})[\x22\x00]', tail):
        cand = m.group(1).decode(errors='ignore')
        if cand.count('.') > 0 and not cand.startswith('Unity') and not cand.startswith('System'):
            guids.add(cand)
    print(f'[{name}] GUIDs extracted: {len(guids)}')

test_guids("Bod 1.png")
test_guids("Blow job sofa 1.png")
