class ZincError(Exception):
    """Base class for all Zinc-related errors."""
    pass

class ZincLogLevelError(ZincError):
    """Raised when an invalid log level is provided."""
    pass