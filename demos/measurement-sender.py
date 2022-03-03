import paho.mqtt.client as paho
import time
import json
from random import randint

thinEdgeClient = paho.Client()
thinEdgeClient.connect("localhost", 1883, 60)

thinEdgeClient.loop_start()

time.sleep(5)

while True:
    measurement = {
        "random": randint(0,20)
    }
    thinEdgeClient.publish("tedge/measurements", json.dumps(measurement))
    time.sleep(5)