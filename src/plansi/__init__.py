"""plansi - Plays videos as ANSI in terminals."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("plansi")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["__version__"]
