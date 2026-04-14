from pathlib import Path

def get_community_subpath(filepath: Path, hs2_root: Path, canonical_base: str) -> Path:
    """
    Given an absolute file path and the expected canonical base (e.g., 'userdata/chara/female'),
    extracts the author/community folder name (the parent of UserData) and any nested subdirectories
    after the canonical base, merging them into a single relative Path object.
    
    Example input: 
      C:\\HS2\\mods\\Discord\\cunihinx\\UserData\\chara\\female\\HS2ChaF_Jill.png
      canonical_base = 'userdata/chara/female'
    Example output:
      [Community]\\cunihinx
    """
    try:
        parts_lower = [p.lower() for p in filepath.parts]
        
        # 1. Extract Author (Parent directory of 'UserData')
        author = None
        if 'userdata' in parts_lower:
            ud_idx = parts_lower.index('userdata')
            parent_idx = len(filepath.parts) - 1 - ud_idx
            # Get the actual original case folder name
            parent_path = filepath.parents[parent_idx]
            
            # Ensure the parent is not the root of the drive or the HS2 root itself
            if parent_path != hs2_root and hs2_root in parent_path.parents:
                author = parent_path.name

        # 2. Extract Suffix (Any subdirectories after the canonical base, before the filename)
        base_parts = [p.lower() for p in Path(canonical_base).parts]
        match_idx = -1
        # Find exactly where the canonical base sequence appears in the filepath
        for i in range(len(parts_lower) - len(base_parts) + 1):
            if parts_lower[i:i+len(base_parts)] == base_parts:
                match_idx = i
                break
                
        suffix_path = Path()
        if match_idx != -1:
            suffix_parts = filepath.parts[match_idx + len(base_parts) : -1]
            if suffix_parts:
                suffix_path = Path(*suffix_parts)

        # 3. Assemble the relative extra path
        extra = Path()
        if author:
            # If the author folder doesn't already have 'community' or 'mods' in its name, wrap it
            if 'community' not in author.lower() and 'mods' not in author.lower():
                extra = extra / '[Community]' / author
            else:
                extra = extra / author
                
        if suffix_path != Path():
            extra = extra / suffix_path
            
        return extra
    except Exception as e:
        print('Error:', e)
        return Path()


if __name__ == "__main__":
    hs2_root = Path(r'C:\HS2')
    
    # Test 1: Full community path with Discord author
    p1 = Path(r'C:\HS2\mods\Sideloader Modpack - Bleeding Edge\Discord\cunihinx\UserData\chara\female\HS2ChaF_20241219171416111_Jill Warrick FFXVI (NGSv2).png')
    res1 = get_community_subpath(p1, hs2_root, 'userdata/chara/female')
    print('Target 1:', hs2_root / 'UserData' / 'chara' / 'female' / res1 / p1.name)

    # Test 2: Standard subfolder without custom author root
    p2 = Path(r'C:\HS2\UserData\chara\female\My Custom Cards\card.png')
    res2 = get_community_subpath(p2, hs2_root, 'userdata/chara/female')
    print('Target 2:', hs2_root / 'UserData' / 'chara' / 'female' / res2 / p2.name)

    # Test 3: Root female folder (no extra path)
    p3 = Path(r'C:\HS2\UserData\chara\female\card.png')
    res3 = get_community_subpath(p3, hs2_root, 'userdata/chara/female')
    print('Target 3:', hs2_root / 'UserData' / 'chara' / 'female' / res3 / p3.name)
