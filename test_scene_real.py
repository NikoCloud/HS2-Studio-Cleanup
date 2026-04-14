import codecs
path = r'C:\HS2\UserData\Studio\scene\2025_0305_2110_09_601.png'
try:
    with open(path, 'rb') as f:
        data = f.read()
    
    idx = data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')
    if idx != -1:
        tail = data[idx+12:]
        import re
        strings = set(re.findall(rb'[A-Za-z0-9_]{5,}', tail))
        print(sorted([s.decode() for s in strings]))
    else:
        print("No IEND")
except Exception as e:
    print(e)
