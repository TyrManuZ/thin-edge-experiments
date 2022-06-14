import random
import paho.mqtt.client as paho
import csv
import os
import json
import time

def send_message():
    client = paho.Client()

    time.sleep(30)

    try:
        broker_address = os.environ['THIN_EDGE_BROKER_ADDRESS']
    except KeyError:
        broker_address = "localhost"

    try:
        broker_port = int(os.environ['THIN_EDGE_BROKER_PORT'])
    except KeyError:
        broker_port = 1883

    print("Connecting to broker: " + broker_address + ":" + str(broker_port))

    client.connect(broker_address, broker_port, 60)
    client.loop_start()

    base_event = {
        "type": "output_detected",
        "text": "new output detected",
    }
    base_availability_event = {
        "type": "availability",
    }

    while True:
        output_event = base_availability_event.copy()
        available_chance = random.randint(1, 100)
        if available_chance > 5:
            output_event["available"] = 1.0
            output_event["text"] = "Machine available"
            output_event["time"] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
            client.publish("c8y/event/events/create", json.dumps(output_event))
            output_event = base_event.copy()
            output_event["time"] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
            full_amount_chance = random.randint(1, 10)
            output_event["output"] = 8 if full_amount_chance == 1 else 9
            quality_amount_chance = random.randint(1, 20)
            output_event["quality"] = output_event["output"] - 1 if quality_amount_chance == 1 else output_event["output"]
            client.publish("c8y/event/events/create", json.dumps(output_event))
        else:
            output_event["available"] = 0
            output_event["text"] = "Machine not available"
            output_event["time"] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
        time.sleep(random.randint(9, 12))

send_message()