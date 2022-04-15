from random import random
import paho.mqtt.client as paho
import csv
import json
import time

def send_message():
    client = paho.Client()

    client.connect("127.0.0.1", 1883, 60)
    client.loop_start()

    cached_positions = []

    with open('positions.csv', 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            cached_positions.append(row)

    index = random.randint(0, len(cached_positions) - 1)

    while True:
        for i, position in enumerate(cached_positions):
            time.sleep(5)
            client.publish("c8y/s/us", "402," + str(position[0]) + "," + str(position[1]))
            index = (index + 1) % len(cached_positions)

send_message()