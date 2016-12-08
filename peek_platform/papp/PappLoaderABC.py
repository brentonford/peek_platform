import imp
import logging
import sys

import os
from abc import ABCMeta, abstractmethod
from collections import defaultdict

from papp_base.PappPackageFileConfig import PappPackageFileConfig
from vortex.Tuple import removeTuplesForTupleNames, registeredTupleNames, \
    tupleForTupleName

from vortex.PayloadIO import PayloadIO

from peek_platform import PeekPlatformConfig

logger = logging.getLogger(__name__)


class PappLoaderABC(metaclass=ABCMeta):
    _instance = None

    def __new__(cls, *args, **kwargs):
        assert cls._instance is None, "PappServerLoader is a singleton, don't construct it"
        cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self):
        self._loadedPapps = {}

        from peek_server.PeekServerConfig import peekServerConfig
        self._pappPath = peekServerConfig.pappSoftwarePath

        self._vortexEndpointInstancesByPappName = defaultdict(list)
        self._vortexTupleNamesByPappName = defaultdict(list)

    def loadPapp(self, pappName):
        try:
            # Make note of the initial registrations for this papp
            endpointInstancesBefore = set(PayloadIO().endpoints)
            tupleNamesBefore = set(registeredTupleNames())

            # Get the location of the PAPP package
            pappRootDir = PeekPlatformConfig.config.pappDir(pappName)
            if not os.path.isdir(pappRootDir): raise NotADirectoryError(pappRootDir)

            # Load up the entry hook details from the papp_package.json
            pappPackageJson = PappPackageFileConfig(pappRootDir)

            # Change the working dir to the PAPP directory
            oldPwd = os.curdir
            os.chdir(pappRootDir)

            self._loadPappThrows(pappName, pappRootDir)

            # Change back to the old dir
            os.chdir(oldPwd)

            # Make note of the final registrations for this papp
            self._vortexEndpointInstancesByPappName[pappName] = list(
                set(PayloadIO().endpoints) - endpointInstancesBefore)

            self._vortexTupleNamesByPappName[pappName] = list(
                set(registeredTupleNames()) - tupleNamesBefore)

            self.sanityCheckServerPapp(pappName)

        except Exception as e:
            logger.error("Failed to load papp %s", pappName)
            logger.exception(e)

    @abstractmethod
    def _loadPappThrows(self, pappName:str):
        pass

    def unloadPapp(self, pappName:str):
        oldLoadedPapp = self._loadedPapps.get(pappName)

        if not oldLoadedPapp:
            return

        # Remove the Papp resource tree
        from peek_server.backend.SiteRootResource import root as serverRootResource
        serverRootResource.deleteChild(pappName.encode())

        # Remove the registered endpoints
        for endpoint in self._vortexEndpointInstancesByPappName[pappName]:
            PayloadIO().remove(endpoint)
        del self._vortexEndpointInstancesByPappName[pappName]

        # Remove the registered tuples
        removeTuplesForTupleNames(self._vortexTupleNamesByPappName[pappName])
        del self._vortexTupleNamesByPappName[pappName]

        self._unloadPappPackage(pappName, oldLoadedPapp)

    def listPapps(self):
        def pappTest(name):
            if not name.startswith("papp_"):
                return False
            return os.path.isdir(os.path.join(self._pappPath, name))

        papps = os.listdir(self._pappPath)
        papps = list(filter(pappTest, papps))
        return papps

    def loadAllPapps(self):
        for pappName in PeekPlatformConfig.config.pappsEnabled:
            self.loadPapp(pappName)

    def unloadAllPapps(self):
        while self._loadedPapps:
            self.unloadPapp(list(self._loadedPapps.keys())[0])

    def _unloadPappPackage(self, pappName, oldLoadedPapp):

        # Stop and remove the Papp
        del self._loadedPapps[pappName]

        try:
            oldLoadedPapp.stop()
            oldLoadedPapp.unload()

        except Exception as e:
            logger.error("An exception occured while unloading papp %s,"
                          " unloading continues" % pappName)
            logger.exception(e)

        # Unload the packages
        loadedSubmodules = [modName
                            for modName in list(sys.modules.keys())
                            if modName.startswith('%s.' % pappName)]

        for modName in loadedSubmodules:
            del sys.modules[modName]

        if pappName in sys.modules:
            del sys.modules[pappName]

        # pypy doesn't have getrefcount
        if hasattr(sys, "getrefcount") and sys.getrefcount(oldLoadedPapp) > 2:
            logger.warning("Old references to %s still exist, count = %s",
                           pappName, sys.getrefcount(oldLoadedPapp))

    def sanityCheckServerPapp(self, pappName):
        ''' Sanity Check Papp

        This method ensures that all the things registed for this papp are
        prefixed by it's pappName, EG papp_noop
        '''

        # All endpoint filters must have the 'papp' : 'papp_name' in them
        for endpoint in self._vortexEndpointInstancesByPappName[pappName]:
            filt = endpoint.filt
            if 'papp' not in filt and filt['papp'] != pappName:
                raise Exception("Payload endpoint does not contan 'papp':'%s'\n%s"
                                % (pappName, filt))

        # all tuple names must start with their pappName
        for tupleName in self._vortexTupleNamesByPappName[pappName]:
            TupleCls = tupleForTupleName(tupleName)
            if not tupleName.startswith(pappName):
                raise Exception("Tuple name does not start with '%s', %s (%s)"
                                % (pappName, tupleName, TupleCls.__name__))

    def notifyOfPappVersionUpdate(self, pappName, pappVersion):
        logger.info("Received PAPP update for %s version %s", pappName, pappVersion)
        return self.loadPapp(pappName)
