import os
import sqlite3

def parse_card_gender(path_str):
    with open(path_str, 'rb') as f: data = f.read()
    iend = data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')
    if iend == -1: return None
    tail = data[iend+12:]
    
    # Locate the sex key in the MessagePack map: 0xa3 + "sex"
    sex_idx = tail.find(b'\xa3sex')
    if sex_idx == -1: return None
    
    # The byte immediately following \xa3sex is the value
    sex_val = tail[sex_idx + 4]
    return sex_val

def test_manual(name):
    con = sqlite3.connect(r'C:\HS2\_StudioCleanup.db')
    cur = con.cursor()
    cur.execute("SELECT path FROM files WHERE path LIKE ? LIMIT 1", ('%' + name + '%',))
    res = cur.fetchone()
    if not res: return
    sex = parse_card_gender(res[0])
    gender_str = "Male" if sex == 0 else "Female" if sex == 1 else f"Unknown ({sex})"
    print(f"[{os.path.basename(res[0])}] -> {gender_str}")
    
test_manual("BR-Chan HS2 Rev2.png")
test_manual("HS2ChaM")
test_manual("Zeff Gunnoff")

