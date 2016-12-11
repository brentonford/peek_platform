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
import logging
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from os.path import expanduser

from pytmpdir.Directory import Directory
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks
from txhttputil.downloader.HttpFileDownloader import HttpFileDownloader
from txhttputil.util.DeferUtil import deferToThreadWrap

logger = logging.getLogger(__name__)


class PeekSwInstallManagerBase:
    def __init__(self):
        pass

    def notifyOfPlatformVersionUpdate(self, newVersion):
        self.installAndRestart(newVersion)

    @inlineCallbacks
    def update(self, targetVersion):
        logger.info("Updating to %s", targetVersion)

        from peek_platform import PeekPlatformConfig

        url = ('http://%(ip)s:%(port)s/peek_server.sw_install.platform.download?'
               ) % {"ip": PeekPlatformConfig.config.peekServerHost,
                    "port": PeekPlatformConfig.config.peekServerPort}

        args = {"name": PeekPlatformConfig.componentName}
        if targetVersion:
            args["version"] = str(targetVersion)

        url += urllib.parse.urlencode(args)

        file = yield HttpFileDownloader(url).run()
        if file.size == 0:
            logger.warning("Peek server doesn't have any updates for %s, version %s",
                           PeekPlatformConfig.componentName, targetVersion)
            return

        yield self._blockingInstallUpdate(targetVersion, file.name)

        defer.returnValue(targetVersion)

    @inlineCallbacks
    def installAndRestart(self, targetVersion):

        from peek_platform import PeekPlatformConfig

        newSoftwareTar = os.path.join(
            PeekPlatformConfig.config.platformSoftwarePath,
            'peek_platform_%s' % targetVersion,
            '%s_%s.tar.bz2' % (PeekPlatformConfig.componentName, targetVersion))

        yield self._blockingInstallUpdate(targetVersion, newSoftwareTar)

    @deferToThreadWrap
    def _blockingInstallUpdate(self, targetVersion, fullTarPath):

        from peek_platform import PeekPlatformConfig

        if not tarfile.is_tarfile(fullTarPath):
            raise Exception("Platform update download is not a tar file")

        directory = Directory()
        tarfile.open(fullTarPath).extractall(directory.path)
        directory.scan()

        runPycFileName = 'run_%s.pyc' % PeekPlatformConfig.componentName

        runPycFile = [f for f in directory.files if f.name == runPycFileName]
        if len(runPycFile) != 1:
            raise Exception("Uploaded archive does not contain Peek Platform software"
                            ", Expected 1 %s, got %s" % (runPycFileName, len(runPycFile)))
        runPycFile = runPycFile[0]

        if '/' in runPycFile.path:
            raise Exception("Expected %s to be one level down, it's at %s"
                            % (runPycFileName, runPycFile.path))

        home = expanduser("~")
        newPath = os.path.join(home, runPycFile.path)

        import peek_platform
        oldPath = os.path.dirname(os.path.dirname(peek_platform.__file__))

        if os.path.exists(newPath):
            # When running from the IDE, oldPath != newPath, so make sure we don't move
            # the project dir.
            tmpPath = tempfile.mkdtemp(dir=home, prefix=runPycFile.path)
            shutil.move(newPath, tmpPath)

            if newPath == oldPath:
                oldPath = tmpPath

        shutil.move(os.path.join(directory.path, runPycFile.path), newPath)

        self._synlinkTo(PeekPlatformConfig.componentName, home, newPath)

        # Stop the system, and update the code
        try:
            self._stopCode()
            self._updateCode()
        except Exception as e:
            logger.exception(e)

            # If the update failed revert to the old code
            self._synlinkTo(PeekPlatformConfig.componentName, home, oldPath)

            try:
                # And start the system again
                self._startCode()
            except Exception as e:
                logger.exception(e)
                raise
            raise

        PeekPlatformConfig.config.platformVersion = targetVersion

        reactor.callLater(1.0, self.restartProcess)

        return targetVersion

    def _stopCode(self):
        pass

    def _updateCode(self):
        pass

    def _startCode(self):
        pass

    def _synlinkTo(self, componentName, home, newPath):
        symLink = os.path.join(home, componentName)
        try:
            os.remove(symLink)
        except:
            pass
        os.symlink(newPath, symLink)

    def restartProcess(self):
        """Restarts the current program.
        Note: this function does not return. Any cleanup action (like
        saving data) must be done before calling this function."""
        python = sys.executable
        argv = list(sys.argv)
        argv.insert(0, "-u")
        os.execl(python, python, *argv)