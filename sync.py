
import dxcam
import websocket
import json
import threading


WEBSOCKET_URL = "ws://127.0.0.1:8080/ws"


frames = []
telemetry_samples = []

stop_event = threading.Event()

last_sample_id = 0


def telemetry_collector(ws):
    global last_sample_id

    print("[WebSocket] Telemetry collection started.")

    while not stop_event.is_set():

        try:
            message = ws.recv()

            if message is None:
                break

            data = json.loads(message)

            if data.get("type") != "telemetry":
                continue

            samples = data.get("samples", [])

            for sample in samples:

                sample_id = sample.get("sampleId")

                if sample_id is None:
                    continue

                if sample_id <= last_sample_id:
                    continue

                telemetry_samples.append(sample)

                last_sample_id = sample_id

        except websocket.WebSocketTimeoutException:
            continue

        except websocket.WebSocketConnectionClosedException:
            print("[WebSocket] Connection closed.")
            break

        except Exception as error:
            print(f"[WebSocket] Error: {error}")
            break

    print("[WebSocket] Telemetry collection stopped.")


def capture_frames():

    frame_id = 0

    print("[DXcam] Frame capture started.")

    camera = dxcam.create(
        output_color="BGRA",
        output_idx=0
    )

    last_frame_timestamp = None

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

            last_frame_timestamp = frame_timestamp

            frame_id += 1

            frames.append({
                "frameId": frame_id,
                "image": frame,
                "timestamp": frame_timestamp
            })

    finally:

        camera.stop()
        camera.release()

    print("[DXcam] Frame capture stopped.")



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

        last_sample_id = handshake.get("latestSampleId", 0)

        print("[WebSocket] Connected successfully.")

        ws.settimeout(0.5)

        collector_thread = threading.Thread(
            target=telemetry_collector,
            args=(ws,),
            daemon=True
        )

        collector_thread.start()

        capture_frames()

    except KeyboardInterrupt:

        print("\n[Main] Stopping collection...")

    except Exception as error:

        print(f"[Main] Error: {error}")

    finally:

        stop_event.set()

        if ws is not None:
            ws.close()

        if collector_thread is not None:
            collector_thread.join(timeout=2)

    
        print(f"Frames collected: {len(frames)}")
        print(f"Telemetry samples collected: {len(telemetry_samples)}")

if __name__ == "__main__":
    main()
