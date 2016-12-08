import logging

from vortex.VortexClient import VortexClient

logger = logging.getLogger(__name__)


class PeekVortexClient:
    __instance = None

    def __new__(cls):
        if cls.__instance is not None:
            return cls.__instance

        self = super(PeekVortexClient, cls).__new__(cls)
        cls.__instance = self
        return self

    def __init__(self):
        self._vortexClient = VortexClient()

    def connect(self):
        from peek_platform import PeekPlatformConfig
        serverPort = PeekPlatformConfig.config.peekServerPort
        serverHost = PeekPlatformConfig.config.peekServerHost

        logger.info('Connecting to Peek Server %s:%s', serverHost, serverPort)
        return self._vortexClient.connect(serverHost, serverPort)

    def disconnect(self):
        self._vortexClient.disconnect()

    def addReconnectPayload(self, vortexMsg):
        return self._vortexClient.addReconnectPayload(vortexMsg)

    def sendPayload(self, payload):
        vortexMsg = payload.toVortexMsg()
        return self.sendVortexMsg(vortexMsg)

    def sendVortexMsg(self, vortexMsg):
        return self._vortexClient.sendVortexMsg(vortexMsg)


peekVortexClient = PeekVortexClient()
