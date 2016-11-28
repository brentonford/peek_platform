"""
 *
 *  Copyright Synerty Pty Ltd 2013
 *
 *  This software is proprietary, you are not free to copy
 *  or redistribute this code in any format.
 *
 *  All rights to this software are reserved by 
 *  Synerty Pty Ltd
 *
"""
import json
import logging
import os
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks

from peek_platform import PeekPlatformConfig
from peek_platform.file_config.PeekFileConfigPlatformMixin import \
    PeekFileConfigPlatformMixin
from txhttputil import Directory
from txhttputil import deferToThreadWrap
from txhttputil import rapuiHttpFileDownloader

logger = logging.getLogger(__name__)


class PappSwInstallManagerBase:
    def __init__(self):
        pass

    @inlineCallbacks
    def update(self, pappName, targetVersion):
        logger.info("Updating %s to %s", pappName, targetVersion)

        from peek_platform import PeekPlatformConfig

        url = ('http://%(ip)s:%(port)s/peek_server.sw_install.papp.download?'
               ) % {"ip": PeekPlatformConfig.config.peekServerHost,
                    "port": PeekPlatformConfig.config.peekServerPort}

        args = {"name": pappName}
        if targetVersion:
            args["version"] = str(targetVersion)

        url += urllib.parse.urlencode(args)

        (dir, file) = yield rapuiHttpFileDownloader(url)
        if file.size == 0:
            logger.warning(
                "Peek server doesn't have any updates for agent %s, version %s",
                pappName, targetVersion)
            return

        yield self.installAndReload(pappName, targetVersion, file.realPath)

        defer.returnValue(targetVersion)

    @deferToThreadWrap
    def installAndReload(self, pappName, targetVersion, fullTarPath):

        assert isinstance(PeekPlatformConfig.config, PeekFileConfigPlatformMixin)
        pappVersionJsonFileName = "papp_version.json"

        if not tarfile.is_tarfile(fullTarPath):
            raise Exception("Papp update %s download is not a tar file" % pappName)

        directory = Directory()
        tarfile.open(fullTarPath).extractall(directory.path)
        directory.scan()

        pappVersionJson = [f for f in directory.files if f.name == pappVersionJsonFileName]

        if len(pappVersionJson) != 1:
            raise Exception("Archive does not contain Peek App software"
                            ", Expected 1 %s, got %s"
                            % (pappVersionJsonFileName, len(pappVersionJson)))

        pappVersionJson = pappVersionJson[0]

        with pappVersionJson.open() as f:
            jsonObj = json.load(f)

        jsonVersion = jsonObj['version']
        jsonBuild = jsonObj['buildNumber']

        if jsonVersion != targetVersion:
            raise Exception("Papp %s Target version is %s json version is %s"
                            % (pappName, targetVersion, jsonVersion))

        archiveRootDirName = pappVersionJson.path

        if '/' in archiveRootDirName:
            raise Exception("Papp %s Expected %s to be one level down, it's at %s"
                            % (pappName, pappVersionJsonFileName, archiveRootDirName))

        expectedRootDir = "%s_%s#%s" % (pappName, jsonVersion, jsonBuild)
        if archiveRootDirName != expectedRootDir:
            raise Exception("Papp %s, archive root dir is expected to be %s but its %s"
                            % (pappName, expectedRootDir, archiveRootDirName))

        newPath = os.path.join(PeekPlatformConfig.config.pappSoftwarePath,
                               archiveRootDirName)

        # Move the old version out of the way.
        if os.path.exists(newPath):
            oldPath = tempfile.mkdtemp(dir=PeekPlatformConfig.config.pappSoftwarePath,
                                       prefix=archiveRootDirName)
            shutil.move(newPath, oldPath)

        # Move the new version into place
        shutil.move(os.path.join(directory.path, archiveRootDirName), newPath)

        PeekPlatformConfig.config.setPappVersion(pappName, targetVersion)
        PeekPlatformConfig.config.setPappDir(pappName, newPath)

        ####
        # FIXME : This will always enabled the Papp and overwrite config changes
        PeekPlatformConfig.config.pappsEnabled = list(set(
            PeekPlatformConfig.config.pappsEnabled + [pappName]))

        # RELOAD PAPP
        reactor.callLater(0, self.notifyOfPappVersionUpdate, pappName, targetVersion)

    def notifyOfPappVersionUpdate(self, pappName, targetVersion):
        raise NotImplementedError("notifyOfPappVersionUpdate")
