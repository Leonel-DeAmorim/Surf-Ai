import math
import bsp_parser
import open3d as o3d
import numpy as np
import json
import urllib.request
import time

#Define function for receiving game data
def get_game_data():
   #Local server provides the latest player position and viewing angles
   url = "http://127.0.0.1:8080/latest"

   try:
      #Request the latest game data and stop waiting if server takes too long
      with urllib.request.urlopen(url, timeout= 1) as response:
         data = json.loads(response.read().decode("utf-8"))
      return data

   except Exception as error:
      #Return None if the server cannot be reached or the data cannot be read
      print("Could not read game data:", error)
      return None

#Get player's data
game_data = get_game_data()

#Stop the program if no initial position is avaliable
if game_data is None or game_data.get("position") is None:
   raise RuntimeError(
      "No player data received. Ensure Momentum Mod and server is running"
      )

#Store player's position as array containing the X, Y, Z coordinates
player_data = game_data ["position"]

player_position = np.array([
   player_data["x"],
   player_data["y"],
   player_data["z"]
], dtype = float)



#Convert the gometry  into triangle mesh for Open3D
all_vertices = []
all_triangles = []
triangle_face_ids = []

#Read every face of the map from BSP geometry
for face_id, face_vertices in bsp_parser.all_map_geometry:

   face_coords = []

   #Convert each vertex into a list of three coordinates
   for v in face_vertices:
       if hasattr(v, "x"):
         #Some verticies store coordinates as X, Y, Z attributes
         coords = [
             float(v.x),
             float(v.y),
            float(v.z)
         ]
       else:
        #Other verticies may already be stored as coordinate arrays
        coords = np.asarray(
           v, dtype = float
       ).reshape(3).tolist()

       face_coords.append(coords)
   #A traingle requires at least 3 vertices
   if len(face_coords) <3:
      continue

   #Record the starting index of the face verticies
   base_index = len(all_vertices)
   all_vertices.extend(face_coords)

   #Split the face into triangles by connecting its first vertex to each consecutive pair of remaining vertices
   for i in range (1,len(face_coords) - 1):

      all_triangles.append([
         base_index,
         base_index + i,
         base_index + i + 1
      ])
      #Keep track of which original map face each trianlge come from
      triangle_face_ids.append(face_id)

#Convert the vertex and triangle lists into numpy arrays for Oen3D
all_vertices = np.asarray(all_vertices, dtype=np.float32)
all_triangles = np.asarray(all_triangles, dtype=np.int32)

#Create a trianlge mesh that Open3D can use for collision detection
mesh =o3d.t.geometry.TriangleMesh()
mesh.vertex["positions"] = o3d.core.Tensor(all_vertices)
mesh.triangle["indices"] = o3d.core.Tensor(all_triangles)

#Build a scene that can test whether rays hit the map and how far away
scene = o3d.t.geometry.RaycastingScene()
scene.add_triangles(mesh)

#Hieght of the LIDAR above player's position
eye_height = 64
#Maximum distance a ray can travel through the map
max_range = 15000.0
#Horizontal and vertical fov covered by LIDAR
horizontal_fov = 90.0
vertical_fov = 60.0
#Number of horizontal and vertical rays to be sent
horizontal_rays = 12
vertical_rays = 6
#Total number of rays cast during each update
num_rays = horizontal_rays * vertical_rays
#Target update rate, aim for 60 updates per second
target_fps = 60
target_frame_time = 1.0 / target_fps

#Create the visible version of the map
visual_mesh = o3d.geometry.TriangleMesh()
visual_mesh.vertices = o3d.utility.Vector3dVector(
   all_vertices.astype(np.float64)
)
visual_mesh.triangles = o3d.utility.Vector3iVector(
   all_triangles
)

#Calculate normal direction of every triangle
visual_mesh.compute_triangle_normals()
#Get the triangle normals as a numpy array
triangle_normals = np.asarray(visual_mesh.triangle_normals)

#Create one colour for every vertex
vertex_colours = np.zeros(
   (len(all_vertices), 3),
   dtype= np.float64
)

#define colour using RGB values from 0 to 1
floor_colour = [0.65, 0.65, 0.65] #Green
wall_colour = [0.65, 0.65, 0.65] #Blue
ramp_colour = [1.00, 0.55, 0.15] #Orange

#Colour each triangle according to its surface normal
for triangle, normal in zip(all_triangles, triangle_normals):

   vertical_alignment = abs(normal[2])

   if vertical_alignment > 0.85:
      colour = floor_colour

   elif vertical_alignment < 0.25:
      colour = wall_colour

   else:
      colour = ramp_colour

   vertex_colours[triangle]= colour

visual_mesh.vertex_colors = o3d.utility.Vector3dVector(
   vertex_colours
)

#Red points show where LIDAR rays hit map
point_cloud = o3d.geometry.PointCloud()
point_cloud.paint_uniform_color([1.0, 0.0, 0.0])

#Blue points mark players current LIDAR origin
origin_cloud = o3d.geometry.PointCloud()
origin_cloud.paint_uniform_color([0.0, 0.0, 1.0])

#Yellow lines show the direction and lengths of the LIDAR ray from origin
ray_lines = o3d.geometry.LineSet()
ray_lines.paint_uniform_color([1.0, 0.8, 0.0])

#Place LIDAR origin at lpayer height
origin = player_position +np.array([0.0, 0.0, eye_height])

#Save the previous position so coordinate frame can follow player
previous_origin = origin.copy()

#Create a set of coloured axes to show LIDAR orientation
coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(
   size = 64.0,
   origin = origin
)

#Create the window which the map and LIDAR will be displayed
vis = o3d.visualization.Visualizer()
vis.create_window(
   window_name= "Live Momentum Mod LIDAR",
   width= 1200,
   height= 800
)
#Configuire how the map is drawn
render_option = vis.get_render_option()
render_option.mesh_show_wireframe =True
render_option.mesh_show_back_face = True

#Add the mapp, hit points, player origin, rays and acxes to the window
for geometry in [
   visual_mesh,
   point_cloud,
   origin_cloud,
   ray_lines,
   coordinate_frame
]:
   vis.add_geometry(geometry)

#These values describe the demensions of the window
width = 1200
height = 800

#Convert feilds of view from degrees to radians for calculation
horizontal_fov_rad = math.radians(horizontal_fov)
vertical_fov_rad = math.radians(vertical_fov)

#Calculate the camers focal length from the feild of view
fx = width / (2 * math.tan(horizontal_fov_rad / 2))
fy = height / (2 * math.tan(vertical_fov_rad /2))

#Define the camers internal setting including resolution and focal length
intrinsic = o3d.camera.PinholeCameraIntrinsic(
   width,
   height,
   fx,
   fy,
   width / 2,
   height / 2
)

#Define the worlds upward direction which is used to calcualte the cameras orientation
world_up = np.array([0.0, 0.0, 1.0])

#Kepp updating the visualization until the user closes the window
print("Close window to stop")

while vis.poll_events():
   #Record start time so the loop can aim for target frame rate
   frame_start = time.perf_counter()
   #Reques the latest player position and viewing angles
   game_data = get_game_data()
   #Only update the lidar when both the position and view angles are avaliable
   if (
      game_data is not None 
      and game_data.get("position") is not None 
      and game_data.get("angles") is not None
      ):
      #Read the players current postion
      player_data = game_data["position"]
      player_position = np.array([
         player_data["x"],
         player_data["y"],
         player_data["z"]
      ], dtype=float)
      #Move the LIDAR origin to the players current position and height
      origin = player_position + np.array([
         0.0, 0.0, eye_height
      ])
      #Read the players pitch and yaw
      angle_data = game_data["angles"]

      pitch = math.radians(angle_data["x"])
      yaw = math.radians(angle_data["y"])
      #Calculate the direction the player is facing using pitch and yaw, the resulting vector describes the forward direction in 3D space
      forward = np.array([
         math.cos(pitch) * math.cos(yaw),
         math.cos(pitch) * math.sin(yaw),
         -math.sin(pitch)
      ], dtype= float)
      #This list will hold the origin and direction of every LIDAR ray
      rays_data = []

      #Generate rays evenly spaced across vertical field of view
      for vertical_index in range(vertical_rays):
         vertical_angle = (
            -vertical_fov / 2 
            + vertical_index * (
               vertical_fov / (vertical_rays - 1)
            )
         )
         #Generate rays evenly spaced across horizontal field of view
         for horizontal_index in range(horizontal_rays):
            horizontal_angle = (
               -horizontal_fov / 2 
               + horizontal_index * ( 
                  horizontal_fov / (horizontal_rays -1)
               )
            ) 
            #Add each rays offset to the players current viewing angle
            ray_pitch = pitch +math.radians(vertical_angle)
            ray_yaw = yaw +math.radians(horizontal_angle)

            #Convert the rays angles into 3D direction vector
            direction = (
               math.cos(ray_pitch) * math.cos(ray_yaw),
               math.cos(ray_pitch) *  math.sin(ray_yaw),
               -math.sin(ray_pitch)
            )
            #Store the ray ass six values that being origin X, Y, Z followed by direction X, Y, Z
            rays_data.append([
               origin[0],
               origin[1],
               origin[2],
               direction[0],
               direction[1],
               direction[2]
            ])
      #Convert the rays into a format open3D can process
      rays = o3d.core.Tensor(
            rays_data,
            dtype= o3d.core.Dtype.Float32
      )
      #Cast all rays into the map and open3D returns the distance to each rays first intersection
      ans = scene.cast_rays(rays)

      #Store the locations where ray hit the map and the ednpoints
      hit_points = []
      ray_endpoint = []

      #Check the result of each ray
      for i in range(num_rays):
         #Get distance from rays origin to its first hit
         t  = ans["t_hit"][i].item()
         #Retrieve rays direction vector
         ray_direction = rays_data[i][3:6]
         #Finite hit distance means the ray hit the map and we only display the hit if its within maximum LIDAR range
         if math.isfinite(t) and t <= max_range:
            #Calculate the 3D coordinates of the hit location
            hit = (
                  origin[0] +ray_direction[0] *t,
                  origin[1] +ray_direction[1] *t,
                  origin[2] +ray_direction[2] *t,
               )
            #Save hit for the red point cloud and ray endpoint
            hit_points.append(hit)
            ray_endpoint.append(hit)

         else:
               #If there us no hit within range extend ray into max_range
               endpoint = (
                  origin[0] +ray_direction[0] *max_range,
                  origin[1] +ray_direction[1] *max_range,
                  origin[2] +ray_direction[2] *max_range,
               )
               ray_endpoint.append(endpoint)
      #Update the red point cloud with latest map hit location
      point_cloud.points = o3d.utility.Vector3dVector(
            np.asarray(hit_points, dtype= np.float64).reshape(-1,3)
         )
      #Update the blue point showing the LIDARs current origin
      origin_cloud.points = o3d.utility.Vector3dVector(
            np.asarray([origin], dtype=np.float64)
         )
      #Build line geometry
      line_points = [origin] + ray_endpoint

      ray_lines.points = o3d.utility.Vector3dVector(
            np.asarray(line_points, dtype=np.float64)
         )
      #Connect the origin to every ray endpoint with line
      ray_lines.lines = o3d.utility.Vector2iVector(
            np.asarray(
               [[0, i +1 ] for i in range (num_rays)],
               dtype= np.int32
            )
         )
      #Move the coordinate exes by the same amount the player moved
      coordinate_frame.translate(
            origin - previous_origin,
            relative = True
         )
      #Save the current position to use during next update
      previous_origin = origin.copy()
      #Normalize the forward vector so its length is one
      forward_vec = forward.copy()
      forward_vec /= np.linalg.norm(forward_vec)
      #Calculate the camers right direction using forward direction and world upward direction
      right = np.cross(forward_vec, world_up)
      right_length = np.linalg.norm(right)

      #Avoid calculating an invalid camera orientation if player is looking almost direclty up or down
      if right_length > 1e-8:
            #Normalize right direction
            right /= right_length
            #Calculate the cmeras downward direction
            camera_down = np.cross(forward_vec, right)
            camera_down /= np.linalg.norm(camera_down)
            #Combine the three directions into a camera rotation matrix
            rotation = np.stack ([
               right, 
               camera_down,
               forward_vec
            ])

            #Create a 4x4 transormation matrix for the camera
            extrinsic = np.eye(4)
            #Store camers rotation
            extrinsic[:3, :3] = rotation
            #Set camera translation based on player position
            extrinsic[:3, 3] = -rotation @ origin

            #Create camera parameters using intrinsics and calculate pose
            camera = o3d.camera.PinholeCameraParameters()
            camera.intrinsic = intrinsic
            camera.extrinsic = extrinsic
            #Apply the camera settings so the view follows the player
            vis.get_view_control().convert_from_pinhole_camera_parameters(
               camera,
               allow_arbitrary= True
            )
      #Tell open3D which moving objects have changed and need updating
      for geometry in [
            point_cloud,
            origin_cloud,
            ray_lines,
            coordinate_frame
         ]:
            vis.update_geometry(geometry)
   #Draw the latest changes 
   vis.update_renderer()
   #Calculate how much time this update took and workout how much time remains in target drame duration
   elapsed = time.perf_counter() - frame_start
   remaining = target_frame_time - elapsed
   #Wait for the remaining time when an update finishes early
   if remaining > 0 :
         time.sleep(remaining)
#Close window and end visualization
vis.destroy_window()
print("Lidar STOPPED")
