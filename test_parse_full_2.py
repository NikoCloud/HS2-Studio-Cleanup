import os
import struct
import sqlite3

def read_msgpack_int(data, offset):
    b = data[offset]
    if b <= 0x7f: return b, offset+1
    if b >= 0xe0: return b - 256, offset+1 # negative fixint
    if b == 0xcc: return data[offset+1], offset+2
    if b == 0xcd: return struct.unpack('>H', data[offset+1:offset+3])[0], offset+3
    if b == 0xce: return struct.unpack('>I', data[offset+1:offset+5])[0], offset+5
    if b == 0xcf: return struct.unpack('>Q', data[offset+1:offset+9])[0], offset+9
    if b == 0xd0: return struct.unpack('>b', data[offset+1:offset+2])[0], offset+2
    if b == 0xd1: return struct.unpack('>h', data[offset+1:offset+3])[0], offset+3
    if b == 0xd2: return struct.unpack('>i', data[offset+1:offset+5])[0], offset+5
    if b == 0xd3: return struct.unpack('>q', data[offset+1:offset+9])[0], offset+9
    return None, offset

def read_msgpack_string(data, offset):
    b = data[offset]
    if 0xa0 <= b <= 0xbf:
        length = b - 0xa0
        return data[offset+1:offset+1+length].decode('utf-8', errors='ignore'), offset+1+length
    if b == 0xd9:
        length = data[offset+1]
        return data[offset+2:offset+2+length].decode('utf-8', errors='ignore'), offset+2+length
    if b == 0xda:
        length = struct.unpack('>H', data[offset+1:offset+3])[0]
        return data[offset+3:offset+3+length].decode('utf-8', errors='ignore'), offset+3+length
    if b == 0xdb:
        length = struct.unpack('>I', data[offset+1:offset+5])[0]
        return data[offset+5:offset+5+length].decode('utf-8', errors='ignore'), offset+5+length
    return None, offset

def parse_card_gender(path_str):
    with open(path_str, 'rb') as f: data = f.read()
    iend = data.rfind(b'\x00\x00\x00\x00IEND\xaeB`\x82')
    if iend == -1: return None
    
    offset = iend + 12
    if offset >= len(data): return None
    
    # Read loadProductNo
    loadProductNo, offset = struct.unpack('<I', data[offset:offset+4])[0], offset+4
    
    def read_7bit_encoded_int():
        nonlocal offset
        value = 0
        shift = 0
        while True:
            b = data[offset]
            offset += 1
            value |= (b & 0x7f) << shift
            shift += 7
            if (b & 0x80) == 0: break
        return value
        
    marker_len = read_7bit_encoded_int()
    marker = data[offset:offset+marker_len].decode('utf-8', errors='ignore')
    offset += marker_len
    
    version_len = read_7bit_encoded_int()
    version = data[offset:offset+version_len].decode('utf-8', errors='ignore')
    offset += version_len
    
    language, offset = struct.unpack('<I', data[offset:offset+4])[0], offset+4
    
    userid_len = read_7bit_encoded_int()
    userid = data[offset:offset+userid_len].decode('utf-8', errors='ignore')
    offset += userid_len
    
    dataid_len = read_7bit_encoded_int()
    dataid = data[offset:offset+dataid_len].decode('utf-8', errors='ignore')
    offset += dataid_len
    
    count, offset = struct.unpack('<I', data[offset:offset+4])[0], offset+4
    
    blockHeaderBytes = data[offset:offset+count]
    offset += count
    
    num, offset = struct.unpack('<q', data[offset:offset+8])[0], offset+8
    base_pos = offset
    
    p_idx = blockHeaderBytes.find(b'\xa9Parameter')
    if p_idx == -1: return None
    
    pos_key_idx = blockHeaderBytes.find(b'\xa3pos', p_idx)
    if pos_key_idx == -1: return None
    
    pos_val_offset = pos_key_idx + 4
    param_pos, _ = read_msgpack_int(blockHeaderBytes, pos_val_offset)
    
    if param_pos is None: return None
    
    # Debug
    print(f"[{os.path.basename(path_str)}] param_pos: {param_pos}, base_pos: {base_pos}")
    
    param_abs_pos = base_pos + param_pos
    arr_b = data[param_abs_pos]
    param_offset = param_abs_pos
    if 0x90 <= arr_b <= 0x9f:
        param_offset += 1
    elif arr_b == 0xdc:
        param_offset += 3
    elif arr_b == 0xdd:
        param_offset += 5
    else: 
        print(arr_b)
        return None
    
    ver, param_offset = read_msgpack_string(data, param_offset)
    sex, param_offset = read_msgpack_int(data, param_offset)
    
    return sex

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

