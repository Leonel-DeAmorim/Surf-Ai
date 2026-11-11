import cv2
import mss
import numpy as np
import requests
import websocket
import json
import time
import threading
import statistics
import math

# -----------------------------
# Configuration
# -----------------------------

SERVER_URL = "http://127.0.0.1:8080"
WEBSOCKET_URL = "ws://127.0.0.1:8080/ws"

TEST_DURATION_SECONDS = 60
MAX_MATCH_DIFFERENCE_MS = 10

# -----------------------------
# Shared data
# -----------------------------

frames = []
telemetry_samples = []

data_lock = threading.Lock()
stop_event = threading.Event()

last_sample_id = 0
sample_available_perf_ns = {}

# -----------------------------
# WebSocket telemetry collection
# -----------------------------

def telemetry_collector(ws):
    global last_sample_id

    print("[WebSocket] Telemetry collector started.")

    while not stop_event.is_set():

        try:
            # Receive the next telemetry message
            message = ws.recv()
            available_at_ns = time.perf_counter_ns()

            if message is None:
                print("[WebSocket] Connection closed.")
                break

           

            data = json.loads(message)
             # Record arrival time immediately after receiving message
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


# -----------------------------
# Frame capture
# -----------------------------

def capture_frames():

    frame_id = 0
    start_time = time.perf_counter()

    print("Screenshot capture started.")
    print("Press Q to stop early.")

    with mss.MSS() as sct:

        monitor = sct.monitors[1]

        while (
            time.perf_counter() - start_time
            < TEST_DURATION_SECONDS
        ):

            screenshot = sct.grab(monitor)

            capture_perf_ns = time.perf_counter_ns()

            # Timestamp immediately after screenshot capture
            timestamp_ms = time.time_ns() / 1_000_000

            frame_id += 1

            frame = np.array(screenshot)

            frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGRA2BGR
            )

            frame_ready_perf_ns = time.perf_counter_ns()

            frames.append({
                "frameId": frame_id,
                "timestampMs": timestamp_ms,
                "capturePerfNs": capture_perf_ns,
                "frameReadyPerfNs": frame_ready_perf_ns
            })

            cv2.imshow(
                "Momentum Mod - Synchronization Test",
                frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()

    print("Screenshot capture stopped.")


# -----------------------------
# Timestamp matching
# -----------------------------

def match_frames():

    print("\nMatching frames with unique telemetry samples...")

    with data_lock:
        samples = list(telemetry_samples)

    samples.sort(key=lambda sample: sample["timestampMs"])

    sorted_frames = sorted(
        frames,
        key=lambda frame: frame["timestampMs"]
    )

    matched = []
    unmatched = []

    sample_index = 0
    used_sample_ids = set()

    for frame in sorted_frames:

        frame_timestamp = frame["timestampMs"]

        # Skip telemetry samples too early to match this frame
        while (
            sample_index < len(samples)
            and samples[sample_index]["timestampMs"]
                < frame_timestamp - MAX_MATCH_DIFFERENCE_MS
        ):
            sample_index += 1

        candidates = []

        # Find available telemetry within matching window
        for index in range(sample_index, len(samples)):

            sample = samples[index]

            difference = sample["timestampMs"] - frame_timestamp

            if difference > MAX_MATCH_DIFFERENCE_MS:
                break

            if sample["sampleId"] not in used_sample_ids:
                candidates.append((index, abs(difference)))

        if not candidates:
            unmatched.append(frame)
            continue

        best_index, difference = min(
            candidates,
            key=lambda candidate: candidate[1]
        )

        best_sample = samples[best_index]

        used_sample_ids.add(best_sample["sampleId"])

        sample_id = best_sample["sampleId"]

        telemetry_ready_ns = sample_available_perf_ns[sample_id]

        # Both converted screenshot and telemetry must be available
        pair_ready_ns = max(
            frame["frameReadyPerfNs"],
            telemetry_ready_ns
        )

        pair_ready_latency_ms = (
            pair_ready_ns - frame["capturePerfNs"]
        ) / 1_000_000

        matched.append({
            "frameId": frame["frameId"],
            "frameTimestampMs": frame_timestamp,
            "sampleId": sample_id,
            "telemetryTimestampMs": best_sample["timestampMs"],
            "differenceMs": difference,
            "pairReadyLatencyMs": pair_ready_latency_ms
        })

    unused_samples = [
        sample for sample in samples
        if sample["sampleId"] not in used_sample_ids
    ]

    return matched, unmatched, unused_samples


# -----------------------------
# Statistics
# -----------------------------

def print_statistics(matched, unmatched, unused_samples):

    total_frames = len(frames)
    total_samples = len(telemetry_samples)
    total_matched = len(matched)

    differences = [
        match["differenceMs"]
        for match in matched
    ]

    print("\n========== UNIQUE SYNCHRONIZATION RESULTS ==========")

    print(f"Frames captured:          {total_frames}")
    print(f"Telemetry samples:        {total_samples}")
    print(f"Unique matched frames:    {total_matched}")
    print(f"Unmatched frames:         {len(unmatched)}")
    print(f"Unused telemetry samples: {len(unused_samples)}")

    if total_frames:

        match_percentage = (
            total_matched / total_frames
        ) * 100

        print(f"Unique match percentage:  {match_percentage:.2f}%")

    if differences:

        sorted_differences = sorted(differences)

        p95_index = max(
            0,
            int(0.95 * len(sorted_differences)) - 1
        )

        print(
            f"Average difference:       "
            f"{statistics.mean(differences):.3f} ms"
        )

        print(
            f"Median difference:        "
            f"{statistics.median(differences):.3f} ms"
        )

        print(
            f"95th percentile:          "
            f"{sorted_differences[p95_index]:.3f} ms"
        )

        print(
            f"Maximum difference:       "
            f"{max(differences):.3f} ms"
        )

    # Screenshot-to-combined-input availability latency
    pair_latencies = [
        match["pairReadyLatencyMs"]
        for match in matched
    ]

    if pair_latencies:

        sorted_latencies = sorted(pair_latencies)

        p95_index = max(
            0,
            int(np.ceil(0.95 * len(sorted_latencies))) - 1
        )

        print("\n========== AI INPUT READINESS RESULTS ==========")

        print(
            f"Average pair readiness:  "
            f"{statistics.mean(pair_latencies):.3f} ms"
        )

        print(
            f"Median pair readiness:   "
            f"{statistics.median(pair_latencies):.3f} ms"
        )

        print(
            f"P95 pair readiness:      "
            f"{sorted_latencies[p95_index]:.3f} ms"
        )

        print(
            f"Maximum pair readiness:  "
            f"{max(pair_latencies):.3f} ms"
        )

        print(
            f"Pairs ready under 50ms:  "
            f"{sum(x <= 50 for x in pair_latencies)}"
        )

        print(
            f"Pairs ready under 100ms: "
            f"{sum(x <= 100 for x in pair_latencies)}"
        )

    print("================================================")


# -----------------------------
# Main program
# -----------------------------

def main():

    global last_sample_id

    ws = None
    collector_thread = None

    try:

        # Check HTTP server health
        response = requests.get(
            f"{SERVER_URL}/health",
            timeout=2
        )

        response.raise_for_status()

        print("Server online.")

        # Connect to WebSocket
        print("[WebSocket] Connecting...")

        ws = websocket.create_connection(
            WEBSOCKET_URL,
            timeout=5
        )

        # Receive initial handshake
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

        # Allow collector to periodically check stop_event
        ws.settimeout(0.5)

        # Start WebSocket receiver
        collector_thread = threading.Thread(
            target=telemetry_collector,
            args=(ws,),
            daemon=True
        )

        collector_thread.start()

        # Capture screenshots
        capture_frames()

    except Exception as error:

        print(f"Test error: {error}")

    finally:

        stop_event.set()

        if ws is not None:
            ws.close()

        if collector_thread is not None:
            collector_thread.join(timeout=2)

    if not frames:
        print("No frames captured. Test stopped.")
        return

    if not telemetry_samples:
        print("No telemetry samples received. Test stopped.")
        return

    # Match screenshots and telemetry
    matched, unmatched, unused_samples = match_frames()

    # Display results
    print_statistics(
        matched,
        unmatched,
        unused_samples
    )


if __name__ == "__main__":
    main()