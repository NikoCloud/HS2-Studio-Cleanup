import sqlite3
import re

con = sqlite3.connect(r'C:\HS2\_StudioCleanup.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

cur.execute("SELECT path FROM files WHERE path LIKE '%Bod 1.png%' LIMIT 1")
res = cur.fetchone()

if res:
    path = res['path']
    with open(path, 'rb') as f:
        data = f.read()
    
    idx = data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')
    if idx != -1:
        tail = data[idx+12:]
        
        strings = re.findall(b'[a-zA-Z0-9_\-\.]{6,}', tail)
        seen = set()
        unique_strings = []
        for s in strings:
            if s not in seen:
                seen.add(s)
                unique_strings.append(s.decode('ascii', errors='ignore'))
        
        print('Strings found in tail:', unique_strings[:50])
