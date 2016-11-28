from txhttputil.site.StaticFileMultiPath import RapuiStaticResources
from twisted.web.resource import Resource

from txhttputil.site.RootResource import callResourceCreators, RootResource


class PappPlatformApiResourceBase:
    def __init__(self):
        self.__staticResources = RapuiStaticResources()
        self.__resourceCreators = {}

    def addStaticResourceDir(self, dir) -> None:
        self.__staticResources.addStaticResourceDir(dir)

    def addResourceCreator(self, pappSubPath, resourceCreatorFunc) -> None:
        pappSubPath = pappSubPath.strip('/')
        assert pappSubPath not in resourceCreatorFunc
        self.__resourceCreators[pappSubPath] = resourceCreatorFunc

    def __createPappRootResource(self, userAccess) -> Resource:
        pappRoot = RootResource(userAccess)
        self.__staticResources.addToResource(pappRoot, userAccess)

        callResourceCreators(self.__resourceCreators, pappRoot, userAccess)

        return pappRoot
