'''
Created on 09/07/2014

@author: synerty
'''
import logging

from peek_platform.PeekVortexClient import peekVortexClient
from rapui.vortex.Payload import Payload
from rapui.vortex.PayloadEndpoint import PayloadEndpoint

__author__ = 'peek'

logger = logging.getLogger(__name__)

# The filter we listen on
agentEchoFilt = {
    'papp' : 'peek_platform',
    'key': "peek_platform.echo"
}  # LISTEN / SEND


class PeekServerRestartWatchHandler(object):
    def __init__(self):
        self._ep = PayloadEndpoint(agentEchoFilt, self._process)
        self._lastPeekServerVortexUuid = None

        # When the vortex reconnects, this will make the server echo back to us.
        peekVortexClient.addReconnectPayload(Payload(filt=agentEchoFilt))

    def _process(self, payload, vortexUuid, **kwargs):
        if self._lastPeekServerVortexUuid is None:
            self._lastPeekServerVortexUuid = vortexUuid
            return

        if self._lastPeekServerVortexUuid == vortexUuid:
            return

        logger.info("Peek Server restart detected, restarting agent")
        from peek_platform.sw_update_client.PeekSwUpdateManager import PeekSwUpdateManager
        PeekSwUpdateManager.restartProcess()


__peekServerRestartWatchHandler = PeekServerRestartWatchHandler()
