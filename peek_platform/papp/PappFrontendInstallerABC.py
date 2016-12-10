import logging
import os
import pty
import subprocess
from collections import namedtuple

import sys
from subprocess import PIPE

from pytmpdir.DirectoryTest import isWindows

from jsoncfg.value_mappers import require_string
from papp_base.PappPackageFileConfig import PappPackageFileConfig
from peek_platform import PeekPlatformConfig
from peek_platform.file_config.PeekFileConfigFrontendDirMixin import \
    PeekFileConfigFrontendDirMixin
from peek_platform.file_config.PeekFileConfigOsMixin import PeekFileConfigOsMixin

logger = logging.getLogger(__name__)

PappDetail = namedtuple("PappDetail",
                        ["pappRootDir", "pappName", "angularFrontendDir",
                         "angularMainModule"])

isWindows

class _PtyOutParser:
    """ PTY Out Parser

    The node tools require a tty, so we run it with

        parser = _PtyOutParser()
        import pty
        pty.spawn(*args, parser.read)

    The only problem being that the output is sent to stdout, to solve this we intercept
    the output, return a . for every read, which it sends to stdout, and then only log
    the summary at the end of the webpack build.

    """
    def __init__(self):
        self.data = ''
        self.startLogging = False # Ignore all the stuff before the final summary

    def read(self, fd):
        data = os.read(fd, 1024)
        self.data += data.decode()
        self.splitData()

        # Silence all the output
        if len(data):
            return b'.'

        # If there is no output, return the EOF data
        return data

    def splitData(self):
        lines = self.data.splitlines(True)
        lines.reverse()
        while lines:
            line = lines.pop()
            if not line.endswith(os.linesep):
                self.data = line
                break
            self.logData(line.strip(os.linesep))

    def logData(self, line):
        self.startLogging = self.startLogging or line.startswith("Hash: ")
        if not (line and self.startLogging):
            return

        logger.debug(line)

class PappFrontendInstallerABC(object):
    """ Peek App Frontend Installer Mixin

    This class is used for the client and server.

    This class contains the logic for:
     * Linking in the frontend angular components to the frontend project
     * Compiling the frontend project

    :TODO: Use find/sort to generate a string of the files when this was last run.
    Only run it again if anything has changed.

    """

    def __init__(self, platformService: str):
        assert platformService in ("server", "client")
        self._platformService = platformService

    def buildFrontend(self) -> None:

        from peek_platform.papp.PappLoaderABC import PappLoaderABC
        assert isinstance(self, PappLoaderABC)

        from peek_platform import PeekPlatformConfig
        if not isinstance(PeekPlatformConfig.config, PeekFileConfigFrontendDirMixin):
            raise Exception("The file config must inherit the"
                            " PeekFileConfigFrontendDirMixin")

        from peek_platform import PeekPlatformConfig
        if not isinstance(PeekPlatformConfig.config, PeekFileConfigOsMixin):
            raise Exception("The file config must inherit the"
                            " PeekFileConfigOsMixin")

        from peek_platform import PeekPlatformConfig
        feSrcDir = PeekPlatformConfig.config.feSrcDir

        pappDetails = self._loadPappConfigs()

        self._writePappRouteLazyLoads(feSrcDir, pappDetails)
        self._relinkPappDirs(feSrcDir, pappDetails)
        self._compileFrontend(feSrcDir)

    def _loadPappConfigs(self) -> [PappDetail]:
        pappDetails = []

        for papp in self._loadedPapps.values():
            assert isinstance(papp.packageCfg, PappPackageFileConfig)
            pappPackageConfig = papp.packageCfg.config

            angularFrontendDir = (pappPackageConfig[self._platformService]
                                  .angularFrontendDir(require_string))

            angularMainModule = (pappPackageConfig[self._platformService]
                                 .angularMainModule(require_string))

            pappDetails.append(
                PappDetail(pappRootDir=papp.rootDir,
                           pappName=papp.name,
                           angularFrontendDir=angularFrontendDir,
                           angularMainModule=angularMainModule)
            )

        return pappDetails

    def _writePappRouteLazyLoads(self, feSrcDir: str, pappDetails: [PappDetail]) -> None:
        """
        export const pappRoutes = [
            {
                path: 'papp_noop',
                loadChildren: "papp-noop/papp-noop.module#default"
            }
        ];
        """
        routes = []
        for pappDetail in pappDetails:
            routes.append(
                """
                {
                    path: '%s',
                    loadChildren: "%s/%s#default"
                }
                """ % (pappDetail.pappName,
                       pappDetail.pappName,
                       pappDetail.angularMainModule))

        pappRoutesTs = os.path.join(feSrcDir, 'PappRoutes.ts')

        routeData = "// This file is auto generated, the git version is blank and .gitignored\n"
        routeData += "export const pappRoutes = [\n"
        routeData += ",\n".join(routes)
        routeData += "];\n"

        # Since writing the file again changes the date/time,
        # this messes with the self._recompileRequiredCheck
        with open(pappRoutesTs, 'r') as f:
            if routeData == f.read():
                logger.debug("PappRoutes.ts is up to date")
                return

        logger.debug("Writing new PappRoutes.ts")
        with open(pappRoutesTs, 'w') as f:
            f.write(routeData)

    def _relinkPappDirs(self, feSrcDir: str, pappDetails: [PappDetail]) -> None:
        # Remove all the old symlinks

        for item in os.listdir(feSrcDir):
            path = os.path.join(feSrcDir, item)
            if item.startswith("papp_") and os.path.islink(path):
                os.remove(path)

        for pappDetail in pappDetails:
            srcDir = os.path.join(pappDetail.pappRootDir,
                                  pappDetail.angularFrontendDir)
            linkPath = os.path.join(feSrcDir, pappDetail.pappName)
            os.symlink(srcDir, linkPath, target_is_directory=True)

    def _recompileRequiredCheck(self, feSrcDir: str) -> bool:
        """ Recompile Check

        This command lists the details of the source dir to see if a recompile is needed

        The find command outputs the following

        543101    0 -rw-r--r--   1 peek     sudo            0 Nov 29 17:27 ./src/app/environment/environment.component.css
        543403    4 drwxr-xr-x   2 peek     sudo         4096 Dec  2 17:37 ./src/app/environment/env-worker
        543446    4 -rw-r--r--   1 peek     sudo         1531 Dec  2 17:37 ./src/app/environment/env-worker/env-worker.component.html

        """
        ignore = (".git", ".idea", "dist")
        ignore = ["'%s'" % i for i in ignore] # Surround with quotes
        grep = "grep -v -e %s " % ' -e '.join(ignore) # Xreate the grep command
        cmd = "find -L %s -ls | %s" % (feSrcDir, grep)
        commandComplete = subprocess.run(cmd,
                                         executable=PeekPlatformConfig.config.bashLocation,
                                         stdout=PIPE, stderr=PIPE, shell=True)

        if commandComplete.returncode:
            for line in commandComplete.stdout.splitlines():
                logger.error(line)
            for line in commandComplete.stderr.splitlines():
                logger.error(line)
            raise Exception("Frontend compile diff check failed")

        logger.debug("Frontend compile diff check ran ok")

        lastHash = commandComplete.stdout
        hashFileName = os.path.join(feSrcDir, ".lastHash")

        if os.path.isfile(hashFileName):
            with open(hashFileName, 'rb') as f:
                if f.read() == lastHash:
                    return False

        with open(hashFileName, 'wb') as f:
            f.write(lastHash)

        return True


    def _compileFrontend(self, feSrcDir: str) -> None:
        """ Compile the frontend

        this runs `ng build`
        """

        if not self._recompileRequiredCheck(feSrcDir):
            logger.info("Frondend has not changed, recompile not required.")
            return

        logger.info("Rebuilding frontend distribution")

        parser = _PtyOutParser()

        returnCode = pty.spawn(["bash", "-l", "-c", "cd %s && ng build" % feSrcDir],
                               parser.read)

        if returnCode:
            raise Exception("The angular frontend failed to build.")
        else:
            logger.info("Frontend distribution rebuild complete.")

