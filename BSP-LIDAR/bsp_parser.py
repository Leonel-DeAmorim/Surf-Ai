import bsp_tool

bsp = bsp_tool.load_bsp(r"c:\Program Files (x86)\Steam\steamapps\common\Momentum Mod Playtest\momentum\maps\surf_mom_training.bsp")

position = (5000, 1000, 0)

def side(position, plane):
  side =  (position[0]*plane.normal[0]+ position[1]*plane.normal[1]+position[2]*plane.normal[2])-plane.distance
  return side

def find_leaf(position, node_index):

 if(node_index <0):
    leaf_index=-node_index-1
    return leaf_index
  
 node = bsp.NODES[node_index]
 plane = bsp.PLANES[node.plane]
 
 if side(position,plane)>=0:
     next_node_index= node.children[0]
 else:
     next_node_index= node.children[1]

 return find_leaf(position, next_node_index)

node = bsp.NODES[0]
plane = bsp.PLANES[node.plane]

print("Distance:",side(position, plane))
print("In node:",find_leaf(position, 0))
print(bsp.LEAVES[256])
print(bsp.LEAVES[257])
