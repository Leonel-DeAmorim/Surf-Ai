//contents for bsp parser
file_path = r"C:\Program Files (x86)\Steam\steamapps\common\Momentum Mod Playtest\momentum\maps\surf_mom_training.bsp"

with open(file_path, "rb") as f:
    data = f.read()

print(len(data))
print(data[:4])
