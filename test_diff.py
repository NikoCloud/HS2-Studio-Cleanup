import os
import sqlite3
from pathlib import Path

def get_card_binary(path_str):
    with open(path_str, 'rb') as f: data = f.read()
    idx = data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')
    if idx == -1: return None
    tail = data[idx+12:]
    # Find marker
    for m in (b"HS2CharaHeader", b"AIS_Chara", b"HS2_Chara", b"KoiKatuCharaHead"):
        p = tail.find(m)
        if p != -1 and p < 64:
            return tail[p:]
    return None

def analyze(label, path):
    print(f"\n--- {label} ---")
    print(os.path.basename(path))
    b = get_card_binary(path)
    if not b:
        print("Not a valid card")
        return
    print(b[:128].hex(' ', 4))

analyze("FEMALE", r"C:\HS2\UserData\chara\female\BR-Chan HS2 Rev2.png")
analyze("FEMALE", r"C:\HS2\UserData\chara\female\Isabela.png")
analyze("MALE", r"C:\HS2\UserData\chara\male\HS2ChaM_20240408200000.png")
analyze("MALE", r"C:\HS2\UserData\chara\male\HS2ChaM_20220116154240357.png")
