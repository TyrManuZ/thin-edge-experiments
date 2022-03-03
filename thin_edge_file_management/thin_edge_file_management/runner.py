import paho.mqtt.client as paho
import yaml
import time
import logging
import os
import toml
import requests
import shutil
import json

from logging.handlers import RotatingFileHandler
from .logfile_management import LogfileManager, SUPPORTED_LOGS, OWN_LOG_PATH
from .config_management import ConfigurationFileUploadManager, ConfigurationFileDownloadManager, SUPPORTED_CONFIGURATIONS
from .client import *

DEFAULT_LOG_LEVEL = 'INFO'
DEFAULT_MAX_MEGA_BYTES = 10
DEFAULT_BACKUP_COUNT = 1

CONFIG_FILE = '/etc/thin-edge-file-management/file-management.yml'
SUPPORTED_OPERATIONS = ['c8y_LogfileRequest', 'c8y_UploadConfigFile', 'c8y_DownloadConfigFile']

SET_CONFIG_UPLOAD_EXECUTING_MSG = '501,c8y_UploadConfigFile'
SET_CONFIG_UPLOAD_SUCCESSFUL_MSG = '503,c8y_UploadConfigFile'
SET_CONFIG_UPLOAD_FAILED_MSG = '502,c8y_UploadConfigFile'


class TmpManager():

    def __init__(self, logger):
        self.path = '/tmp/tedge_file_mgmt'
        self.logger = logger
        self.createTmpDir()

    def createTmpDir(self):
        if os.path.exists(self.path):
            self.clearTmpDir()
        else:
            os.makedirs(self.path)

    def getTmpFilePath(self, name):
        timePrefix = str(round(time.time() * 1000))
        return self.path + '/' + timePrefix + name

    def removeFileFromTmp(self, path):
        if os.path.isfile(path):
            os.unlink(path)
        else:
            self.logger.warn('Cannot remove file because not existing: ' + path)

    def clearTmpDir(self):
        for filename in os.listdir(self.path):
            filePath = os.path.join(self.path, filename)
            try:
                if os.path.isfile(filePath) or os.path.islink(filePath):
                    os.unlink(filePath)
                elif os.path.isdir(filePath):
                    shutil.rmtree(filePath)
            except Exception as e:
                self.logger.exception('Error deleting tmp dir')

class FileManager():

    def __init__(self, httpClient, configUploadManager, configDownloadManager, logfileManager, c8yUrl, config, logger):
        self.c8yJWT = None
        self.logger = logger
        self.config = config
        self.c8yUrl = c8yUrl
        self.thinEdgeClient = paho.Client()
        self.thinEdgeClient.on_message = self.onMessageCallback
        self.httpClient = httpClient
        self.configUploadManager = configUploadManager
        self.configDownloadManager = configDownloadManager
        self.logfileManager = logfileManager

    def onMessageCallback(self, client, userdata, msg):
        if msg.topic == C8Y_TOKEN_RECIEVE_TOPIC:
            self.logger.info('New JWT received!')
            payload = msg.payload.decode("utf-8")
            self.c8yJWT = payload[3:]
            self.httpClient.headers.update({'Authorization': 'Bearer ' + self.c8yJWT})
        elif msg.topic == C8Y_DOWNLINK_TOPIC:
            payload = msg.payload.decode("utf-8")
            payloadRows = payload.split('\n\r')
            for row in payloadRows:
                payloadChunks = row.split(',')
                self.logger.debug(row)
                if payloadChunks[0] == '526':
                    self.configUploadManager.queueOperation((payloadChunks[1], payloadChunks[2]))
                elif payloadChunks[0] == '522':
                    self.logfileManager.queueOperation((payloadChunks[1], payloadChunks[2]))
                elif payloadChunks[0] == '524':
                    self.configDownloadManager.queueOperation((payloadChunks[1], payloadChunks[2], payloadChunks[3]))
            self.configUploadManager.handleConfigUploadQueue(client)
            self.logfileManager.handleLogfileUploadQueue(client)
            self.configDownloadManager.handleQueue(client)

    def getNewToken(self):
        self.thinEdgeClient.publish(C8Y_TOKEN_REQUEST_TOPIC, '', 1)

    def updateInventoryFragments(self):
        # Prepare c8y_SupportedOperations
        allSupportedOperations = SUPPORTED_OPERATIONS.copy()
        allSupportedOperations.extend(self.config['thin-edge']['additionalSupportedOps'])
        self.logger.info(allSupportedOperations)
        # Prepare c8y_SupportedConfigurations
        allSupportedConfigurations = SUPPORTED_CONFIGURATIONS.copy()
        allSupportedConfigurations.extend(self.config['config-management']['files'])
        # Prepare c8y_SupportedLogs
        allSupportedLogs = SUPPORTED_LOGS.copy()
        allSupportedLogs.extend(self.config['log-management']['files'])
        messages = [
            '114,' + ','.join(allSupportedOperations),
            '119,' + ','.join(allSupportedConfigurations),
            '118,' + ','.join(allSupportedLogs)
        ]
        self.thinEdgeClient.publish(C8Y_UPLINK_TOPIC, '\n'.join(messages), 1)

    def connect(self):
        self.thinEdgeClient.connect(self.config['thin-edge']['host'], self.config['thin-edge']['port'], 60)
        self.thinEdgeClient.loop_start()
        self.thinEdgeClient.subscribe(C8Y_DOWNLINK_TOPIC, 2)
        self.thinEdgeClient.subscribe(C8Y_TOKEN_RECIEVE_TOPIC, 2)
        self.updateInventoryFragments()
        self.getNewToken()

    def disconnect(self):
        self.thinEdgeClient.disconnect()

class FileChangeAgent():

    def __init__(self, config, logger):
        self.unchangedConfig = True
        self.config = config
        self.logger = logger
        self.thinEdgeFileChangeClient = paho.Client()
        self.thinEdgeFileChangeClient.on_message = self.configChangeCallback

    def configChangeCallback(self, client, userdata, msg):
        message = json.loads(msg.payload.decode("utf-8"))

        if message['changedFile'] == CONFIG_FILE:
            self.unchangedConfig = False

    def run(self):
        self.thinEdgeFileChangeClient.connect(self.config['thin-edge']['host'], self.config['thin-edge']['port'], 60)
        self.thinEdgeFileChangeClient.loop_start()
        # should happen after successful CONNACK
        time.sleep(3)
        self.thinEdgeFileChangeClient.subscribe(BROADCASTING_TOPIC, 2)
        while self.unchangedConfig:
            time.sleep(1)
        self.thinEdgeFileChangeClient.disconnect()

def start():
    while True:
        # load config
        config = yaml.safe_load(open(CONFIG_FILE))
        
        # create logger
        loggingConfigs = config.get(
            'logging',
            {
                'maxMegaBytes': DEFAULT_MAX_MEGA_BYTES,
                'logLevel': DEFAULT_LOG_LEVEL,
                'backupCount': DEFAULT_BACKUP_COUNT
            }
        )
        logLevel = loggingConfigs.get('logLevel', DEFAULT_LOG_LEVEL)
        maxBytes = int(loggingConfigs.get('maxMegaBytes', DEFAULT_MAX_MEGA_BYTES)) * 1024 * 1024
        backupCount = int(loggingConfigs.get('backupCount', DEFAULT_BACKUP_COUNT))  

        # create dir
        logDir = OWN_LOG_PATH[0:OWN_LOG_PATH.rfind('/')]
        if not os.path.exists(logDir):
            os.makedirs(logDir)

        logger = logging.getLogger('file-mgmt-logger')
        logger.setLevel(logging.getLevelName(logLevel))
        fileHandler = RotatingFileHandler(OWN_LOG_PATH, maxBytes=maxBytes, backupCount=backupCount)
        formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
        fileHandler.setFormatter(formatter)
        fileHandler.setLevel(logging.getLevelName(logLevel))
        logger.addHandler(fileHandler)
        # create HTTP client
        httpClient = requests.Session()
        httpClient.headers.update({'Content-Type': 'application/json'})
        httpClient.headers.update({'Accept': 'application/json'})
        # Load url from tedge config
        tedgeConfig = toml.load(config['thin-edge']['config'])
        c8yUrl = 'https://' + tedgeConfig['c8y']['url']

        logger.info('Starting service ...')
        logger.debug('C8Y URL: ' + c8yUrl)
        logfileManager = LogfileManager(httpClient, c8yUrl, logger)
        configUploadManager = ConfigurationFileUploadManager(httpClient, c8yUrl, logger)
        configDownloadManager = ConfigurationFileDownloadManager(httpClient, c8yUrl, logger)

        fm = FileManager(httpClient, configUploadManager, configDownloadManager, logfileManager, c8yUrl, config, logger)
        logger.info('conecting to thin-edge')
        fm.connect()
        fileChangeAgent = FileChangeAgent(config, logger)
        # this call is blocking
        fileChangeAgent.run()
        logger.info('disconecting from thin-edge')
        fm.disconnect()
        fm = None
        fileChangeAgent = None
        logger.removeHandler(fileHandler)
        time.sleep(3)

start()    