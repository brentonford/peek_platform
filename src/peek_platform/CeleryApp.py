from __future__ import absolute_import

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


def start(*args):
    configureCeleryApp(celeryApp)

    pappIncludes = PeekPlatformConfig.pappLoader.celeryAppIncludes

    celeryApp.conf.update(
        # DbConnection MUST BE FIRST, so that it creates a new connection
        CELERY_INCLUDE=['papp_base.worker.CeleryDbConnInit'] + pappIncludes,
    )

    # Create and set this attribute so that the CeleryDbConn can use it
    # Worker is passed as sender to @worker_init.connect
    celeryApp.peekDbConnectString = PeekPlatformConfig.config.dbConnectString
    # Ingore this we need different pool settings for workers, they are one per proc
    # peekWorkerApp.xxx = peekWorkerConfig.sqlaEngineArgs

    celeryApp.worker_main()
