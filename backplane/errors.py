class ConfigNotFound(BaseException):
    """Raised when the config can't be found"""

    pass


class ServiceNotFound(BaseException):
    """Raised when the config can't be found"""

    pass


class CannotStartService(BaseException):
    """Raised when a container can't be started"""

    pass


class CannotStopService(BaseException):
    """Raised when a container can't be stopped"""

    pass


class CannotRemoveService(BaseException):
    """Raised when a container can't be removed"""

    pass
