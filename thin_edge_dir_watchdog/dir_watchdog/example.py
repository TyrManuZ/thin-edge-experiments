import paho.mqtt.client as paho
import random
import json
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileCreateHandler(FileSystemEventHandler):
    def on_created(self, event):
        print("Created: " + event.src_path)


event_handler = FileCreateHandler()

# Create an observer.
observer = Observer()

# Attach the observer to the event handler.
observer.schedule(event_handler, ".", recursive=True)

# Start the observer.
observer.start()

try:
    print("Test")
    while observer.is_alive():
        observer.join(1)
finally:
    observer.stop()
    observer.join()

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