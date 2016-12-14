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

from pytmpdir.Directory import Directory
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks

from peek_platform import PeekPlatformConfig
from peek_platform.file_config.PeekFileConfigPlatformMixin import \
    PeekFileConfigPlatformMixin
from txhttputil.downloader.HttpFileDownloader import HttpFileDownloader
from vortex.Payload import deferToThreadWrap

logger = logging.getLogger(__name__)


class PluginSwInstallManagerBase:
    def __init__(self):
        pass

    @inlineCallbacks
    def update(self, pluginName, targetVersion):
        logger.info("Updating %s to %s", pluginName, targetVersion)

        from peek_platform import PeekPlatformConfig

        url = ('http://%(ip)s:%(port)s/peek_server.sw_install.plugin.download?'
               ) % {"ip": PeekPlatformConfig.config.peekServerHost,
                    "port": PeekPlatformConfig.config.peekServerPort}

        args = {"name": pluginName}
        if targetVersion:
            args["version"] = str(targetVersion)

        url += urllib.parse.urlencode(args)

        file = yield HttpFileDownloader(url).run()
        if file.size == 0:
            logger.warning(
                "Peek server doesn't have any updates for agent %s, version %s",
                pluginName, targetVersion)
            return

        yield self.installAndReload(pluginName, targetVersion, file.realPath)

        defer.returnValue(targetVersion)

    @deferToThreadWrap
    def installAndReload(self, pluginName, targetVersion, fullTarPath):

        assert isinstance(PeekPlatformConfig.config, PeekFileConfigPlatformMixin)
        pluginVersionJsonFileName = "plugin_version.json"

        if not tarfile.is_tarfile(fullTarPath):
            raise Exception("Plugin update %s download is not a tar file" % pluginName)

        directory = Directory()
        tarfile.open(fullTarPath).extractall(directory.path)
        directory.scan()

        pluginVersionJson = [f for f in directory.files if f.name == pluginVersionJsonFileName]

        if len(pluginVersionJson) != 1:
            raise Exception("Archive does not contain Peek App software"
                            ", Expected 1 %s, got %s"
                            % (pluginVersionJsonFileName, len(pluginVersionJson)))

        pluginVersionJson = pluginVersionJson[0]

        with pluginVersionJson.open() as f:
            jsonObj = json.load(f)

        jsonVersion = jsonObj['version']
        jsonBuild = jsonObj['buildNumber']

        if jsonVersion != targetVersion:
            raise Exception("Plugin %s Target version is %s json version is %s"
                            % (pluginName, targetVersion, jsonVersion))

        archiveRootDirName = pluginVersionJson.path

        if '/' in archiveRootDirName:
            raise Exception("Plugin %s Expected %s to be one level down, it's at %s"
                            % (pluginName, pluginVersionJsonFileName, archiveRootDirName))

        expectedRootDir = "%s_%s#%s" % (pluginName, jsonVersion, jsonBuild)
        if archiveRootDirName != expectedRootDir:
            raise Exception("Plugin %s, archive root dir is expected to be %s but its %s"
                            % (pluginName, expectedRootDir, archiveRootDirName))

        newPath = os.path.join(PeekPlatformConfig.config.pluginSoftwarePath,
                               archiveRootDirName)

        # Move the old version out of the way.
        if os.path.exists(newPath):
            oldPath = tempfile.mkdtemp(dir=PeekPlatformConfig.config.pluginSoftwarePath,
                                       prefix=archiveRootDirName)
            shutil.move(newPath, oldPath)

        # Move the new version into place
        shutil.move(os.path.join(directory.path, archiveRootDirName), newPath)

        PeekPlatformConfig.config.setPluginVersion(pluginName, targetVersion)
        PeekPlatformConfig.config.setPluginDir(pluginName, newPath)

        ####
        # FIXME : This will always enabled the Plugin and overwrite config changes
        PeekPlatformConfig.config.pluginsEnabled = list(set(
            PeekPlatformConfig.config.pluginsEnabled + [pluginName]))

        # RELOAD PLUGIN
        reactor.callLater(0, self.notifyOfPluginVersionUpdate, pluginName, targetVersion)

    def notifyOfPluginVersionUpdate(self, pluginName, targetVersion):
        raise NotImplementedError("notifyOfPluginVersionUpdate")
