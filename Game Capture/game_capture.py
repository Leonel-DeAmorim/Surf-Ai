import cv2
import mss
import numpy as np
import time

frame_id = 0

frame_start_time = time.perf_counter()
fps_frame_count = 0

print("Momentum Mod Game Capture")
print("Press Q in the preview window to stop.")

with mss.mss() as sct:
        monitor = sct.monitors[1]
        while True:
            screenshot = sct.grab(monitor)
            capture_timestamp_ms = time.time_ns() / 1_000_000
            frame_id += 1
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            fps_frame_count += 1
            elapsed = time.perf_counter() - frame_start_time
            if elapsed >= 1.0:
                 fps =fps_frame_count / elapsed
                 print(
                      f"FPS: {fps:.2f} | "
                      f"Frame ID: {frame_id} | "
                      f"Capture Timestamp: {capture_timestamp_ms:.2f}"
                 )
                 frame_start_time = time.perf_counter()
                 fps_frame_count = 0

            cv2.imshow("Momentum Mod - Game Capture", frame)

            # Exit when Q is pressed in the preview window.
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()
        print("Game capture stopped.")
