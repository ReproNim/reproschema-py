import logging
import os

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions

#
# Basic logger configuration
#


def get_logger(name=None):
    """Return a logger to use
    """
    return logging.getLogger("reproschema" + (".%s" % name if name else ""))


def set_logger_level(lgr, level):
    if isinstance(level, int):
        pass
    elif level.isnumeric():
        level = int(level)
    elif level.isalpha():
        level = getattr(logging, level)
    else:
        lgr.warning("Do not know how to treat loglevel %s" % level)
        return
    lgr.setLevel(level)


_DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

lgr = get_logger()
# Basic settings for output, for now just basic
set_logger_level(lgr, os.environ.get("REPROSCHEMA_LOG_LEVEL", logging.INFO))
FORMAT = "%(asctime)-15s [%(levelname)8s] %(message)s"
logging.basicConfig(format=FORMAT)

try:
    import etelemetry

    etelemetry.check_available_version("repronim/reproschema-py", __version__, lgr=lgr)
except Exception as exc:
    lgr.warning(
        "Failed to check for a more recent version available with etelemetry: %s", exc
    )
