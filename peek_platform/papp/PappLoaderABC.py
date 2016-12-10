import logging
import os
import sys
from abc import ABCMeta, abstractmethod, abstractproperty
from collections import defaultdict
from importlib.util import find_spec
from typing import Type

from jsoncfg.value_mappers import require_string, require_array
from papp_base.PappCommonEntryHookABC import PappCommonEntryHookABC
from papp_base.PappPackageFileConfig import PappPackageFileConfig
from peek_platform import PeekPlatformConfig
from vortex.PayloadIO import PayloadIO
from vortex.Tuple import removeTuplesForTupleNames, registeredTupleNames, \
    tupleForTupleName

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

    @abstractproperty
    def _entryHookFuncName(self) -> str:
        """ Entry Hook Func Name.
        Protected property
        :return: EG  "peekServerEntryHook"

        """

    @abstractproperty
    def _entryHookClassType(self):
        """ Entry Hook Class Type
        Protected property
        :return: EG  PappServerEntryHookABC

        """

    @abstractproperty
    def _platformServiceNames(self) -> [str]:
        """ Platform Service Name
        Protected property
        :return: one or more of "server", "worker", "agent", "client", "storage"

        """

    def loadPapp(self, pappName):
        try:
            self.unloadPapp(pappName)

            # Make note of the initial registrations for this papp
            endpointInstancesBefore = set(PayloadIO().endpoints)
            tupleNamesBefore = set(registeredTupleNames())

            modSpec = find_spec(pappName)
            if not modSpec:
                raise Exception("Can not load Peek App package %s", pappName)

            PappPackage = modSpec.loader.load_module()
            pappRootDir = os.path.dirname(PappPackage.__file__)

            # Load up the papp package info
            pappPackageJson = PappPackageFileConfig(pappRootDir)
            pappVersion = pappPackageJson.config.papp.version(require_string)
            pappRequiresService = pappPackageJson.config.requiresServices(require_array)

            # Make sure the service is required
            # Storage and Server are loaded at the same time, hence the intersection
            if not set(pappRequiresService) & set(self._platformServiceNames):
                logger.debug("%s does not require %s, Skipping load",
                             pappName, self._platformServiceNames)
                return

            # Get the entry hook class from the package
            entryHookGetter = getattr(PappPackage, str(self._entryHookFuncName))
            EntryHookClass = entryHookGetter() if entryHookGetter else None

            if not EntryHookClass:
                logger.warning(
                    "Skipping load for %s, %s.%s is missing or returned None",
                    pappName, pappName, self._entryHookFuncName)
                return

            if not issubclass(EntryHookClass, self._entryHookClassType):
                raise Exception("%s load error, Excpected %s, received %s"
                                % (pappName, self._entryHookClassType, EntryHookClass))

            ### Perform the loading of the papp
            self._loadPappThrows(pappName, EntryHookClass, pappRootDir)

            # Make sure the version we have recorded is correct
            PeekPlatformConfig.config.setPappVersion(pappName, pappVersion)

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
    def _loadPappThrows(self, pappName: str, EntryHookClass: Type[PappCommonEntryHookABC],
                        pappRootDir: str) -> None:
        """ Load Papp (May throw Exception)

        This method is called to perform the load of the module.

        :param pappName: The name of the Peek App, eg "papp_noop"
        :param PappPackage: A reference to the main papp package, eg "import papp_noop"
        this parameter would be papp_noop.
        :param pappRootDir: The directory of the papp package,
         EG dirname(papp_noop.__file__)

        """

    def unloadPapp(self, pappName: str):
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
