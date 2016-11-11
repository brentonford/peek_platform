import imp
import logging
import sys

import os

from peek_platform import PeekPlatformConfig

logger = logging.getLogger(__name__)


class PappLoaderBase():
    _instance = None

    def __new__(cls, *args, **kwargs):
        assert cls._instance is None, "PappServerLoader is a singleton, don't construct it"
        cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._loadedPapps = {}

    def loadPapp(self, pappName):
        raise NotImplementedError("loadPapp")

    def unloadPapp(self, pappName):
        raise NotImplementedError("unloadPapp")

    def listPapps(self):
        def pappTest(name):
            if not name.startswith("papp_"):
                return False
            return os.path.isdir(os.path.join(self._pappPath, name))

        papps = os.listdir(self._pappPath)
        papps = filter(pappTest, papps)
        return papps

    def loadAllPapps(self):
        for pappName in PeekPlatformConfig.config.pappsEnabled:
            self.loadPapp(pappName)

    def unloadAllPapps(self):
        while self._loadedPapps:
            self.unloadPapp(self._loadedPapps.keys()[0])

    def _unloadPappPackage(self, pappName, oldLoadedPapp):

        # Stop and remove the Papp
        del self._loadedPapps[pappName]
        oldLoadedPapp.stop()
        oldLoadedPapp.unload()

        # Unload the packages
        loadedSubmodules = [modName
                            for modName in sys.modules.keys()
                            if modName.startswith('%s.' % pappName)]

        for modName in loadedSubmodules:
            del sys.modules[modName]

        del sys.modules[pappName]

        if sys.getrefcount(oldLoadedPapp) > 2:
            logger.warning("Old references to %s still exist, count = %s",
                           pappName, sys.getrefcount(oldLoadedPapp))
