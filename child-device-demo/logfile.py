import requests
import json
import logging
import time
import http.client

from datetime import datetime

# ------------------------------------------
# Cumulocity configuration
# ------------------------------------------
C8Y_BASE = 'http://examples.cumulocity.com'
C8Y_TENANT = ''
C8Y_USER = ''
C8Y_PASSWORD = ''
# ------------------------------------------

# ------------------------------------------
# Additional configuration
# ------------------------------------------
USE_EVENT_APPROACH = True
# ------------------------------------------


http.client.HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

client = requests.Session()
client.auth = (C8Y_TENANT + '/' + C8Y_USER, C8Y_PASSWORD)
client.headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

FILE_CONTENT = 'line1=value1\nline2=value2\nline3=value3\nline4=value4'
C8Y_EXT_ID_TYPE = 'c8y_DeviceTutorials'
C8Y_EXT_ID_VALUE = 'c8y_LogfileDevice'

'''
Preparation:

1. Create device with logifle feature
2. Poll for operation
'''

# Check if device already existing
res = client.get(C8Y_BASE + '/identity/externalIds/' + C8Y_EXT_ID_TYPE + '/' + C8Y_EXT_ID_VALUE)
if res.status_code > 299:
    # Create device
    logfileDevice = {
        'name': 'D-MGMT Examples: Logfile',
        'type': C8Y_EXT_ID_VALUE,
        'c8y_IsDevice': {},
        'c8y_SupportedOperations': [
            'c8y_LogfileRequest'
        ],
        'c8y_SupportedLogs': [
            'log_A',
            'log_B'
        ],
        'com_cumulocity_model_Agent': {}
    }
    res = client.post(C8Y_BASE + '/inventory/managedObjects', data=json.dumps(logfileDevice))
    DEVICE_ID = res.json()['id']
    # Assign externalId
    externalId = {
        'externalId': C8Y_EXT_ID_VALUE,
        'type': C8Y_EXT_ID_TYPE
    }
    client.post(C8Y_BASE + '/identity/globalIds/' + DEVICE_ID + '/externalIds', data=json.dumps(externalId))
else:
    DEVICE_ID = res.json()['managedObject']['id']

# Poll for operation
logfileOperation = None
while logfileOperation == None:
    time.sleep(5)
    res = client.get(C8Y_BASE + '/devicecontrol/operations?status=PENDING&agentId=' + DEVICE_ID)
    operations = res.json()['operations']
    if len(operations) > 0:
        operation = operations[0]
        if 'c8y_LogfileRequest' in operation.keys():
            logfileOperation = operation
            
'''
Approach 1 (preferred):

Step 1: Create event
Step 2: Upload logfile to event as binary
Step 3: Update operation (with ID reference to logfile in event storage)
'''
if USE_EVENT_APPROACH:
    # Create event
    logfileEvent = {
        'type': 'c8y_Logfile',
        'text': 'See attached logfile',
        'time': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
        'source': {
            'id': DEVICE_ID
        }
    }
    res = client.post(C8Y_BASE + '/event/events/', data=json.dumps(logfileEvent))
    eventId = res.json()['id']

    # Attach Binary
    res = client.post(C8Y_BASE + '/event/events/' + eventId + '/binaries', data=bytes(FILE_CONTENT, 'utf-8'), headers={'Content-Type': 'application/octet-stream'})
    binaryRef = res.json()['self']

    # Update operation
    logfileFragment = logfileOperation['c8y_LogfileRequest']
    logfileFragment['file'] = binaryRef
    updatedOperation = {
        'status': 'SUCCESSFUL',
        'c8y_LogfileRequest': logfileFragment
    }
    client.put(C8Y_BASE + '/devicecontrol/operations/' + logfileOperation['id'], data=json.dumps(updatedOperation))

'''
Approach 2 (legacy):

Step 1: Upload logfile to file storage
Step 2: Update operation (with ID reference to logfile in file storage)

Note: You need to manually delete files from file storage. There is no automated retention
'''

if not USE_EVENT_APPROACH:

    # Upload to file storage
    fileMO = {
        'name': 'my logfile',
        'type': 'logfile'
    }
    multipart = {
        'object': (None, json.dumps(fileMO)),
        'filesize': (None, len(FILE_CONTENT)),
        'file': ('logfile', bytes(FILE_CONTENT, 'utf-8'), 'application/octet-stream')
    }
    client.headers['Content-Type'] = None
    res = client.post(C8Y_BASE + '/inventory/binaries', files=multipart)
    binaryRef = res.json()['self']
    client.headers['Content-Type'] = 'application/json'

    # Update operation
    logfileFragment = logfileOperation['c8y_LogfileRequest']
    logfileFragment['file'] = binaryRef
    updatedOperation = {
        'status': 'SUCCESSFUL',
        'c8y_LogfileRequest': logfileFragment
    }
    client.put(C8Y_BASE + '/devicecontrol/operations/' + logfileOperation['id'], data=json.dumps(updatedOperation))