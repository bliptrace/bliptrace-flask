"""Flask extension that wires the g8scope runtime client into a Flask app.

THIN glue over the ``g8scope`` Python SDK. It:

* builds a :class:`g8scope.Client` once from the app config / kwargs,
* listens for unhandled exceptions via Flask's ``got_request_exception``
  signal and ships them, enriched with request context,
* exposes :meth:`capture_exception` for manual capture.

Everything is guard-wrapped — capturing an error must NEVER break the host
app. ``project`` is never sent: the server resolves it from the ingest key.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from g8scope import Client, Config

from .context import build_context

# Maps Config kwargs to their ``BLIPTRACE_*`` Flask config keys
# (deprecated ``G8SCOPE_*`` keys are read as a fallback).
_CONFIG_KEYS = (
    "key",
    "endpoint",
    "environment",
    "release",
    "timeout",
    "max_frames",
    "max_message",
    "ignore_exceptions",
    "scrub_keys",
    "base_path",
    "enabled",
    "sdk_name",
    "sdk_version",
)


class G8Scope:
    """Flask extension for g8scope error capture.

    Usage::

        app = Flask(__name__)
        g8 = G8Scope(app, key="ingest-key")

    or, with the application-factory pattern::

        g8 = G8Scope()
        g8.init_app(app)
    """

    def __init__(self, app: Optional[Any] = None, **config: Any) -> None:
        self._config_overrides: Dict[str, Any] = config
        self.client: Optional[Client] = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Any) -> None:
        """Bind the extension to a Flask ``app``."""
        try:
            self.client = self._build_client(app)
        except Exception:
            # A misconfigured client must not stop the app from booting.
            self.client = None

        # Register on the app extensions registry (Flask convention).
        try:
            app.extensions = getattr(app, "extensions", {})
            app.extensions["g8scope"] = self
        except Exception:
            pass

        self._connect_signal(app)

    # -- public API ---------------------------------------------------------

    def capture_exception(
        self, exc: BaseException, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Manually capture an exception. Guard-wrapped; never raises.

        Merges live Flask request context (when available) with any caller
        supplied ``context``.
        """
        try:
            if self.client is None:
                return
            merged = self._merge_context(context)
            self.client.capture(exc, merged)
        except Exception:
            pass  # never break the app

    # -- internals ----------------------------------------------------------

    def _build_client(self, app: Any) -> Client:
        kwargs: Dict[str, Any] = {}
        app_config = getattr(app, "config", {}) or {}

        for name in _CONFIG_KEYS:
            # BLIPTRACE_* wins; G8SCOPE_* is a deprecated fallback (next major drops it).
            for prefix in ("BLIPTRACE_", "G8SCOPE_"):
                flask_key = prefix + name.upper()
                if flask_key in app_config:
                    kwargs[name] = app_config[flask_key]
                    break

        # Explicit kwargs to __init__ win over app.config.
        kwargs.update(self._config_overrides)

        return Client(Config(**kwargs))

    def _connect_signal(self, app: Any) -> None:
        """Subscribe to Flask's unhandled-exception signal.

        ``got_request_exception`` fires for exceptions raised while handling a
        request, before Flask renders the error response — so we capture even
        when the app has its own error handlers. We never swallow or re-raise;
        Flask's normal handling proceeds unchanged.
        """
        try:
            from flask import got_request_exception

            got_request_exception.connect(self._on_exception, app, weak=False)
        except Exception:
            pass

    def _on_exception(self, sender: Any, exception: BaseException, **extra: Any) -> None:
        # Signal receivers must never raise.
        try:
            self.capture_exception(exception)
        except Exception:
            pass

    def _merge_context(
        self, context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        base = build_context(self._current_request())
        if context:
            try:
                custom = dict(base.get("custom") or {})
                incoming_custom = context.get("custom")
                if isinstance(incoming_custom, dict):
                    custom.update(incoming_custom)
                merged = dict(base)
                merged.update({k: v for k, v in context.items() if k != "custom"})
                merged["custom"] = custom
                return merged
            except Exception:
                return base
        return base

    @staticmethod
    def _current_request() -> Optional[Any]:
        try:
            from flask import request, has_request_context

            if has_request_context():
                # Resolve the underlying request object from the proxy.
                return request._get_current_object()  # type: ignore[attr-defined]
        except Exception:
            return None
        return None
