import cv2
import mss
import numpy as np


with mss.mss() as sct:
        monitor = sct.monitors[1]

        print("Momentum Mod Game Capture")
        print("Press Q in the preview window to stop.")

        while True:
            screenshot = sct.grab(monitor)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            cv2.imshow("Momentum Mod - Game Capture", frame)

            # Exit when Q is pressed in the preview window.
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()
        print("Game capture stopped.")
