# Real-Time Synthetic LiDAR Simulator & RL Surfing Bot

A highly optimized Python pipeline that streams real-time player positions (`XYZ`, `Angles`) inside a parsed Source engine BSP map and generates a live, synthetic 3D LiDAR point cloud. 

By leveraging the map's native **PVS (Potentially Visible Set)** and **BSP Tree**, the system dynamically culls invisible geometry to achieve real-time, high-frame-rate laser raycasting updates without rendering the entire map mesh.

## Core Features

* **BSP Structural Parsing**: Leverages `bsp_tool` to deconstruct compiled binary map lumps (Vertices, Edges, Faces, and Leaves).
* **PVS Optimization**: Traverses the BSP tree to pinpoint the player's current leaf cluster and dynamically streams only visible geometry to the ray-caster.
* **Continuous Streaming Loop**: Non-blocking Open3D visualizer that accepts live coordinate inputs and updates the point cloud at runtime.
* **Realistic LiDAR Modeling**: Simulates custom horizontal/vertical fields of view.
* **Telemetry Data Pipeline**: HTTP Requestsfrom momentum mod to node server. Around 1-2 ms Panorama to Node response time sampling ddata at 200 transmissions a second.


## Prerequisites & Installation
-python 3.14.7
-websocket pip


