"""g8scope Flask adapter — thin Flask integration over the g8scope Python SDK."""

from .context import build_context
from .extension import G8Scope

__version__ = "1.0.0"

__all__ = ["G8Scope", "build_context", "__version__"]
