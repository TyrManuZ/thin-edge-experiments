import paho.mqtt.client as paho
import random
import json
import time

def send_message():
    client = paho.Client()

    client.connect("127.0.0.1", 1883, 60)
    client.loop_start()
    while True:
        time.sleep(5)
        tedgeMeasurement = {
            "example": random.randint(-20, 20)     
        }
        client.publish("tedge/measurements", json.dumps(tedgeMeasurement))