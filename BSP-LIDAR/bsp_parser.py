import bsp_tool

#Load the .bsp map using bsp_tool
bsp = bsp_tool.load_bsp(r"c:\Program Files (x86)\Steam\steamapps\common\Momentum Mod Playtest\momentum\maps\surf_utopia.bsp")
#Define a 3D coordinate point (X,Y,Z) to test within map space
position = (-13952.00, 0.00, 12864.03)
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

#Initialize an empty list to store the final parsed 3D geometry
map_geometry = []
#Loop through every face defined in the BSP file, giving us the fface index and face data
for face_index, face in enumerate(bsp.FACES):
    #Get the surfedges that belongs to specific face
    #first_edge tells is where dace edge starts and num_edges tells us how many edges belong to that face
    surfedges = bsp.SURFEDGES[
       face.first_edge:
       face.first_edge + face.num_edges
    ]
    #Create an empty list to store the vertices for this fface
    vertices = []
   #Loop through each surfedge belonging to that current face
    for surfedge in surfedges:
        #A surfedge can be positive or negative so we do abs() to remove sign and use it as an index
        edge_index = abs(surfedge)
        #Get the actual edge using the dege index
        edge = bsp.EDGES[edge_index]
        #The sign determines the direction the edge should be traversed
        if surfedge >= 0:
           vertex_index = edge[0]
        else: 
           vertex_index = edge[1]
         #Use vertex index to retreive the actual 3D vertex from BSP file
        vertex = bsp.VERTICES[vertex_index]
        #Add the vertex to current faces vertex list
        vertices.append(vertex)
   #Only add faces that contain enough vertices to form a polygon
    if len(vertices) >= 3:
       #Store face index together with its list of vertices, giving us the final 3D geometry
       map_geometry.append((face_index, vertices))

#Create list to then find geometry from given face ID
geometry_by_face = {}
#Iterate through the geometry data and map the unique face index to its corresponding list of vertices
for face_index, vertices in map_geometry:
   geometry_by_face[face_index] = vertices


#Retrieve the face indices and corresponding vertex geometry got a specific BSP leaf
def get_leaf_geometry(leaf_index):
   #Look at specific leaf object using leaf_index
   leaf = bsp.LEAVES[leaf_index]
   #Extract only the face indices belonging to the speciffic leaff
   leaf_face_indices = bsp.LEAF_FACES[
      leaf.first_leaf_face:
      leaf.first_leaf_face + leaf.num_leaf_faces
   ]

   leaf_geometry = []
   #Iterate through each face index assigned to this leaf
   for face_index in leaf_face_indices:
      #Retreieve the vertex dataa associated with leaf index and then group the face index and vertices together
      vertices = geometry_by_face[face_index]
      leaf_geometry.append(
         (face_index,vertices)
      )
   return leaf_geometry

#Test variables
leaf_index = find_leaf(position,0)

leaf_geometry = get_leaf_geometry(leaf_index)

leaf = bsp.LEAVES[leaf_index]

player_pvs = bsp.VISIBILITY.pvs[leaf.cluster]
visible_clusters = []


#Get players visible cluster
#The PVS(Potential Visible Set) tells us which clusters can be seen from players current location
for cluster_index in range(len(bsp.VISIBILITY.pvs)):
   #Each cluster is repersented by one bit in the PVS data
   #Ddivide the cluster index by 8 to find which byte containts its bit
   byte_index = cluster_index // 8
   #Find which bit inside the byte repersents this cluster
   bit_index = cluster_index % 8 
   #Check whether the bit for this cluster is turned on, if it is then the cluster is visible to the player
   if player_pvs[byte_index] & (1 << bit_index):
      visible_clusters.append(cluster_index)

#Print the cluster that contains player current position
print("Player cluster: ", leaf.cluster)
#Print how many clusters are potentially visible
print("Visible clusters: ", len(visible_clusters))
#Print the first 20 visible clusters (test)
print("Frist visible cluster: ", visible_clusters[:20])

#Get the faces from those leaves that belong to the visible clusters
visible_leaves = []
#Go through every leaf in BSP
for visible_leaf_index, visible_leaf in enumerate (bsp.LEAVES):
   #A cluster value below 0 means this lead does not belong so we skip it
   if visible_leaf.cluster<0:
      continue
   #If the leaf's cluster is one of the visible clusters from player position then we add that leaf to our list
   if visible_leaf.cluster in visible_clusters:
      visible_leaves.append(visible_leaf_index)
#Print how many leaves we found in the visible clusters
print("Visible leaves: ", len(visible_leaves))
#Print the first 20 visible leaves(Test)
print("First vsible leaves: ", visible_leaves[:20])

#Get the faces from those visible leaves in clusters
#We use set so the same face is only storedd once
visible_faces = set()
#Go through every possible lead
for leaf_index in visible_leaves:
   #Get the actual leaf object from the BSP
   leaf = bsp.LEAVES[leaf_index]
   #Get the fface indices belonging to this leaf
   #first_leaf_face is where the leaf's face list starts and num_leaf_faces is how many belong to the leaf
   #So first_leaf_face = 100 and num_leaf_faces=5 then we get LEAF_FACES[100:105]
   leaf_face_indices = bsp.LEAF_FACES[
      leaf.first_leaf_face:
      leaf.first_leaf_face + leaf.num_leaf_faces
   ]
   #Add each face to the set of visible faces
   for face_index in leaf_face_indices:
      visible_faces.add(face_index)
#Print total number of unique visible faces
print("Unique visible faces: ", len(visible_faces))
#Print the first 20 visible faces (Test)
print("First vsible face: ", list(visible_faces)[:20])

#Get geometry belonging to each visible face
pvs_geometry = []
#Go through every unique visible ace
for face_index in visible_faces:
   #Get the vertices that make up this face
   vertices = geometry_by_face[face_index]
   #Store both fface index and its geometry
   pvs_geometry.append(
      (face_index, vertices)
   )
#Print how many geometry faces collected
print("PVS geometry faces: ", len(pvs_geometry))
#Print the first PVS geometry face (Test)
print("First PVS geometry face: ", list(pvs_geometry)[0])
