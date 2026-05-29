"""
Gardener Tools — Plant care database, storage, and analysis tools.

Each submodule is imported independently so a missing optional dependency
(psycopg2, boto3, requests) only disables the affected tools rather than
breaking the whole package.
"""
import logging as _logging

_log = _logging.getLogger(__name__)


def _safe_import(name: str) -> dict:
    """Import a submodule by name, returning its public symbols. Logs and
    skips on ImportError so an optional dep doesn't break the package."""
    try:
        mod = __import__(f"{__name__}.{name}", fromlist=["*"])
    except ImportError as e:
        _log.warning("gardener.tools.%s unavailable: %s", name, e)
        return {}
    return {k: getattr(mod, k) for k in dir(mod) if not k.startswith("_")}


globals().update(_safe_import("db"))
globals().update(_safe_import("guides"))
globals().update(_safe_import("s3"))
globals().update(_safe_import("plant_analyzer"))
globals().update(_safe_import("plantnet"))
globals().update(_safe_import("bootstrap"))
