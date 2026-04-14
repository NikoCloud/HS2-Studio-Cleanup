import sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\mizua\OneDrive\Desktop\StudioCLeanup")

from core.org_engine import get_chara_destination

hs2_root = Path(r"C:\HS2")
p1 = Path(r"C:\HS2\mods\Sideloader Modpack - Bleeding Edge\Discord\cunihinx\UserData\chara\female\HS2ChaF_20241219171416111_Jill Warrick FFXVI (NGSv2).png")

dest = get_chara_destination(p1, hs2_root, "female")
print(f"Target: {dest}")

