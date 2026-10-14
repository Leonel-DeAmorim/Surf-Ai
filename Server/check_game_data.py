import json
import time 
import urllib.request

url = "http://127.0.0.1:8080/latest"

print("Waiting for Momentum Mod Data")

while True:
    try:
     with urllib.request.urlopen(url, timeout=2) as response:
        data = json.loads(response.read().decode("utf-8"))

        if data is None:
            print("No data received yet")

        else:
            print("Position:", data.get("position"))
            print("Angles:", data.get("angles"))
            print("----------------------------------------")

    except Exception as error:
        print("Connection or data error", error)

    time.sleep(0.05)