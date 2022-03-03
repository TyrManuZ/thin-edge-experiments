import paho.mqtt.client as paho
import yaml
import json
import time

from tinkerforge.ip_connection import IPConnection
from tinkerforge.bricklet_linear_poti import BrickletLinearPoti

CONFIG_FILE = '/etc/thin-edge-tinkerforge/linear-poti.yml'

def read_linear_poti():

    config = yaml.safe_load(open(CONFIG_FILE))
    thinEdgeClient = paho.Client()

    tinkerforgeClient = IPConnection()
    tinkerforgeClient.connect(config['tinkerforge']['host'], config['tinkerforge']['port'])

    bricklets = []
    for bricklet in config['bricklets']:
        bricklets.append(BrickletLinearPoti(bricklet, tinkerforgeClient))

    thinEdgeClient.connect(config['thin-edge']['host'], config['thin-edge']['port'], 60)
    thinEdgeClient.loop_start()

    if len(bricklets) > 0:
        while True:
            time.sleep(5)
            tedgeMeasurement = {
                "linearPoti": {}
            }
            i = 1
            for bricklet in bricklets:
                tedgeMeasurement['linearPoti']['position' + str(i)] = bricklet.get_position()
            thinEdgeClient.publish("tedge/measurements", json.dumps(tedgeMeasurement))