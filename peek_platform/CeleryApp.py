

from celery import Celery

from peek_platform import PeekPlatformConfig

celeryApp = Celery('celery')


def configureCeleryApp(app):
    # Optional configuration, see the application user guide.
    app.conf.update(
        BROKER_URL='amqp://',
        CELERY_RESULT_BACKEND='redis://localhost',

        # Leave the logging to us
        CELERYD_HIJACK_ROOT_LOGGER=False,

        CELERY_TASK_RESULT_EXPIRES=3600,
        CELERY_TASK_SERIALIZER='json',
        CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
        CELERY_RESULT_SERIALIZER='json',
        CELERY_ENABLE_UTC=True
    )


def start():
    configureCeleryApp(celeryApp)

    pluginIncludes = PeekPlatformConfig.pluginLoader.celeryAppIncludes

    celeryApp.conf.update(
        # DbConnection MUST BE FIRST, so that it creates a new connection
        CELERY_INCLUDE=['peek_plugin_base.worker.CeleryDbConnInit'] + pluginIncludes,
    )

    # Create and set this attribute so that the CeleryDbConn can use it
    # Worker is passed as sender to @worker_init.connect
    celeryApp.peekDbConnectString = PeekPlatformConfig.config.dbConnectString

    celeryApp.worker_main()
