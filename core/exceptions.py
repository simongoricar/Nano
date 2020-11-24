class NanoException(Exception):
    """
    Base class for all Nano exceptions.
    """


class IgnoredException(NanoException):
    """
    An exception that will be ignored (for flow control)
    """
    pass


class SecurityError(NanoException):
    """
    Raised when something would go wrong but has been caught (see validate_input decorator)
    """
    pass


class PluginDisabledException(NanoException):
    """
    Raised by a plugin on disable (e.g. on missing configuration)
    """
    pass
