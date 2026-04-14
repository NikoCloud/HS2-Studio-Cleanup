import sqlite3
import os

con = sqlite3.connect(r'C:\HS2\_StudioCleanup.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

cur.execute("SELECT path FROM files WHERE path LIKE '%Bod 1.png%' OR path LIKE '%2025_0305_2110_09_601.png%' LIMIT 1")
res = cur.fetchone()

if res:
    path = res['path']
    print(f'Found: {path}')
    
    with open(path, 'rb') as f:
        data = f.read()
    
    idx = data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')
    if idx != -1:
        tail = data[idx+12:]
        print(f'Tail length: {len(tail)}')
        print(f'First 100 bytes:')
        print(repr(tail[:100]))
        
        # Check for our scene markers
        for m in (b'Studio00', b'KStudio', b'studioVersion', b'SceneInfo', b'H2Studio', b'HS2_Chara'):
            if m in tail:
                print(f'Found marker: {m}')
    else:
        print('No IEND found')
else:
    print('File not found in DB')
