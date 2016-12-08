from abc import ABCMeta

from jsoncfg.value_mappers import require_string, require_integer


class PeekFileConfigPeekServerClientMixin(metaclass=ABCMeta):

    ### SERVER SECTION ###
    @property
    def peekServerPort(self):
        with self._cfg as c:
            return c.peekServer.port(8011, require_integer)


    @property
    def peekServerHost(self):
        with self._cfg as c:
            return c.peekServer.host('127.0.0.1', require_string)
