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
            print("Position:  ", data.get('position'))
            print("Angles:    ", data.get('angles'))
            print("Velocity:  ", data.get('velocity'))
            print("Speed:     ", data.get('speed'))
            print("Energy:    ", data.get('energy'))
            print("WishVel:   ", data.get('wishVel'))
            print("Game Time: ", data.get('gameTime'))
            print("Run Time:  ", data.get('runTime'))
            print("Move Type: ", data.get('moveType'))
            print("Ducking:   ", data.get('ducking'))
            print("Buttons:   ", data.get('physicalButtons'))
            print("Map:       ", data.get('mapName'))
            print("Last Tick: ", data.get('lastTick'))

    except Exception as error:
        print("Connection or data error", error)

    time.sleep(0.05)