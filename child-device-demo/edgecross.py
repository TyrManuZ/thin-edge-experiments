import paho.mqtt.client as mqtt
import json

# MQTT broker information
broker_address = "localhost"
broker_port = 1883

# MQTT topic to subscribe to
topic = "edgecross"


def boolean_to_number(val):
    if isinstance(val, bool):
        return int(val)
    else:
        return val
    
def parse_edgeross_format(message):
    message = json.loads(message)
    parsed_messages = []
    events = []
    for record in message["records"]:
        tedge_message = {}
        tedge_event = {}
        tedge_message['time'] = record['time'][:record['time'].find('.')+3] + 'Z'
        tedge_event['time'] = record['time'][:record['time'].find('.')+3] + 'Z'
        tedge_event['type'] = 'edgecross_raw_data'
        for data in record["record"]:
            tedge_event[data['name']] = data['data']
            if not isinstance(data['data'], str):
                tedge_message[data['name']] = boolean_to_number(data['data'])
        parsed_messages.append(tedge_message)
        events.append(tedge_event)
    return (parsed_messages, events)

# Callback function for when the client receives a CONNACK response from the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(topic)
    else:
        print("Failed to connect to MQTT broker")

# Callback function for when a message is received from the broker
def on_message(client, userdata, msg):
    output = parse_edgeross_format(msg.payload.decode())
    for message in output[0]:
        client.publish('tedge/measurements/edgecross', json.dumps(message))
    for message in output[1]:
        client.publish('tedge/events/edgecross_raw_data/edgecross', json.dumps(message))

# Create a MQTT client instance
client = mqtt.Client()

# Assign callback functions
client.on_connect = on_connect
client.on_message = on_message

# Connect to the MQTT broker
client.connect(broker_address, broker_port, 60)

# Start the network loop to process MQTT messages
client.loop_start()

# Keep the script running until interrupted
try:
    while True:
        pass
except KeyboardInterrupt:
    print("Script interrupted")

# Disconnect from the MQTT broker
client.disconnect()