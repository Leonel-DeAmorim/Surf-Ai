import dxcam
import websocket
import json
import time
import threading

WEBSOCKET_URL = "ws://127.0.0.1:8080/ws"

MAX_MATCH_DIFFERENCE_MS = 10

perf_before = time.perf_counter()
wall_time = time.time()
perf_after = time.perf_counter()

perf_midpoint = (perf_before + perf_after) / 2

WALL_CLOCK_OFFSET_SECONDS = wall_time - perf_midpoint

print(
    f"Clock calibration uncertainty: "
    f"{(perf_after - perf_before) * 500:.3f} ms"
)

frames = []
telemetry_samples = []
sample_available_perf_ns = {}

data_lock = threading.Lock()
stop_event = threading.Event()

last_sample_id = 0


def telemetry_collector(ws):
    global last_sample_id

    print("[WebSocket] Telemetry collector started.")

    while not stop_event.is_set():

        try:
            message = ws.recv()
            available_at_ns = time.perf_counter_ns()

            if message is None:
                print("[WebSocket] Connection closed.")
                break

           

            data = json.loads(message)
            if data.get("type") != "telemetry":
                continue

            samples = data.get("samples", [])

            if not samples:
                continue

            with data_lock:

                for sample in samples:

                    sample_id = sample.get("sampleId")

                    if sample_id is None:
                        continue

                    if sample_id <= last_sample_id:
                        continue

                    telemetry_samples.append(sample)

                    sample_available_perf_ns[sample_id] = available_at_ns

                    last_sample_id = sample_id

        except websocket.WebSocketTimeoutException:
            continue

        except websocket.WebSocketConnectionClosedException:
            if not stop_event.is_set():
                print("[WebSocket] Connection unexpectedly closed.")
            break

        except Exception as error:
            if not stop_event.is_set():
                print(f"[WebSocket] Receiver error: {error}")
            break

    print("[WebSocket] Telemetry collector stopped.")

def capture_frames():
    frame_id = 0
    last_frame_timestamp = None

    print("DXcam screenshot capture started.")

    camera = dxcam.create(
        output_color="BGRA",
        output_idx=0
    )

    try:

        camera.start(
            target_fps=0,
            video_mode=False
        )

        while not stop_event.is_set():

            result = camera.get_latest_frame(
                with_timestamp=True
            )

            if result is None:
                continue

            frame, frame_timestamp = result

            if frame_timestamp == last_frame_timestamp:
                continue

            frame_present_perf_ns = int(
                frame_timestamp * 1_000_000_000
            )
            last_frame_timestamp = frame_timestamp

            frame_ready_perf_ns = time.perf_counter_ns()
           
            timestamp_ms = (
                frame_timestamp
                + WALL_CLOCK_OFFSET_SECONDS
            ) * 1000

            frame_id += 1

            frames.append({
                "frameId": frame_id,

                 "image": frame,
                "timestampMs": timestamp_ms,

                "capturePerfNs": frame_present_perf_ns,

                "frameReadyPerfNs": frame_ready_perf_ns,

            })

    finally:

        camera.stop()
        camera.release()

    print("DXcam screenshot capture stopped.")


def main():

    global last_sample_id

    ws = None
    collector_thread = None

    try:

        print("[WebSocket] Connecting...")

        ws = websocket.create_connection(
            WEBSOCKET_URL,
            timeout=5
        )

        handshake = json.loads(ws.recv())

        if handshake.get("type") != "connected":
            raise RuntimeError("Invalid WebSocket handshake.")

        # Ignore samples collected before this test
        last_sample_id = handshake.get("latestSampleId", 0)

        print("[WebSocket] Connected successfully.")

        print(
            f"[WebSocket] Starting after sample ID: "
            f"{last_sample_id}"
        )

        ws.settimeout(0.5)

        # Start WebSocket receiver
        collector_thread = threading.Thread(
            target=telemetry_collector,
            args=(ws,),
            daemon=True
        )

        collector_thread.start()

        capture_frames()

    except Exception as error:

        print(f"Test error: {error}")

    finally:

        stop_event.set()

        if ws is not None:
            ws.close()

        if collector_thread is not None:
            collector_thread.join(timeout=2)


if __name__ == "__main__":
    main()
