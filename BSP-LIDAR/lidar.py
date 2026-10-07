import math
import bsp_parser
import open3d as o3d
import numpy as np

#Define view angle taken from Momentum Mod which is given as degrees
view_angle = (0.07, 0.04, 0.00)
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
#Print the result
print("View angles", view_angle)
print("forward vector", forward)

print("PVS geometry:", len(bsp_parser.pvs_geometry))
print("Player position:", bsp_parser.position)
print("//////////////////////////////////////////////")


#Test code to understand open3d library
#Create a test trinagle to then hit with lidar 
#Create verticies
verticies = np.array([
    [0,0,0],
    [10,0,0],
    [0,10,0]
], dtype=np.float32)
#Pair verticies into traingle
trinagles = np.array([
    [0,1,2]
],dtype=np.int32)
#After defining the above we now store the repersentation in Open3D TriangleMesh so Open3D can work with it
mesh = o3d.t.geometry.TriangleMesh()
mesh.vertex["positions"] = o3d.core.Tensor(verticies)
mesh.triangle["indices"] = o3d.core.Tensor(trinagles)
print(mesh)
#Put triangle geometry into raycasting scene
scene = o3d.t.geometry.RaycastingScene()
scene.add_triangles(mesh)

#Create lidar ray and give it direction to test if it hits our test triangle

origin = (4,3,5)
direction = (0.6,0.48,-0.64)
max_range = 10.0
fov = 60.0
num_rays = 5
rays_data = []

for i in range(num_rays):
    angle = -fov / 2 + i * (fov / (num_rays -1))

    angle_radians = math.radians(angle)

    direction = (
        math.sin(angle_radians),
        0.0,
        -math.cos(angle_radians)
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
    dtype=o3d.core.Dtype.Float32
)

ans = scene.cast_rays(rays)
print(ans)
hit_points = []

for i in range(num_rays):
    t= ans["t_hit"][i].item()

    if math.isfinite(t) and t <= max_range:
        hit_x = origin[0] +rays_data[i][3]*t
        hit_y = origin[1] +rays_data[i][4]*t
        hit_z = origin[2] +rays_data[i][5]*t
        hit = (hit_x,hit_y,hit_z)
        hit_points.append(hit)
        print("Ray",i,"Hit Point:",hit,"Distance:",t)

    else:
     print("Ray",i,"No hit" )


#Create a open3D visual 
#Create empty visual mesh to populate
visual_mesh = o3d.geometry.TriangleMesh()

visual_mesh.vertices = o3d.utility.Vector3dVector(
   verticies.astype(np.float64)
)
visual_mesh.triangles = o3d.utility.Vector3iVector(
   trinagles.astype(np.int32)
)

visual_mesh.compute_vertex_normals()

point_cloud = o3d.geometry.PointCloud()

point_cloud.points = o3d.utility.Vector3dVector(
   np.array(hit_points,dtype=np.float64)
)
origin_cloud = o3d.geometry.PointCloud()
origin_cloud.points = o3d.utility.Vector3dVector(
   np.array([origin],dtype=np.float64)
)

line_points = [origin] +hit_points

line_indices = []

for i in range(len(hit_points)):
   line_indices.append([0, i+1])

ray_lines = o3d.geometry.LineSet()

ray_lines.points = o3d.utility.Vector3dVector(
   np.array(line_points,dtype=np.float64)
)
ray_lines.lines = o3d.utility.Vector2iVector(
   np.array(line_indices,dtype=np.int32)
)

visual_mesh.paint_uniform_color([0.7,0.7,0.7])
point_cloud.paint_uniform_color([1.0,0.0,0.0])
origin_cloud.paint_uniform_color([0.0,0.0,1.0])
ray_lines.paint_uniform_color([1.0,0.8,0.0])

coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(
   size = 2.0,
   origin = origin
)
#Display
o3d.visualization.draw_geometries(
   [
      visual_mesh,
      point_cloud,
      origin_cloud,
      ray_lines,
      coordinate_frame
   ],
   window_name = "lidar test",
   width = 1200,
   height = 800,
   mesh_show_wireframe = True,
   mesh_show_back_face = True
)
