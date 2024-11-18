import subprocess
import shutil
import requests
import tempfile
import json
import logging
import yaml
import time

from datetime import datetime

from paho.mqtt import client as mqtt_client
from paho.mqtt.client import Client,MQTTMessage

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

config_data = None

with open('config.yml', 'r') as file:
    config_data = yaml.safe_load(file)

print(config_data)

jwt_token = None
observer = None
device_id = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def start_camera_eval():
    # xvfb-run sudo sh imx500_start.sh
    p = subprocess.Popen(['systemctl', 'start', 'camera-runner.service', '&'], cwd='/home/pi/sc_t2r/', stdout=subprocess.PIPE)
    out, err = p.communicate()

def stop_camera_eval():
    # xvfb-run sudo sh imx500_start.sh
    p = subprocess.Popen(['systemctl', 'stop', 'camera-runner.service', '&'], cwd='/home/pi/sc_t2r/', stdout=subprocess.PIPE)
    out, err = p.communicate()

def status_camera_eval():
    # xvfb-run sudo sh imx500_start.sh
    p = subprocess.Popen(['systemctl', 'status', 'camera-runner.service', '&'], cwd='/home/pi/sc_t2r/', stdout=subprocess.PIPE)
    out, err = p.communicate()

def is_camera_powered_on():
    p = subprocess.Popen(['./i2cread', '40', '04'], cwd='/home/pi/sc_t2r/', stdout=subprocess.PIPE)
    out, err = p.communicate()
    result = out.decode('utf-8')[:3]
    if result == '0x0':
        return False
    else:
        return True
    
def power_on_camera():
    p = subprocess.Popen(['sh', 'power_supply_start.sh'], cwd='/home/pi/sc_t2r/', stdout=subprocess.PIPE)
    out, err = p.communicate()

def power_off_camera():
    p = subprocess.Popen(['sh', 'power_supply_stop.sh'], cwd='/home/pi/sc_t2r/', stdout=subprocess.PIPE)
    out, err = p.communicate()

def bootstrap(client):
    URL = "http://127.0.0.1:8000/tedge/file-transfer/{}/c8y-configuration-plugin".format(config_data['c8y']['child'])
    CONFIG_TYPE = "c8y-configuration-plugin"

    print(f"Uploading the config file")
    with open(config_data['c8y']['config-plugin-path'], 'rb') as file:
        content = file.read()

    response = requests.put(URL, data=content)
    print(URL, response.status_code)

    # Set config update command status to successful
    print(f"Setting config_snapshot status for config-type: {CONFIG_TYPE} to successful")
    config_snapshot_response_topic = f"tedge/{config_data['c8y']['child']}/commands/res/config_snapshot" # {config_type}
    message_payload = json.dumps({
            "path": "",
            "type": CONFIG_TYPE,
    })
    client.publish(f"{config_snapshot_response_topic}", message_payload)
    client.publish('c8y/s/uat', '')

def file_system_listening(client: mqtt_client.Client):
    global observer
    class PictureCreatedEventHandler(FileSystemEventHandler):

        def __init__(self):
            super()
            global jwt_token
            self.client = requests.Session()

        def on_created(self, event):
            global device_id
            logging.info(event)
            pic_upload_event = {
                'type': 'c8y_PictureUpload',
                'text': 'See attached picture',
                'time': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                'source': {
                    'id': device_id
                }
            }
            self.client.headers = {
                'Authorization': 'Bearer ' + jwt_token,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            res = self.client.post(config_data['c8y']['url'] + '/event/events', data=json.dumps(pic_upload_event))
            logging.info(res)
            eventId = res.json()['id']

            # Attach Binary
            filename = event.src_path.split('/')[-1]
            with open(event.src_path,'rb') as pic:
                res = self.client.post(config_data['c8y']['url'] + '/event/events/' + eventId + '/binaries', data=pic.read(), headers={'Content-Type': 'application/octet-stream', 'Content-Disposition': 'attachment; filename="' + filename + '"'})
            logging.info(res)
            logging.info(res.json())

    class OutputCreatedEventHandler(FileSystemEventHandler):

        def __init__(self, client):
            super()
            self.client = client

        def on_created(self, event):
            logging.info(event)
            filename = event.src_path
            file_number = filename.split('_')[-1].split('.')[0]
            output = {}
            output[file_number] = {}
            with open(filename, 'r') as output_file:
                i = 0
                for line in output_file:
                    output[file_number][str(i)] = float(line)
                    i += 1

            client.publish('tedge/measurements/' + config_data['c8y']['child'], json.dumps(output))

    picture_handler = PictureCreatedEventHandler()
    output_handler = OutputCreatedEventHandler(client)
    observer = Observer()
    observer.schedule(picture_handler, config_data['imx500']['pics-path'], recursive=False)
    observer.schedule(output_handler, config_data['imx500']['output-path'], recursive=False)
    observer.start()

def connect_mqtt() -> mqtt_client.Client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(config_data['c8y']['child'])
    client.on_connect = on_connect
    client.connect(config_data['thin-edge']['broker'], config_data['thin-edge']['port'])
    return client

def subscribe(client: mqtt_client.Client):
    def on_jwt_token(client, userdata, msg: MQTTMessage):
        global jwt_token
        global device_id
        jwt_token = msg.payload.decode('utf-8').split(',',1)[1]
        print("received token: " + jwt_token)
        res = requests.get(config_data['c8y']['url'] + '/identity/externalIds/c8y_Serial/' + config_data['c8y']['child'], headers={'Authorization': 'Bearer ' + jwt_token})
        logging.info(res)
        device_id = res.json()['managedObject']['id']
        logging.info('Child device ID: ' + device_id)

    jwt_token_topic = 'c8y/s/dat'
    client.subscribe(jwt_token_topic)
    client.message_callback_add(jwt_token_topic, on_jwt_token)

    def on_config_snapshot_request(client, userdata, msg: MQTTMessage):
        print(f"Config snapshot request received `{msg.payload.decode()}` on `{msg.topic}` topic")

        payload = json.loads(msg.payload.decode())
        print(payload)

        path = payload["path"]
        config_type = payload["type"]
        upload_url_path = payload["url"]

        # Set config update command status to executing
        print(f"Setting config_snapshot status for config-type: {config_type} to executing")
        config_snapshot_executing_topic = f"tedge/{config_data['c8y']['child']}/commands/res/config_snapshot" # {config_type}
        message_payload = json.dumps({
                "status": "executing",
                "path": path,
                "type": config_type,
        })
        client.publish(f"{config_snapshot_executing_topic}", message_payload)


        if config_type == "c8y-configuration-plugin":
            path = config_data['c8y']['config-plugin-path']

        # Upload the requested file
        print(f"Uploading the config file")
        with open(path, 'rb') as file:
            content = file.read()
        response = requests.put(upload_url_path, data=content)
        print(upload_url_path, response.status_code)

        # Set config update command status to successful
        print(f"Setting config_snapshot status for config-type: {config_type} to successful")
        config_snapshot_executing_topic = f"tedge/{config_data['c8y']['child']}/commands/res/config_snapshot" # {config_type}
        message_payload = json.dumps({
                "status": "successful",
                "path": path,
                "type": config_type,
        })
        client.publish(f"{config_snapshot_executing_topic}", message_payload)

    config_snapshot_req_topic = f"tedge/{config_data['c8y']['child']}/commands/req/config_snapshot"
    client.subscribe(config_snapshot_req_topic)
    client.message_callback_add(config_snapshot_req_topic, on_config_snapshot_request)

    def on_config_update_request(client: Client, userdata, msg: MQTTMessage):
        print(f"Config update request received `{msg.payload.decode()}` from `{msg.topic}` topic")

        payload = json.loads(msg.payload.decode())

        payload_path = payload["path"]
        download_url = payload["url"]
        if payload["type"] == None:
            config_type = payload["path"]
        else:
            config_type = payload["type"]

        # Set config update command status to executing
        config_snapshot_executing_topic = f"tedge/{config_data['c8y']['child']}/commands/res/config_update" # {config_type}
        message_payload = json.dumps({
                "status": "executing",
                "path": payload_path,
                "type": config_type,
        })
        client.publish(f"{config_snapshot_executing_topic}", message_payload)

        # Download the config file update from tedge
        print(download_url)
        response = requests.get(download_url)
        print(response.content, response.status_code)
        target_path = tempfile.NamedTemporaryFile(prefix=config_type, delete=False)
        print(target_path.name)
        try:
            target_path.write(response.content)
        finally:
            target_path.close()

        # Replace the existing config file with the updated file downloaded from tedge
        shutil.move(target_path.name, payload_path)

        # Set config update command status to successful
        config_snapshot_executing_topic = f"tedge/{config_data['c8y']['child']}/commands/res/config_update"
        message_payload = json.dumps({
                "status": "successful",
                "path": payload_path,
                "type": config_type,
        })
        client.publish(config_snapshot_executing_topic, message_payload)
    
    config_update_topic = f"tedge/{config_data['c8y']['child']}/commands/req/config_update"
    client.subscribe(config_update_topic)
    client.message_callback_add(config_update_topic, on_config_update_request)

    def on_firmware_update_request(client: Client, userdata, msg: MQTTMessage):
        print(
            f"Firmware update request received `{msg.payload.decode()}` from `{msg.topic}` topic"
        )

        payload = json.loads(msg.payload.decode())

        req_id = payload["id"]
        download_url = payload["url"]

        # Set firmware update command status to executing
        firmware_update_res_topic = (
            f"tedge/{config_data['c8y']['child']}/commands/res/firmware_update"
        )
        message_payload = json.dumps(
            {
                "status": "executing",
                "id": req_id,
            }
        )
        print(
            f"Sending firmware update executing response to `{firmware_update_res_topic}` topic with payload `{message_payload}`"
        )
        client.publish(f"{firmware_update_res_topic}", message_payload)

        # Download the firmware file update from tedge
        print(download_url)
        response = requests.get(download_url)
        print("Download status code: ", response.status_code)
        target_path = tempfile.NamedTemporaryFile(prefix=req_id, delete=False)
        print("Firmware file downloaded to: ", target_path.name)
        try:
            target_path.write(response.content)
        finally:
            target_path.close()

        message_payload = json.dumps(
            {
                "status": "successful",
                "id": req_id,
            }
        )
        print(
            f"Sending firmware update successful response to `{firmware_update_res_topic}` topic with payload `{message_payload}`"
        )
        client.publish(firmware_update_res_topic, message_payload)

    firmware_update_topic = f"tedge/{config_data['c8y']['child']}/commands/req/firmware_update"
    client.subscribe(firmware_update_topic)
    client.message_callback_add(firmware_update_topic, on_firmware_update_request)

    def on_child_operation_received(client, userdata, msg: MQTTMessage):
        decoded_message = msg.payload.decode()
        print('Operation received: ' + decoded_message)
        msg_parts = decoded_message.split(',')
        if msg_parts[1] == config_data['c8y']['child']:
            if msg_parts[0] == '511':
                client.publish('c8y/s/us/' + config_data['c8y']['child'], '501,c8y_Command')
                print('Handle child command')
                if msg_parts[2] == 'power on':
                    print('Turn camera power on')
                    power_on_camera()
                    client.publish('c8y/s/us/' + config_data['c8y']['child'], '503,c8y_Command,Turned on')
                elif msg_parts[2] == 'power off':
                    print('Turn camera power off')
                    power_off_camera()
                    client.publish('c8y/s/us/' + config_data['c8y']['child'], '503,c8y_Command,Turned off')
                elif msg_parts[2] == 'camera on':
                    print('Start camera')
                    start_camera_eval()
                    client.publish('c8y/s/us/' + config_data['c8y']['child'], '503,c8y_Command,Camera running')
                elif msg_parts[2] == 'camera off':
                    print('Stop camera')
                    stop_camera_eval()
                    client.publish('c8y/s/us/' + config_data['c8y']['child'], '503,c8y_Command,Camera stopped')
                elif msg_parts[2] == 'power status':
                    print('Check power status')
                    client.publish('c8y/s/us/' + config_data['c8y']['child'], '503,c8y_Command,' + str(is_camera_powered_on()))
                elif msg_parts[2] == 'camera status':
                    print('Check camera status')
                    out, err = status_camera_eval()
                    client.publish('c8y/s/us/' + config_data['c8y']['child'], '503,c8y_Command,' + out)
                else:
                    print('Unrecongnized command')
            elif msg_parts[0] == '528':
                software_list = []
                current_software = []
                for part in msg_parts[2:]:
                    current_software.append(part)
                    if len(current_software) == 4:
                        software_list.append(current_software)
                        current_software = []
                client.publish('c8y/s/us/' + config_data['c8y']['child'], '501,c8y_SoftwareUpdate')
                current_software = None
                for sw in software_list:
                    if sw[-1] != 'delete':
                        current_software = sw
                time.sleep(5)
                client.publish('c8y/s/us/' + config_data['c8y']['child'], '116,' + ','.join(current_software[:-1]))
                client.publish('c8y/s/us/' + config_data['c8y']['child'], '503,c8y_SoftwareUpdate')
            else:
                print('Not a command or softwarea update => Ignore')
        else:
            print('Not for that child device => Ignore')
        

    general_child_operation_topic = 'c8y/s/ds'
    client.subscribe(general_child_operation_topic)
    client.message_callback_add(general_child_operation_topic, on_child_operation_received)


def run():

    client = connect_mqtt()
    subscribe(client)
    bootstrap(client)
    file_system_listening(client)
    client.loop_forever()

if __name__ == '__main__':
    #print(is_camera_powered_on())
    #power_on_camera()
    #print(is_camera_powered_on())
    
    try:
        run()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()