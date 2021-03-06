import logging

import os
from abc import ABCMeta, abstractproperty
from typing import Optional

from jsoncfg.value_mappers import require_string, RequireType, require_list
from peek_platform.file_config.PeekFileConfigABC import PeekFileConfigABC

logger = logging.getLogger(__name__)


class PeekFileConfigPlatformMixin(metaclass=ABCMeta):
    # --- Platform Logging

    @property
    def loggingLevel(self):
        with self._cfg as c:
            lvl = c.logging.level.installed("INFO", require_string)
            if lvl in logging._nameToLevel:
                return lvl

            logger.warning("Logging level %s is not valid, defauling to INFO", lvl)
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

    # --- Plugin Software Path
    @property
    def pluginSoftwarePath(self):
        default = os.path.join(self._homePath, 'plugin_software')
        with self._cfg as c:
            return self._chkDir(c.plugin.softwarePath(default, require_string))

    # --- Plugin Software Version
    def pluginVersion(self, pluginName):
        """ Plugin Version

        The last version that we know about
        """
        with self._cfg as c:
            return c.plugin[pluginName].version(None, RequireType(type(None), str))

    def setPluginVersion(self, pluginName, version):
        with self._cfg as c:
            c.plugin[pluginName].version = version

    # --- Plugins Installed
    @property
    def pluginsEnabled(self):
        with self._cfg as c:
            return c.plugin.enabled([], require_list)

    @pluginsEnabled.setter
    def pluginsEnabled(self, value):
        with self._cfg as c:
            c.plugin.enabled = value
