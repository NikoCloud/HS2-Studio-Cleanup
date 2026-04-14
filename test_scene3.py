import sqlite3, re
con = sqlite3.connect(r'C:\HS2\_StudioCleanup.db')
cur = con.cursor()
cur.execute("SELECT path FROM files WHERE path LIKE '%Bod 1.png%' LIMIT 1")
path = cur.fetchone()[0]
with open(path, 'rb') as f: data = f.read()
idx = data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')
print('IEND:', idx)
if idx != -1:
    tail = data[idx+12:]
    strings = set(re.findall(rb'[a-zA-Z0-9_\-\.]{6,}', tail))
    unique = [s.decode() for s in strings]
    print(unique[:100])
