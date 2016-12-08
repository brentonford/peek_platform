import logging

import os
from abc import ABCMeta

from jsoncfg.value_mappers import require_string, RequireType, require_list
from peek_platform.file_config.PeekFileConfigABC import PeekFileConfigABC

logger = logging.getLogger(__name__)


class PeekFileConfigPlatformMixin:
    # --- Platform Logging

    @property
    def loggingLevel(self):
        with self._cfg as c:
            lvl = c.logging.level.installed("INFO", require_string)
            if lvl in logging._nameToLevel:
                return lvl

            logger.warn("Logging level %s is not valid, defauling to INFO", lvl)
            return "INFO"

    # --- Platform Tmp Path
    @property
    def tmpPath(self):
        default = os.path.join(self._homePath, 'tmp')
        with self._cfg as c:
            return self._chkDir(c.disk.tmp(default, require_string))

    # --- Platform Software Path
    @property
    def platformSoftwarePath(self):
        default = os.path.join(self._homePath, 'platform_software')
        with self._cfg as c:
            return self._chkDir(c.platform.softwarePath(default, require_string))

    # --- Platform Version
    @property
    def platformVersion(self):
        with self._cfg as c:
            return c.platform.version('0.0.0', require_string)

    @platformVersion.setter
    def platformVersion(self, value):
        with self._cfg as c:
            c.platform.version = value

    # --- Papp Software Path
    @property
    def pappSoftwarePath(self):
        default = os.path.join(self._homePath, 'papp_software')
        with self._cfg as c:
            return self._chkDir(c.papp.softwarePath(default, require_string))

    # --- Papp Install Dir
    def pappDir(self, pappName):
        with self._cfg as c:
            return c.papp[pappName].dir(None, RequireType(type(None), str))

    def setPappDir(self, pappName, dir):
        with self._cfg as c:
            c.papp[pappName].dir = dir

    # --- Papp Software Version
    def pappVersion(self, pappName):
        with self._cfg as c:
            return c.papp[pappName].version(None, RequireType(type(None), str))

    def setPappVersion(self, pappName, version):
        with self._cfg as c:
            c.papp[pappName].version = version

    # --- Papps Installed
    @property
    def pappsEnabled(self):
        with self._cfg as c:
            return c.papp.enabled([], require_list)

    @pappsEnabled.setter
    def pappsEnabled(self, value):
        with self._cfg as c:
            c.papp.enabled = value
