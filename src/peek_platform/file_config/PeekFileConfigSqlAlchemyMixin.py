import logging

from jsoncfg.value_mappers import require_string, require_dict

logger = logging.getLogger(__name__)


class PeekFileConfigSqlAlchemyMixin:
    @property
    def sqlaConnectUrl(self):
        default = 'postgresql://peek:PASSWORD@localhost/peek'
        with self._cfg as c:
            return c.sqlalchemy.url(default, require_string)

    @property
    def sqlaEngineArgs(self):
        default = {
            'pool_size': 20,  # Number of connections to keep open
            'max_overflow': 50,  # Number that the pool size can exceed when required
            'pool_timeout': 60,  # Timeout for getting conn from pool
            'pool_recycle': 600  # Reconnect?? after 10 minutes
        }
        with self._cfg as c:
            return c.sqlalchemy.engin_args(default, require_dict)
