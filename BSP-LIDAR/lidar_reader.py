import open3d as o3d

cloud = o3d.io.read_point_cloud("momentum_lidar.ply")

print("Number of points:", len(cloud.points))
print("Point cloud bounds:", cloud.get_min_bound(), cloud.get_max_bound())

o3d.visualization.draw_geometries(
    [cloud],
    window_name="Saved Momentum Mod LiDAR Scan",
    width=1200,
    height=800
)