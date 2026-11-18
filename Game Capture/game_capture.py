import dxcam

print("Momentum Mod - DXcam Timestamp Test")
print("Press Ctrl+C to stop.")

camera = dxcam.create(
    output_color="BGRA",
    output_idx=0
)

try:
    camera.start(
        target_fps=0,
        video_mode=False
    )

    while True:

        result = camera.get_latest_frame(with_timestamp=True)

        if result is None:
            continue

        frame, frame_timestamp = result

except KeyboardInterrupt:
    print("\nDXcam capture stopped.")

finally:
    camera.stop()
    camera.release()
