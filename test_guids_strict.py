import sqlite3, re
con = sqlite3.connect(r'C:\HS2\_StudioCleanup.db')
cur = con.cursor()
cur.execute("SELECT path FROM files WHERE path LIKE '%Blow job sofa 1.png%' LIMIT 1")
path = cur.fetchone()[0]
with open(path, 'rb') as f: data = f.read()
tail = data[data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')+12:]

guids = set()
for m in re.finditer(rb'[\x22\x00]([\w][\w.\-]{5,63})[\x22\x00]', tail):
    cand = m.group(1).decode('ascii', errors='ignore')
    if '.' in cand and not cand.startswith('Unity') and not cand.startswith('System'):
        guids.add(cand)

print('GUIDs:', guids)
