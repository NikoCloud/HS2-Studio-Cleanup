import os
from pathlib import Path

def test_manual(path_str):
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
    # Dump 64 bytes around the "Parameter" string 
    print("BlockHeader area:", tail[p_idx:p_idx+64].hex(' '))
    
test_manual(r"C:\HS2\UserData\chara\female\BR-Chan HS2 Rev2.png")
test_manual(r"C:\HS2\UserData\chara\male\HS2ChaM_20240408200000.png")
