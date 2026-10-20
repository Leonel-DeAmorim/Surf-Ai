import bsp_tool
import re
import numpy as np

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
world_model = bsp.MODELS[0]
first_face = world_model.first_face
last_face = first_face + world_model.num_faces

#Loop through every face defined in the BSP file, giving us the fface index and face data
for face_index in range(first_face, last_face):
    face = bsp.FACES[face_index]

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

#Exclude submodels to only keep waht we want
all_map_geometry = list(map_geometry)

#Convert the BSP entity lump into readable text
#Entities contain information about map objects including thier class name and model references which we will use to filter geometry
raw_entities = bytes(bsp.ENTITIES)
entity_text = raw_entities.decode("utf-8", errors="replace")

#Store entities that reference a BSP submmodel, the dictionary key is the submodel ID and the value containts model entity properties 
entities_by_model = {}

#Split the entity text into individual entity blocks
entity_blocks = re.findall(r"\{([^{}]*)\}", entity_text)

#Read each entitys key value pairs and save entities reference a model using a reference such as "*1" or "*25" 
for block in entity_blocks:
    pairs = re.findall(r'"([^"]*)"\s*"([^"]*)"', block)
    entity = dict(pairs)

    model_ref = entity.get("model", "")
    if model_ref.startswith("*"):
        try:
            model_id = int(model_ref[1:])
            entities_by_model[model_id] = entity
        except ValueError:
            #Skip model references that cannot be converted to a integer 
            continue


def extract_model_faces(model_id, model_origin):
   #Retrieve BSP model and convert its origin to a numpy array so it can be added to vertex coordinates
   model = bsp.MODELS[model_id]
   origin_offset = np.asarray(model_origin, dtype=float)

   extracted = []

   #Find the range of faces belonging to the submodel
   first_face = model.first_face
   last_face = first_face + model.num_faces

   #Process each face belonging to the submodel
   for face_index in range (first_face, last_face):
      face = bsp.FACES[face_index]

      #Get the edge reference that defin the outline of the face
      surfedge = bsp.SURFEDGES[
         face.first_edge:
         face.first_edge + face.num_edges
      ]

      vertices = []

      #Resolve each surfedge into a vertex index, the sign of the surfedge dtermines which endpoint of the reference to use
      for surfedge in surfedge:
         edge = bsp.EDGES[abs(surfedge)]

         if surfedge >= 0 :
            vertex_index = edge[0]
         else:
            vertex_index = edge[1]

         #Retrieve the vertex coordinates and apply the model origin
         vertex = np.asarray(
            bsp.VERTICES[vertex_index],
            dtype=float
         )

         vertices.append(vertex + origin_offset)

      #Polygon needs at least 3 vertices to form a face
      if len(vertices) >=3:
         #Store the model ID and face ID so each face can be identified later
         extracted.append(
            ((model_id, face_index), vertices)
         )
   return extracted

#Track which submodels are excluded and which are added to map geometry
skipped_models = []
included_models = []

#Exlude teleport triggers and timer zones volumes from the render geometry as it was being rendered when it shouldnt have
#We kept other classes such as func_illusionary as they contain geometry for a curved ramp needed in the utopia test file
#Other maps may need looking into what to exclude but excluding trigger and zones for now seem to work 
excluded_classes = {
    "trigger_teleport",
    "zone_timer_start",
    "zone_timer_checkpoint",
    "zone_timer_end",
}

#Start at model 1 becouse model 0 repersents the world geometry which is already extracted
for model_id in range(1, len(bsp.MODELS)):
    #Find the entity associated with this submodel
    entity = entities_by_model.get(model_id)

    if entity is None:
        print(f"Model {model_id}: no matching entity")
        classname = "unknown"
    else:
        #Normalize the class name so comparisons are case insensitive
        classname = entity.get("classname", "unknown").strip().lower()

   #Skip models whos entits class are in the exclusion list
    if classname in excluded_classes:
        skipped_models.append((model_id, classname))
        continue

   #Read the entity origin using zero offset when its missing or invalid
    origin_text = entity.get("origin", "0 0 0") if entity else "0 0 0"

    try:
        model_origin = [float(value) for value in origin_text.split()]
        if len(model_origin) != 3:
            model_origin = [0.0, 0.0, 0.0]
    except ValueError:
        model_origin = [0.0, 0.0, 0.0]

   #Extract the model's polygons and append them to the full map geometry
    model_geometry = extract_model_faces(model_id, model_origin)
    all_map_geometry.extend(model_geometry)
    #Record the cindluded model for option debugging
    included_models.append((model_id, classname))


#Create lookup table that maps each world face ID to it vertices
#This lets use quickly find geometry associated with face when building PVS geometry
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

#Find which BSP leaf contains the test position
#Leaf identifies the area of the map where position is located
leaf_index = find_leaf(position,0)

#Get the leaf so we can determine its visibility cluster
leaf = bsp.LEAVES[leaf_index]

#Get PVS bit data for the cluster containing the test position
#Each bit indicated whether another cluster is potentially visible
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


#Get the faces from those leaves that belong to the visible clusters
#THis finds all BSP leaves that belong to PVS and leaves with negative cluster value are not associated with a regular visibility cluster so we skip them
visible_leaves = []
#Go through every leaf in BSP
for visible_leaf_index, visible_leaf in enumerate (bsp.LEAVES):
   #A cluster value below 0 means this lead does not belong so we skip it
   if visible_leaf.cluster<0:
      continue
   #If the leaf's cluster is one of the visible clusters from player position then we add that leaf to our list
   if visible_leaf.cluster in visible_clusters:
      visible_leaves.append(visible_leaf_index)


#Get the faces from those visible leaves in clusters
#We use set so the same face is only storedd once and avoid duplicates
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


#Build seperate list containing only world faces found through PVS calculation
#This is kept seperate from all_map_geometry so it is its own seperate set
pvs_geometry = []
#Go through every unique visible ace
for face_index in visible_faces:
   #Get the vertices that make up this face
   if face_index not in geometry_by_face:
      continue
   vertices = geometry_by_face[face_index]
   #Store both fface index and its geometry
   pvs_geometry.append(
      (face_index, vertices)
   )
