import random
import paho.mqtt.client as paho
import csv
import os
import json
import time

def send_message():
    client = paho.Client()

    broker_address = "192.168.151.101"
    broker_port = 1883

    print("Connecting to broker: " + broker_address + ":" + str(broker_port))

    client.username_pw_set("edge/edge1011", "Edge1011!")
    client.connect(broker_address, broker_port, 60)
    
    client.loop_start()

    base_event = {
        "type": "output_detected",
        "text": "new output detected",
    }

    time.sleep(5)

    client.publish("s/us", "100,OEE Simulator")

    while True:
        output_event = base_event.copy()
        output_event["time"] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
        full_amount_chance = random.randint(1, 10)
        output_event["output"] = 8 if full_amount_chance == 1 else 9
        client.publish("event/events/create", json.dumps(output_event))
        time.sleep(random.randint(9, 12))

send_message()