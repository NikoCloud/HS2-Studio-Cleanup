import os, re

path = None
for dp, dn, fn in os.walk(r'C:\HS2'):
    if 'Bod 1.png' in fn:
        path = os.path.join(dp, 'Bod 1.png')
        break

if not path:
    print('Not found')
else:
    print('Found at:', path)
    with open(path, 'rb') as f:
        data = f.read()
    idx = data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')
    print('IEND idx:', idx)
    if idx != -1:
        tail = data[idx+12:]
        strings = set(re.findall(rb'[a-zA-Z0-9_\-\.]{6,}', tail))
        print([s.decode() for s in strings][:50])
