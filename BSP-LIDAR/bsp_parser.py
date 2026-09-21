import bsp_tool
#Load the .bsp map using bsp_tool
bsp = bsp_tool.load_bsp(r"c:\Program Files (x86)\Steam\steamapps\common\Momentum Mod Playtest\momentum\maps\surf_utopia.bsp")
#Define a 3D coordinate point (X,Y,Z) to test within map space
position = (-12720.69, -5.97, 11479.33)
#Given position and plane we do the dot product and subtract it from the distance to find on which side of the plane our position is
def side(position, plane):
  side =  (position[0]*plane.normal[0]+ position[1]*plane.normal[1]+position[2]*plane.normal[2])-plane.distance
  return side
#Define recursive function to go through the bsp and find the leaf our position is in
def find_leaf(position, node_index):
#If we get a negative value then that tells use we reached the leaf
#Leaf nodes are encoded as -(node +1) so when we get a leaf -256 its node index is 255
 if(node_index <0):
    leaf_index=-node_index-1
    return leaf_index
  
 node = bsp.NODES[node_index]
 plane = bsp.PLANES[node.plane]
 #If out side value is positive then we move left down the BSP tree else we move right
 if side(position,plane)>=0:
     next_node_index= node.children[0]
 else:
     next_node_index= node.children[1]
#return our lead node index
 return find_leaf(position, next_node_index)

map_geometry = []

for face_index, face in enumerate(bsp.FACES):
    surfedges = bsp.SURFEDGES[
       face.first_edge:
       face.first_edge + face.num_edges
    ]
    vertices = []

    for surfedge in surfedges:
        edge_index = abs(surfedge)
        edge = bsp.EDGES[edge_index]
        if surfedge >= 0:
           vertex_index = edge[0]
        else: 
           vertex_index = edge[1]
        vertex = bsp.VERTICES[vertex_index]
        vertices.append(vertex)

    if len(vertices) >= 3:
       map_geometry.append((face_index, vertices))

print("BSP FACES:", len(bsp.FACES))
print("Total stored geometry:", len(map_geometry))
print("First entry:", map_geometry[0])
print("Last entry:", map_geometry[-1])
