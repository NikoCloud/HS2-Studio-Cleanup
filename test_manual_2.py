import os
import sqlite3
from pathlib import Path

def test_manual(name):
    con = sqlite3.connect(r'C:\HS2\_StudioCleanup.db')
    cur = con.cursor()
    cur.execute("SELECT path FROM files WHERE path LIKE ? LIMIT 1", ('%' + name + '%',))
    res = cur.fetchone()
    if not res:
        print(f"Not found: {name}")
        return
    path_str = res[0]

    with open(path_str, 'rb') as f: data = f.read()
    idx = data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')
    if idx == -1: return
    tail = data[idx+12:]
    
    # MessagePack string "Parameter" is 0xa9 + "Parameter"
    p_idx = tail.find(b'\xa9Parameter')
    if p_idx == -1:
        print(f"[{os.path.basename(path_str)}] No \xa9Parameter found")
        return
        
    print(f"\n[{os.path.basename(path_str)}]")
    print("BlockHeader area:", tail[p_idx:p_idx+40].hex(' '))
    
    # We also need to find the actual Parameter block data.
    # We can search for the "fullname" property which is also a string (or the text inside)
    # But wait, MessagePack serializes fields in order without names for MessagePackObject(true)!
    # The fields are: version(str), sex(byte), fullname(str), personality(int).
    # Since version is usually "0.0.0" or "1.0.0", let's look for b"\xa50.0.0" or b"\xa51.0.0" (length 5 string).
    
    v_idx = tail.find(b'\xa50.0.0', p_idx+40)
    if v_idx == -1:
        v_idx = tail.find(b'\xa51.0.0', p_idx+40)
    if v_idx == -1:
        v_idx = tail.find(b'\xa52.0.0', p_idx+40)
        
    if v_idx != -1:
        b_area = tail[v_idx-4 : v_idx+32]
        print("Data area around version:", b_area.hex(' '))
        
        # sex byte is immediately after version string. version string is \xa5 + 5 bytes = 6 bytes.
        # So sex byte is at v_idx + 6.
        sex_byte = tail[v_idx + 6]
        print(f"Sex byte: {sex_byte} (0=Male, 1=Female, 2=?)")
    else:
        print("Could not find version string.")
        
test_manual("BR-Chan HS2 Rev2.png")
test_manual("HS2ChaM")
test_manual("20241224070550010_Lofang")
test_manual("20250105091650504")
