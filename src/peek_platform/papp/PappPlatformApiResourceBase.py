from rapui.site.RapuiStaticResources import RapuiStaticResources
from rapui.site.RootResource import callResourceCreators, RootResource


class PappPlatformApiResourceBase:
    def __init__(self):
        self.__staticResources = RapuiStaticResources()
        self.__resourceCreators = {}

    def addStaticResourceDir(self, dir):
        self.__staticResources.addStaticResourceDir(dir)

    def addResourceCreator(self, pappSubPath, resourceCreatorFunc):
        pappSubPath = pappSubPath.strip('/')
        assert pappSubPath not in resourceCreatorFunc
        self.__resourceCreators[pappSubPath] = resourceCreatorFunc

    def __createPappRootResource(self, userAccess):
        pappRoot = RootResource(userAccess)
        self.__staticResources.addToResource(pappRoot, userAccess)

        callResourceCreators(self.__resourceCreators, pappRoot, userAccess)

        return pappRoot
