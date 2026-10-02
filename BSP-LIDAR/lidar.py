import math
import bsp_parser

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
#Test to see if import works
print("PVS geometry:", len(bsp_parser.pvs_geometry))
print("Player position:", bsp_parser.position)
