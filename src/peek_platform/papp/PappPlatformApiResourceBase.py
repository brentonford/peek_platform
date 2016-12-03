from twisted.web.resource import Resource

from txhttputil.site.BasicResource import BasicResource
from txhttputil.site.FileUnderlayResource import FileUnderlayResource


class PappPlatformApiResourceBase:
    def __init__(self):
        self.__rootResource = FileUnderlayResource()

    def addStaticResourceDir(self, dir: str) -> None:
        self.__rootResource.addFileSystemRoot(dir)

    def addResource(self, pappSubPath: bytes, resource: BasicResource) -> None:
        pappSubPath = pappSubPath.strip(b'/')
        self.__rootResource.putChild(pappSubPath, resource)

    @property
    def rootResource(self) -> BasicResource:
        return self.__rootResource
