import math
import bsp_parser
import open3d as o3d
import numpy as np
import json
import urllib.request
import time
#Define function for receiving game data
def get_game_data():
   url = "http://127.0.0.1:8080/latest"

   try:
      with urllib.request.urlopen(url, timeout= 1) as response:
         data = json.loads(response.read().decode("utf-8"))
      return data

   except Exception as error:
      print("Could not read game data:", error)
      return None


game_data = get_game_data()

if game_data is None or game_data.get("position") is None:
   raise RuntimeError(
      "No player data received. Ensure Momentum Mod and server is running"
      )

player_data = game_data ["position"]

player_position = np.array([
   player_data["x"],
   player_data["y"],
   player_data["z"]
], dtype = float)

#Define view angle taken from Momentum Mod which is given as degrees
angle_data = game_data["angles"]

view_angle = (
   angle_data["x"],
   angle_data["y"],
   angle_data["z"]
)
#We will create forward vector to know where player is looking and this will be the basis of our lidar

#Convert the view_angle from degrees to radians for the speciic pitch, yaw and roll 
pitch = math.radians(view_angle[0])
yaw = math.radians(view_angle[1])
roll = math.radians(view_angle[2])

#Create our forward direction vector
forward = (
    math.cos(pitch) * math.cos(yaw),
    math.cos(pitch) * math.sin(yaw),
    -math.sin(pitch)
)


print("//////////////////////////////////////////////")

#Convert the gometry  into triangle mesh ffor Open3D
pvs_vertices = []
pvs_triangles = []
triangle_face_ids = []

for face_id, face_vertices in bsp_parser.all_map_geometry:

   face_coords = [
      [float(v.x),float(v.y),float(v.z)]
      for v in face_vertices
   ]

   if len(face_coords) <3:
      continue

   base_index = len(pvs_vertices)
   pvs_vertices.extend(face_coords)

   for i in range (1,len(face_coords) - 1):

      pvs_triangles.append([
         base_index,
         base_index + i,
         base_index + i + 1
      ])

      triangle_face_ids.append(face_id)

pvs_vertices = np.asanyarray(pvs_vertices, dtype=np.float32)
pvs_triangles = np.asanyarray(pvs_triangles, dtype=np.int32)

print("PVS faces:", len(bsp_parser.pvs_geometry))
print("Mesh vertives:", len(pvs_vertices))
print("Mesh triangles:", len(pvs_triangles))

mesh =o3d.t.geometry.TriangleMesh()
mesh.vertex["positions"] = o3d.core.Tensor(pvs_vertices)
mesh.triangle["indices"] = o3d.core.Tensor(pvs_triangles)

scene = o3d.t.geometry.RaycastingScene()
scene.add_triangles(mesh)

#Create lidar ray and give it direction to test if it hits our test triangle
eye_height = 64
max_range = 15000.0
horizontal_fov = 90.0
vertical_fov = 60.0
horizontal_rays = 12
vertical_rays = 6
num_rays = horizontal_rays * vertical_rays
target_fps = 60
target_frame_time = 1.0 / target_fps

visual_mesh = o3d.geometry.TriangleMesh()
visual_mesh.vertices = o3d.utility.Vector3dVector(
   pvs_vertices.astype(np.float64)
)
visual_mesh.triangles = o3d.utility.Vector3iVector(
   pvs_triangles
)
visual_mesh.compute_triangle_normals()
visual_mesh.paint_uniform_color([0.65, 0.65, 0.65])

point_cloud = o3d.geometry.PointCloud()
point_cloud.paint_uniform_color([1.0, 0.0, 0.0])

origin_cloud = o3d.geometry.PointCloud()
origin_cloud.paint_uniform_color([0.0, 0.0, 1.0])

ray_lines = o3d.geometry.LineSet()
ray_lines.paint_uniform_color([1.0, 0.8, 0.0])

origin = player_position +np.array([0.0, 0.0, eye_height])
previous_origin = origin.copy()

coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(
   size = 64.0,
   origin = origin
)

vis = o3d.visualization.Visualizer()
vis.create_window(
   window_name= "Live Momentum Mod LIDAR",
   width= 1200,
   height= 800
)
render_option = vis.get_render_option()
render_option.mesh_show_wireframe =True
render_option.mesh_show_back_face = True

for geometry in [
   visual_mesh,
   point_cloud,
   origin_cloud,
   ray_lines,
   coordinate_frame
]:
   vis.add_geometry(geometry)

width = 1200
height = 800

horizontal_fov_rad = math.radians(horizontal_fov)
vertical_fov_rad = math.radians(vertical_fov)

fx = width / (2 * math.tan(horizontal_fov_rad / 2))
fy = height / (2 * math.tan(vertical_fov_rad /2))

intrinsic = o3d.camera.PinholeCameraIntrinsic(
   width,
   height,
   fx,
   fy,
   width / 2,
   height / 2
)

world_up = np.array([0.0, 0.0, 1.0])

frame_count = 0
report_start = time.perf_counter()
last_scan_ms = 0.0

print("Starting live LIDAR at 60fps")
print("Close window to stop")

while vis.poll_events():

   frame_start = time.perf_counter()

   game_data = get_game_data()

   if (
      game_data is not None 
      and game_data.get("position") is not None 
      and game_data.get("angles") is not None
      ):
      player_data = game_data["position"]
      player_position = np.array([
         player_data["x"],
         player_data["y"],
         player_data["z"]
      ], dtype=float)

      origin = player_position + np.array([
         0.0, 0.0, eye_height
      ])

      angle_data = game_data["angles"]

      pitch = math.radians(angle_data["x"])
      yaw = math.radians(angle_data["y"])
      roll = math.radians(angle_data["z"])

      forward = np.array([
         math.cos(pitch) * math.cos(yaw),
         math.cos(pitch) * math.sin(yaw),
         -math.sin(pitch)
      ], dtype= float)

      rays_data = []

      for vertical_index in range(vertical_rays):
         vertical_angle = (
            -vertical_fov / 2 
            + vertical_index * (
               vertical_fov / (vertical_rays - 1)
            )
         )
         for horizontal_index in range(horizontal_rays):
            horizontal_angle = (
               -horizontal_fov / 2 
               + horizontal_index * ( 
                  horizontal_fov / (horizontal_rays -1)
               )
            ) 
            ray_pitch = pitch +math.radians(vertical_angle)
            ray_yaw = yaw +math.radians(horizontal_angle)

            direction = (
               math.cos(ray_pitch) * math.cos(ray_yaw),
               math.cos(ray_pitch) *  math.sin(ray_yaw),
               -math.sin(ray_pitch)
            )

            rays_data.append([
               origin[0],
               origin[1],
               origin[2],
               direction[0],
               direction[1],
               direction[2]
            ])

      rays = o3d.core.Tensor(
            rays_data,
            dtype= o3d.core.Dtype.Float32
      )

      ans = scene.cast_rays(rays)

      hit_points = []
      ray_endpoint = []

      for i in range(num_rays):
         t  = ans["t_hit"][i].item()
         ray_direction = rays_data[i][3:6]

         if math.isfinite(t) and t <= max_range:
            hit = (
                  origin[0] +ray_direction[0] *t,
                  origin[1] +ray_direction[1] *t,
                  origin[2] +ray_direction[2] *t,
               )

            hit_points.append(hit)
            ray_endpoint.append(hit)

         else:
               endpoint = (
                  origin[0] +ray_direction[0] *max_range,
                  origin[1] +ray_direction[1] *max_range,
                  origin[2] +ray_direction[2] *max_range,
               )
               ray_endpoint.append(endpoint)

      point_cloud.points = o3d.utility.Vector3dVector(
            np.asarray(hit_points, dtype= np.float64).reshape(-1,3)
         )

      origin_cloud.points = o3d.utility.Vector3dVector(
            np.asarray([origin], dtype=np.float64)
         )

      line_points = [origin] + ray_endpoint

      ray_lines.points = o3d.utility.Vector3dVector(
            np.asarray(line_points, dtype=np.float64)
         )

      ray_lines.lines = o3d.utility.Vector2iVector(
            np.asarray(
               [[0, i +1 ] for i in range (num_rays)],
               dtype= np.int32
            )
         )

      coordinate_frame.translate(
            origin - previous_origin,
            relative = True
         )
      previous_origin = origin.copy()

      forward_vec = forward.copy()
      forward_vec /= np.linalg.norm(forward_vec)

      right = np.cross(forward_vec, world_up)
      right_length = np.linalg.norm(right)

      if right_length > 1e-8:
            right /= right_length

            camera_down = np.cross(forward_vec, right)
            camera_down /= np.linalg.norm(camera_down)

            rotation = np.stack ([
               right, 
               camera_down,
               forward_vec
            ])

            extrinsic = np.eye(4)
            extrinsic[:3, :3] = rotation
            extrinsic[:3, 3] = -rotation @ origin

            camera = o3d.camera.PinholeCameraParameters()
            camera.intrinsic = intrinsic
            camera.extrinsic = extrinsic

            vis.get_view_control().convert_from_pinhole_camera_parameters(
               camera,
               allow_arbitrary= True
            )
      for geometry in [
            point_cloud,
            origin_cloud,
            ray_lines,
            coordinate_frame
         ]:
            vis.update_geometry(geometry)

      last_scan_ms = (
            time.perf_counter()-frame_start
         ) *1000.0
      frame_count += 1

   vis.update_renderer()

   elapsed = time.perf_counter() - frame_start
   remaining = target_frame_time - elapsed

   if remaining > 0 :
         time.sleep(remaining)

   now = time.perf_counter()
   report_elapsed = now -report_start

   if report_elapsed >= 1.0:
         actual_fps =frame_count / report_elapsed

         print(
          f"Lidar rate : {actual_fps:.1f} scans/s | "
          f"Last scan: {last_scan_ms:.2f} ms"
         )
         frame_count = 0
         report_start= now

vis.destroy_window()
print("Lidar STOPPED")