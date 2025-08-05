"""plansi - Plays videos as differential ANSI in terminals."""

from importlib.metadata import version, PackageNotFoundError
from .player import Player

try:
    __version__ = version("plansi")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["Player", "__version__"]
