import paho.mqtt.client as paho
import os
import json
import time
import mimetypes

from datetime import datetime

from .client import C8Y_UPLINK_TOPIC, C8Y_EXTERNAL_ID_TYPE, C8Y_TOKEN_REQUEST_TOPIC, BROADCASTING_TOPIC

SUPPORTED_CONFIGURATIONS = ['/etc/thin-edge-file-management/file-management.yml']
SET_CONFIG_UPLOAD_EXECUTING_MSG = '501,c8y_UploadConfigFile'
SET_CONFIG_UPLOAD_SUCCESSFUL_MSG = '503,c8y_UploadConfigFile'
SET_CONFIG_UPLOAD_FAILED_MSG = '502,c8y_UploadConfigFile'
SET_CONFIG_DOWNLOAD_EXECUTING_MSG = '501,c8y_DownloadConfigFile'
SET_CONFIG_DOWNLOAD_SUCCESSFUL_MSG = '503,c8y_DownloadConfigFile'
SET_CONFIG_DOWNLOAD_FAILED_MSG = '502,c8y_DownloadConfigFile'

class ConfigurationFileUploadManager():

    def __init__(self, httpClient, c8yUrl, logger):
        self.c8yUrl = c8yUrl
        self.logger = logger
        self.httpClient = httpClient
        self.configUploadQueue = []
        self.thinEdgeClient = None
        
    def handleConfigUploadQueue(self, client):
        self.thinEdgeClient = client
        continuePrevious = False
        failCounter = 0
        while len(self.configUploadQueue) > 0:
            continuePrevious = self.handleOperation(continuePrevious)
            if continuePrevious:
                failCounter += 1
            else:
                failCounter = 0
            if failCounter == 3:
                self.logger.warn('Logfile Upload operation failed 3 times => aborting it')
                continuePrevious = False
                self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_CONFIG_UPLOAD_FAILED_MSG + ',Execution failed 3 times', 2)
                self.configUploadQueue.pop(0)
            time.sleep(1)

    def queueOperation(self, operation):
        self.configUploadQueue.append(operation)

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

    def createConfgiUploadEvent(self, deviceId, file):
        event = {
            'source': {
                'id': deviceId
            },
            'time': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            'type': file,
            'text': 'Upload config: ' + file
        }
        res = self.httpClient.post(self.c8yUrl + '/event/events', data=json.dumps(event))
        if res.status_code == 401:
            self.getNewToken()
            time.sleep(5)
            return True
        elif res.status_code > 399:
            self.logger.warn('HTTP client ran into error code on calling event API' + str(res.status_code))
            return True
        return res.json()['id']

    def attachFileToEvent(self, eventId, file):
        try:
            with open(file, 'rb') as configFile:
                filename = file.split('/')[-1]
                mt = mimetypes.guess_type(filename)
                mt = 'text/plain' if mt[0] == None else mt[0]
                res = self.httpClient.post(self.c8yUrl + '/event/events/' + eventId + '/binaries', data=configFile, headers={'Content-Type': mt, 'Content-Disposition': 'filename="' + filename + '"'})
                if res.status_code == 401:
                    self.getNewToken()
                    time.sleep(5)
                    return True
                elif res.status_code > 399:
                    self.logger.warn('HTTP client ran into error code on calling identities API' + str(res.status_code))
                    return True
        except Exception as e:
            self.logger.exception(e)
            return True

    def hasFileAccess(self, file):
        if os.access(file, os.R_OK):
            return True
        return False

    def handleOperation(self, continuePrevious):
        # Take the first in the queue
        operation = self.configUploadQueue[0]
        device = operation[0]
        file = operation[1]
        # Set operation to executing
        if not continuePrevious:
            self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_CONFIG_UPLOAD_EXECUTING_MSG, 2)
        # Verify file access
        if not self.hasFileAccess(file):
            self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_CONFIG_UPLOAD_FAILED_MSG + ',File not readable', 2)
        # Get C8Y deviceId
        deviceId = self.getDeviceId(device)
        # Create event
        eventId = self.createConfgiUploadEvent(deviceId, file)
        # Upload config file
        self.attachFileToEvent(eventId, file)
        # Set successful
        self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_CONFIG_UPLOAD_SUCCESSFUL_MSG, 2)
        self.configUploadQueue.pop(0)

class ConfigurationFileDownloadManager():

    def __init__(self, httpClient, c8yUrl, logger):
        self.c8yUrl = c8yUrl
        self.logger = logger
        self.httpClient = httpClient
        self.configDownloadQueue = []
        self.thinEdgeClient = None
        
    def handleQueue(self, client):
        self.thinEdgeClient = client
        continuePrevious = False
        failCounter = 0
        while len(self.configDownloadQueue) > 0:
            try:
                continuePrevious = self.handleOperation(continuePrevious)
                if continuePrevious:
                    failCounter += 1
                else:
                    failCounter = 0
            except PermissionError:
                self.logger.exception('Failed on handling config download operation')
                failCounter = 3
            except:
                self.logger.exception('Failed on handling config download operation')
                failCounter += 1
            finally:
                if failCounter == 3:
                    self.logger.warn('Config download operation failed 3 times => aborting it')
                    continuePrevious = False
                    self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_CONFIG_DOWNLOAD_FAILED_MSG + ',Execution failed 3 times', 2)
                    self.configDownloadQueue.pop(0)
                    failCounter = 0
                time.sleep(1)

    def queueOperation(self, operation):
        self.configDownloadQueue.append(operation)

    def getNewToken(self):
        self.thinEdgeClient.publish(C8Y_TOKEN_REQUEST_TOPIC, '', 1)

    def hasFileAccess(self, file):
        if os.access(file, os.W_OK):
            return True
        return False

    def downloadNewConfiguration(self, downloadPath, configPath):
        response = self.httpClient.get(downloadPath)
        with open(configPath, 'wb') as configFile:
            configFile.write(response.content)

    def handleOperation(self, continuePrevious):
        # Take the first in the queue
        operation = self.configDownloadQueue[0]
        device = operation[0]
        downloadPath = operation[1]
        configPath = operation[2]
        # Set operation to executing
        if not continuePrevious:
            self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_CONFIG_DOWNLOAD_EXECUTING_MSG, 2)
        # Write access to file?
        if not self.hasFileAccess(configPath):
            self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_CONFIG_DOWNLOAD_FAILED_MSG + ',File not writable', 2)
        # Download new configuration
        self.downloadNewConfiguration(downloadPath, configPath)
        # Set successful
        self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, SET_CONFIG_DOWNLOAD_SUCCESSFUL_MSG, 2)
        # Broadcast file change
        self.thinEdgeClient.publish(BROADCASTING_TOPIC, json.dumps({ 'changedFile': configPath }), 1)
        self.configDownloadQueue.pop(0)