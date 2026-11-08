
import websocket
import json

ws = websocket.create_connection(
    "ws://127.0.0.1:8080/ws",
    timeout=5
)

print("Connected to server!")

handshake = json.loads(ws.recv())
print("Server response:", handshake)

print("Waiting for telemetry...")

try:
    while True:
        message = json.loads(ws.recv())

        print("\nMessage type:", message.get("type"))

        if message.get("type") == "telemetry":
            samples = message.get("samples", [])

            print("Received samples:", len(samples))

            if samples:
                print("Latest sample ID:", samples[-1]["sampleId"])
                print("Latest timestamp:", samples[-1]["timestampMs"])
            else:
                print("WARNING: Empty telemetry batch received!")

except KeyboardInterrupt:
    print("\nTest stopped.")

finally:
    ws.close()
