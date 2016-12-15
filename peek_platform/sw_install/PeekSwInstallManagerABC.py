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
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from abc import ABCMeta
from typing import Optional

import pip
from pytmpdir.Directory import Directory
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks
from txhttputil.downloader.HttpFileDownloader import HttpFileDownloader
from txhttputil.util.DeferUtil import deferToThreadWrap

logger = logging.getLogger(__name__)

PEEK_PLATFORM_STAMP_FILE = 'version'
"""Peek Platform Stamp File, The file within the release that conatins the version"""


class PeekSwInstallManagerABC(metaclass=ABCMeta):
    """ Peek Software Install Manager ABC

    This class handles downloading the latest platform update from the server service
    installing it and then restarting this service.

    """

    def __init__(self):
        pass

    @classmethod
    def makeReleaseFileName(cls, version: str) -> str:
        """ Make Release File Name

        This method creates an absolute path/filename for a peek release given it's
        stamp/version

        :param version: The stamp/version of the release
        :return: The absolute filename of the peek-release tar file
        """

        from peek_platform import PeekPlatformConfig

        return os.path.join(
            PeekPlatformConfig.config.platformSoftwarePath,
            'peek-release-%s.tar.gz' % version)

    @classmethod
    def makePipArgs(cls, directory: Directory) -> [str]:
        """ Make PIP Args

        This method creates the install arg list for pip, it's used both when testing
        when a new platform release is uploaded and the install on each service.

        :param directory: The directory where the peek-release is extracted to
        :return: The list of arguments to pass to pip
        """

        # Create an array of the package paths
        absFilePaths = [f.realPath
                        for f in directory.files
                        if f.name.endswith(".tar.gz")]

        # Createand return the pip args
        return ['install',  # Install the packages
                '--force-reinstall',  # Reinstall if they already exist
                '--no-cache-dir',  # Don't use the local pip cache
                '--no-index',  # Work offline, don't use pypi
                '--find-links', directory.path,
                # Look in the directory for dependencies
                ] + absFilePaths

    def notifyOfPlatformVersionUpdate(self, newVersion):
        self.installAndRestart(newVersion)

    @inlineCallbacks
    def update(self, targetVersion) -> Optional[str]:
        """ Update

        This method is called when this service detects that the peek server has a newer
        version of software than this service.

        :param targetVersion: The target version to update to
        :return: The version that was updated to, or None if it failed
        """
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
    def installAndRestart(self, targetVersion: str) -> None:
        newSoftwareTar = self.makeReleaseFileName(targetVersion)

        yield self._blockingInstallUpdate(targetVersion, newSoftwareTar)

    @deferToThreadWrap
    def _blockingInstallUpdate(self, targetVersion: str, fullTarPath: str) -> str:
        """ Install Update (Blocking)

        This method installs the packages in the latest peek-release.
        It then calls self.restartProcess to restart the service

        :param targetVersion: The version we should be updating to.
        :param fullTarPath: The path to the peek-release to install
        :return: The version that was installed, (from the file in the release)
        """

        from peek_platform import PeekPlatformConfig

        if not tarfile.is_tarfile(fullTarPath):
            raise Exception("Platform update download is not a tar file")

        directory = Directory()
        tarfile.open(fullTarPath).extractall(directory.path)
        directory.scan()

        stampFile = directory.getFile(name=PEEK_PLATFORM_STAMP_FILE)
        if not stampFile:
            raise Exception("Peek release %s doesn't contain version stamp file %s"
                            % (fullTarPath, PEEK_PLATFORM_STAMP_FILE))

        with stampFile.open() as f:
            stampVersion = f.read().strip()

        if stampVersion != targetVersion:
            raise Exception("Stamp file version %s doesn't match target version %s"
                            % (stampVersion, targetVersion))

        pip.utils.logging._log_state.indentation = 0
        pip.main(self.makePipArgs(directory))

        PeekPlatformConfig.config.platformVersion = targetVersion

        reactor.callLater(1.0, self.restartProcess)

        return targetVersion

    # @abstractmethod
    # def _stopCode(self) -> None:
    #     """ Stop Code
    #
    #     This method should stop the running code, mainly timers and processing queues.
    #     Possibly web servers that may call database updates.
    #
    #     """
    #
    # @abstractmethod
    # def _updateCode(self):
    #     """ Update Code
    #
    #     This method is called to update any data, such as a database migration (typically)
    #     """
    #
    # @abstractmethod
    # def _startCode(self):
    #     """ Start Code
    #
    #     This is called when the update fails, the service should start back up and run as
    #     it did before the update.
    #
    #     """

    # def _synlinkTo(self, componentName, home, newPath):
    #     symLink = os.path.join(home, componentName)
    #     try:
    #         os.remove(symLink)
    #     except:
    #         pass
    #     os.symlink(newPath, symLink)

    def restartProcess(self):
        """Restarts the current program.
        Note: this function does not return. Any cleanup action (like
        saving data) must be done before calling this function."""
        python = sys.executable
        argv = list(sys.argv)
        argv.insert(0, "-u")
        os.execl(python, python, *argv)
