import json
import time
import os
import requests

import mimetypes

from datetime import datetime

from .client import C8Y_UPLINK_TOPIC, C8Y_EXTERNAL_ID_TYPE, C8Y_TOKEN_REQUEST_TOPIC

OWN_LOG_PATH = '/var/log/thin-edge-file-management/file-management.log'

SUPPORTED_LOGS = ['/var/log/mosquitto/mosquitto.log', OWN_LOG_PATH]
SET_LOGFILE_UPLOAD_EXECUTING_MSG = '501,c8y_LogfileRequest'
SET_LOGFILE_UPLOAD_SUCCESSFUL_MSG = '503,c8y_LogfileRequest'
SET_LOGFILE_UPLOAD_FAILED_MSG = '502,c8y_LogfileRequest'

class LogfileManager():

    def __init__(self, httpClient, c8yUrl, logger):
        self.c8yUrl = c8yUrl
        self.logger = logger
        self.httpClient = httpClient
        self.logfileUploadQueue = []
        self.thinEdgeClient = None
        
    def handleLogfileUploadQueue(self, client):
        self.thinEdgeClient = client
        continuePrevious = False
        failCounter = 0
        while len(self.logfileUploadQueue) > 0:
            continuePrevious = self.handleOperation(continuePrevious)
            if continuePrevious:
                failCounter += 1
            else:
                failCounter = 0
            if failCounter == 3:
                self.logger.warn('Logfile Upload operation failed 3 times => aborting it')
                continuePrevious = False
                self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_LOGFILE_UPLOAD_FAILED_MSG + ',Execution failed 3 times', 2)
            time.sleep(1)

    def queueOperation(self, operation):
        self.logfileUploadQueue.append(operation)

    def getNewToken(self):
        self.thinEdgeClient.publish(C8Y_TOKEN_REQUEST_TOPIC, '', 1)

    def getDeviceId(self, device):
        res = self.httpClient.get(self.c8yUrl + '/identity/externalIds/' + C8Y_EXTERNAL_ID_TYPE + '/' + device)
        if res.status_code == 401:
            self.getNewToken()
            time.sleep(5)
            return True
        elif res.status_code > 399:
            self.logger.warn('HTTP client ran into error code on calling identities API' + str(res.status_code))
            return True
        # Request worked => get deviceId
        return res.json()['managedObject']['id']

    def createLogfileEvent(self, deviceId, file):
        event = {
            'source': {
                'id': deviceId
            },
            'time': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            'type': 'c8y_Logfile',
            'text': 'Upload logile: ' + file
        }
        res = self.httpClient.post(self.c8yUrl + '/event/events', data=json.dumps(event))
        res.raise_for_status()
        return res.json()['id']

    def attachLogfileToEvent(self, eventId, file):
        if os.access(file, os.R_OK):
            self.logger.debug(file + ' is accessible')
            with open(file, 'rb') as logfile:
                filename = file.split('/')[-1]
                mt = mimetypes.guess_type(filename)
                mt = 'text/plain' if mt[0] == None else mt[0]
                res = self.httpClient.post(self.c8yUrl + '/event/events/' + eventId + '/binaries', data=logfile, headers={'Content-Type': mt, 'Content-Disposition': 'filename="' + filename + '"'})
                res.raise_for_status()
                return res.json()['self']
        else:
            self.logger.warn(file + ' is not accessible')
            raise PermissionError()        

    def handleOperation(self, continuePrevious):
        # Take the first in the queue
        operation = self.logfileUploadQueue[0]
        device = operation[0]
        file = operation[1]
        # Set operation to executing
        if not continuePrevious:
            self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_LOGFILE_UPLOAD_EXECUTING_MSG, 2)
        try:
            # Get C8Y deviceId
            deviceId = self.getDeviceId(device)
            # Create event
            eventId = self.createLogfileEvent(deviceId, file)
            # Upload config file
            fileUrl = self.attachLogfileToEvent(eventId, file)
            # Set successful
            self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_LOGFILE_UPLOAD_SUCCESSFUL_MSG + ',' + fileUrl, 2)
            self.logfileUploadQueue.pop(0)
        except requests.exceptions.HTTPError:
            return True
        except PermissionError as e:
            self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_LOGFILE_UPLOAD_FAILED_MSG + ',File not accessible', 2)
            self.logfileUploadQueue.pop(0)
        except Exception as e:
            self.logger.exception(e)
            self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_LOGFILE_UPLOAD_FAILED_MSG + ',Error occured', 2)
            self.logfileUploadQueue.pop(0)

