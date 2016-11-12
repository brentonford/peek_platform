'''
Created on 09/07/2014

@author: synerty
'''

from twisted.internet.defer import Deferred, DeferredList

from peek_platform.sw_install.PeekSwInstallManagerBase import PeekSwInstallManagerBase
from rapui.vortex.Payload import Payload
from rapui.vortex.PayloadEndpoint import PayloadEndpoint

__author__ = 'peek'
import logging

logger = logging.getLogger(__name__)

# -------------------------------------
# Software Update Handler for data from agents

# The filter we listen on
peekPlatformVersionFilt = {
    'papp': 'peak_platform',
    'key': "peek_platform.version.check"}  # LISTEN / SEND


class PeekSwVersionPollHandler(object):
    PEEK_PLATFORM = "peek_platform"

    def __init__(self):
        self._startupDeferred = Deferred()
        self._ep = None

    def start(self):
        self._ep = PayloadEndpoint(peekPlatformVersionFilt, self._process)

        from peek_platform.PeekVortexClient import peekVortexClient
        peekVortexClient.sendPayload(Payload(filt=peekPlatformVersionFilt))

        return self._startupDeferred

    def _process(self, payload, vortexUuid, **kwargs):
        assert not payload.result  # result is None means success

        from peek_platform import PeekPlatformConfig

        platformUpdate = False
        deferredList = []

        for swVersionInfo in payload.tuples:
            if swVersionInfo.name == self.PEEK_PLATFORM:
                if PeekPlatformConfig.config.platformVersion != swVersionInfo.version:
                    logger.info("Recieved platform update new version is %s, we're %s",
                                swVersionInfo.version,
                                PeekPlatformConfig.config.platformVersion)
                    d = PeekSwInstallManagerBase().update(swVersionInfo.version)
                    deferredList.append(d)

                    # Don't process any more, we'll update them when we restart.
                    platformUpdate = True
                    break

            else:
                installedPappVer = PeekPlatformConfig.config.pappVersion(
                    swVersionInfo.name)

                if installedPappVer != swVersionInfo.version:
                    logger.info("Recieved %s update new version is %s, we're %s",
                                swVersionInfo.name,
                                swVersionInfo.version,
                                installedPappVer)

                    d = PeekPlatformConfig.pappSwInstallManager.update(
                        swVersionInfo.name, swVersionInfo.version)
                    deferredList.append(d)

        if not self._startupDeferred:
            return

        if deferredList:
            if platformUpdate:
                self._startupDeferred.errback(
                    Exception("Startup stopped, Platform update and restart"))
            else:
                DeferredList(deferredList).chainDeferred(self._startupDeferred)

        else:
            logger.info("No update required")
            if self._startupDeferred:
                self._startupDeferred.callback(True)

        self._startupDeferred = None


peekSwVersionPollHandler = PeekSwVersionPollHandler()
