import bsp_tool

bsp = bsp_tool.load_bsp(r"c:\Program Files (x86)\Steam\steamapps\common\Momentum Mod Playtest\momentum\maps\surf_mom_training.bsp")

plane = bsp.PLANES[bsp.NODES[1].plane]

print(plane)

point1 = (5000, 1000, 0)
point2 = (5000, -1000, 0)

for point in [point1, point2]:
    result = (
        point[0] * plane.normal[0]
        + point[1] * plane.normal[1]
        + point[2] * plane.normal[2]
        - plane.distance
    )

node = bsp.NODES[2]

print("Plane:", bsp.PLANES[node.plane])
print("Children:", node.children)

for child in node.children:
    child_node = bsp.NODES[child]
    print("Child:", child)
    print("Min:", child_node.bounds.mins)
    print("Max:", child_node.bounds.maxs)
