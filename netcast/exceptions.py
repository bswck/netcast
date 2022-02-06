class NetcastError(Exception):
    """A netcast library exception."""


class ArrangementError(NetcastError):
    pass


class ArrangementConstructionError(ArrangementError, ValueError):
    pass


class ArrangementTypeError(ArrangementError, TypeError):
    pass


class ConstraintError(NetcastError, ValueError):
    """A constraint failed."""
