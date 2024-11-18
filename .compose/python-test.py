import ssl
import time
import random
import logging
import paho.mqtt.client as paho

logging.basicConfig(level=logging.DEBUG)

# --------------------------
# Path to the files
ca = '...' 
cert = '...'
private = '...'
# client_id needs to be identical to CN in certificate
client_id = '...'
url = 'demo.eu-latest.cumulocity.com'
# --------------------------

def on_connect(client, userdata, flags, rc):
    logging.info('Agent connected with result code: ' + str(rc))

def on_message(self, client, userdata, msg):
    logging.info('Message received on: ' + msg.topic)
    decoded = msg.payload.decode('utf-8')
    logging.info(decoded)

logging.info('Create SSL context')
ssl_context = ssl.create_default_context()
ssl_context.load_verify_locations(cafile=ca)
ssl_context.load_cert_chain(certfile=cert, keyfile=private)

logging.info('Configure MQTT client')
client = paho.Client(client_id=client_id)
client.tls_set_context(context=ssl_context)
client.on_connect = on_connect
client.on_message = on_message
client.connect(url, 8883, 30)
client.loop_start()

while True:
    time.sleep(5)
    logging.debug('Sending data')
    client.publish('s/us', '200,c8y_Temperature,T,' + str(random.randint(19, 28)))