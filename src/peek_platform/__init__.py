
class PeekPlatformConfig:
    # The component name of this part of the platform
    # EG, peek_server, peek_worker, peek_agent
    componentName = None

    # The config accessor class
    config = None

    # The inherited class of PappSwInstallManagerBase
    pappSwInstallManager = None