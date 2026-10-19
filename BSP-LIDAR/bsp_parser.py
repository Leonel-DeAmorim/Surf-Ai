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


raw_entities = bytes(bsp.ENTITIES)
entity_text = raw_entities.decode("utf-8", errors="replace")

print("Entity lump bytes:", len(raw_entities))
print("Entity text preview:", repr(entity_text[:300]))

entities_by_model = {}

entity_blocks = re.findall(r"\{([^{}]*)\}", entity_text)
print("Entity blocks found:", len(entity_blocks))

for block in entity_blocks:
    pairs = re.findall(r'"([^"]*)"\s*"([^"]*)"', block)
    entity = dict(pairs)

    model_ref = entity.get("model", "")
    if model_ref.startswith("*"):
        try:
            model_id = int(model_ref[1:])
            entities_by_model[model_id] = entity
        except ValueError:
            continue

print("Entities with model references:", len(entities_by_model))
print("Sample model entities:", list(entities_by_model.items())[:5])


print("Entities with model references:", len(entities_by_model))
print(
    "Sample model entities:",
    list(entities_by_model.items())[:5]
)


def extract_model_faces(model_id, model_origin):
   model = bsp.MODELS[model_id]
   origin_offset = np.asarray(model_origin, dtype=float)

   extracted = []

   first_face = model.first_face
   last_face = first_face + model.num_faces

   for face_index in range (first_face, last_face):
      face = bsp.FACES[face_index]

      surfedge = bsp.SURFEDGES[
         face.first_edge:
         face.first_edge + face.num_edges
      ]

      vertices = []

      for surfedge in surfedge:
         edge = bsp.EDGES[abs(surfedge)]

         if surfedge >= 0 :
            vertex_index = edge[0]
         else:
            vertex_index = edge[1]

         vertex = np.asarray(
            bsp.VERTICES[vertex_index],
            dtype=float
         )

         vertices.append(vertex + origin_offset)

      if len(vertices) >=3:
         extracted.append(
            ((model_id, face_index), vertices)
         )
   return extracted

skipped_models = []
included_models = []

excluded_classes = {
    "trigger_teleport",
    "zone_timer_start",
    "zone_timer_checkpoint",
    "zone_timer_end",
}

for model_id in range(1, len(bsp.MODELS)):
    entity = entities_by_model.get(model_id)

    if entity is None:
        print(f"Model {model_id}: no matching entity")
        classname = "unknown"
    else:
        classname = entity.get("classname", "unknown").strip().lower()

    should_exclude = classname in excluded_classes

    if should_exclude:
        skipped_models.append((model_id, classname))
        continue

    origin_text = entity.get("origin", "0 0 0") if entity else "0 0 0"

    try:
        model_origin = [float(value) for value in origin_text.split()]
        if len(model_origin) != 3:
            model_origin = [0.0, 0.0, 0.0]
    except ValueError:
        model_origin = [0.0, 0.0, 0.0]

    model_geometry = extract_model_faces(model_id, model_origin)
    all_map_geometry.extend(model_geometry)
    included_models.append((model_id, classname))

print("Included submodels:", len(included_models))
print("Excluded submodels:", len(skipped_models))
print("Excluded models and classes:", skipped_models)
print("Included model classes:", sorted(set(c for _, c in included_models)))
print("Included model IDs:", included_models)
print("Total geometry faces:", len(all_map_geometry))

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
   if face_index not in geometry_by_face:
      continue
   vertices = geometry_by_face[face_index]
   #Store both fface index and its geometry
   pvs_geometry.append(
      (face_index, vertices)
   )
#Print how many geometry faces collected
print("PVS geometry faces: ", len(pvs_geometry))
#Print the first PVS geometry face (Test)
print("First PVS geometry face: ", list(pvs_geometry)[0])

#CHECK attributes to filter potentially

from collections import Counter

print("\n=== ENTITY CLASSNAMES ===")

entities = bsp.ENTITIES
class_counts = Counter(
    entity.get("classname", "<no classname>")
    for entity in entities
)

for classname, count in class_counts.most_common():
    print(f"{classname}: {count}")

print("\n=== TRIGGER / CHECKPOINT ENTITIES ===")

for index, entity in enumerate(entities):
    classname = entity.get("classname", "").lower()
    if any(word in classname for word in (
        "trigger", "checkpoint", "start", "zone"
    )):
        print(index, dict(entity))

print("\n=== BRUSH ATTRIBUTES ===")

for lump_name in ("BRUSHES", "BRUSH_SIDES",
                  "FACE_BRUSHES", "FACE_BRUSH_LIST"):
    lump = getattr(bsp, lump_name, None)
    print(f"\n{lump_name}: {len(lump) if lump is not None else 'missing'}")
    if lump is not None and len(lump) > 0:
        print("First entry:", lump[0])

print("\n=== FACE SURFACE FLAG COUNTS ===")

flag_counts = Counter()

for face in bsp.FACES:
    if face.texture_info < len(bsp.TEXTURE_INFO):
        flags = bsp.TEXTURE_INFO[face.texture_info].flags
        flag_counts[str(flags)] += 1

for flags, count in flag_counts.most_common(30):
    print(f"{flags}: {count}")

print("\n=== TEXTURE STRING DATA ===")

for lump_name in ("TEXTURE_DATA_STRING_TABLE",
                  "TEXTURE_DATA_STRING_DATA"):
    lump = getattr(bsp, lump_name, None)
    print(f"\n{lump_name}: {len(lump) if lump is not None else 'missing'}")
    if lump is not None:
        print("First entries:", list(lump[:10]))
