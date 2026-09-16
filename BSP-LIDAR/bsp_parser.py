import bsp_tool

bsp = bsp_tool.load_bsp(r"c:\Program Files (x86)\Steam\steamapps\common\Momentum Mod Playtest\momentum\maps\surf_mom_training.bsp")

print("BSP version:", bsp.version)
print("Number of planes:", len(bsp.PLANES))
print("Number of nodes:", len(bsp.NODES))
print("Number of leaves:", len(bsp.LEAVES))
print("Number of vertices:", len(bsp.VERTICES))
print("Number of faces:", len(bsp.FACES))
