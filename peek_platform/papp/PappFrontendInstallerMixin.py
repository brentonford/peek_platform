import logging
import os
import subprocess
from collections import namedtuple

from papp_base.PappPackageFileConfig import PappPackageFileConfig
from peek_platform.file_config.PeekFileConfigFrontendDirMixin import \
    PeekFileConfigFrontendDirMixin

logger = logging.getLogger(__name__)

PappDetail = namedtuple("PappDetail",
                        ["pappRootDir", "pappName", "angularFrontendDir",
                         "angularMainModule"])


class PappFrontendBuilderMixin(object):
    """ Peek App Frontend Installer Mixin

    This class is used for the client and server.

    This class contains the logic for:
     * Linking in the frontend angular components to the frontend project
     * Compiling the frontend project

    and

    """

    def __init__(self, platformService: str):
        assert platformService in ("server", "client")
        self._platformService = platformService

        from peek_platform.papp.PappLoaderABC import PappLoaderABC
        assert isinstance(self, PappLoaderABC)

        from peek_platform import PeekPlatformConfig
        if not isinstance(PeekPlatformConfig.config, PeekFileConfigFrontendDirMixin):
            raise Exception("The file config must inherit the"
                            " PeekFileConfigFrontendDirMixin")

    def buildFrontend(self) -> None:
        from peek_platform import PeekPlatformConfig
        feSrcDir = PeekPlatformConfig.config.feSrcDir

        pappDetails = self._loadPappConfigs()

        self._writePappRouteLazyLoads(feSrcDir, pappDetails)
        self._relinkPappDirs(feSrcDir, pappDetails)
        self._compileFrontend(feSrcDir)

    def _loadPappConfigs(self) -> [PappDetail]:
        pappDetails = []

        for papp in self._loadedPapps.values():
            pappPackageConfig = papp.config
            assert isinstance(pappPackageConfig, PappPackageFileConfig)

            serviceSection = pappPackageConfig[self._platformService]

            pappDetails.append(
                PappDetail(pappRootDir=papp.pappRootDir,
                           pappName=pappPackageConfig.papp.pappName,
                           angularFrontendDir=serviceSection.angularFrontendDir,
                           angularMainModule=serviceSection.angularMainModule)
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
        with open(pappRoutesTs, 'wa') as fobj:
            fobj.write("export const pappRoutes = [\n")
            fobj.write(",\n".join(routes))
            fobj.write("];\n")

    def _relinkPappDirs(self, feSrcDir: str, pappDetails: [PappDetail]) -> None:
        # Remove all the old symlinks

        for item in os.listdir(feSrcDir):
            path = os.path.join(feSrcDir, path)
            if item.startswith("papp_") and os.path.islink(path):
                os.remove(path)

        for pappDetail in pappDetails:
            srcDir = os.path.join(pappDetail.pappRootDir,
                                           pappDetail.angularFrontendDir)
            linkPath = os.path.join(feSrcDir, pappDetail.pappName)
            os.symlink(srcDir, linkPath, target_is_directory=True)

    def _compileFrontend(self, feSrcDir: str) -> None:
        """ Compile the frontend

        this runs `ng build`
        """

        completedProcess = subprocess.run(["ng", "build"], stdout=subprocess.PIPE)
        if completedProcess.returncode:
            logger.debug(completedProcess.stdout)
        else:
            logger.error(completedProcess.stdout)
            raise Exception("The angular frontend failed to build.")
