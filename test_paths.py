from pathlib import Path

def get_community_subpath(filepath: Path, hs2_root: Path, canonical_base: str) -> Path:
    try:
        parts_lower = [p.lower() for p in filepath.parts]
        
        author = None
        if "userdata" in parts_lower:
            ud_idx = parts_lower.index("userdata")
            # Get the actual original case folder name for the parent of UserData
            parent_path = filepath.parents[len(filepath.parts) - 1 - ud_idx + 1]
            if parent_path != hs2_root and hs2_root in parent_path.parents:
                author = parent_path.name

        # Normalise canonical base parts
        base_parts = [p.lower() for p in Path(canonical_base).parts]
        match_idx = -1
        # Find exactly where the canonical base sequence appears in the filepath
        for i in range(len(parts_lower) - len(base_parts) + 1):
            if parts_lower[i:i+len(base_parts)] == base_parts:
                match_idx = i
                break
                
        suffix_path = Path()
        if match_idx != -1:
            # Everything after the canonical base, excluding the filename itself
            suffix_parts = filepath.parts[match_idx + len(base_parts) : -1]
            if suffix_parts:
                suffix_path = Path(*suffix_parts)

        extra = Path()
        if author:
            if "community" not in author.lower() and "mods" not in author.lower():
                extra = extra / "[Community]" / author
            else:
                extra = extra / author
                
        if suffix_path != Path():
            extra = extra / suffix_path
            
        return extra
    except Exception as e:
        print("Error:", e)
        return Path()

hs2_root = Path(r"C:\HS2")

p1 = Path(r"C:\HS2\mods\Sideloader Modpack - Bleeding Edge\Discord\cunihinx\UserData\chara\female\HS2ChaF_20241219171416111_Jill Warrick FFXVI (NGSv2).png")
res1 = get_community_subpath(p1, hs2_root, "userdata/chara/female")
print("Target 1:", hs2_root / "UserData" / "chara" / "female" / res1 / p1.name)

p2 = Path(r"C:\HS2\[Community] Mods\UserData\Studio\scene\gamedemo\scene1.png")
res2 = get_community_subpath(p2, hs2_root, "userdata/studio/scene")
print("Target 2:", hs2_root / "UserData" / "Studio" / "scene" / res2 / p2.name)

