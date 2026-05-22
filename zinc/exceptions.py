class ZincError(Exception):
    """Base class for all Zinc-related errors."""

    pass


class ZincLogLevelError(ZincError):
    """Raised when an invalid log level is provided."""

    pass


class ZincTypeError(ZincError):
    """Raised when Zinc type inference or validation fails."""

    pass


class ZincModuleError(ZincError):
    """Raised when package or module loading fails."""

    pass
