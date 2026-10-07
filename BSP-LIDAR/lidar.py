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

origin =(0,0,5)
direction = (0.6,0.48,-0.64)

rays = o3d.core.Tensor([
    [0,0,5,0.6,0.48,-0.64]
],dtype=o3d.core.Dtype.Float32)

ans = scene.cast_rays(rays)
print(ans)

t= ans["t_hit"][0].item()

if math.isfinite(t):
    hit_x = origin[0] +direction[0]*t
    hit_y = origin[1] +direction[1]*t
    hit_z = origin[2] +direction[2]*t
    hit = (hit_x,hit_y,hit_z)
    print("Hit Point: ", hit)

else:
    print("No Hit")
