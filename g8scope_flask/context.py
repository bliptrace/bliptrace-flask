"""Build envelope context from a Flask request.

Duck-typed and tolerant so it is unit-testable without a live request and
never raises into the host app. Sensitive request headers (``authorization``,
``cookie``) are stripped before anything leaves the process.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Headers that must never leave the monitored app, even before the
# server-side scrubber runs. Lower-cased for case-insensitive matching.
_STRIPPED_HEADERS = {"authorization", "cookie", "set-cookie", "proxy-authorization"}


def build_context(request: Optional[Any] = None) -> Dict[str, Any]:
    """Build an envelope ``context`` dict from a Flask ``request``.

    Always returns a dict with a ``custom`` key. When ``request`` is missing
    or unusable, falls back to ``{"custom": {}}``. Never raises.
    """
    context: Dict[str, Any] = {"custom": {}}
    if request is None:
        return context

    try:
        http: Dict[str, Any] = {}

        method = getattr(request, "method", None)
        if method:
            http["method"] = method

        url = getattr(request, "url", None)
        if url:
            http["url"] = url

        path = getattr(request, "path", None)
        if path:
            http["path"] = path

        headers = _safe_headers(getattr(request, "headers", None))
        if headers:
            http["headers"] = headers

        if http:
            context["request"] = http
    except Exception:
        # Context enrichment must never break capture.
        return {"custom": {}}

    return context


def _safe_headers(raw: Any) -> Dict[str, str]:
    """Return request headers as a flat dict minus sensitive ones."""
    out: Dict[str, str] = {}
    if raw is None:
        return out
    try:
        # werkzeug Headers, dicts, and lists of pairs all expose ``items()``.
        items = raw.items() if hasattr(raw, "items") else raw
        for key, value in items:
            if not isinstance(key, str):
                continue
            if key.lower() in _STRIPPED_HEADERS:
                continue
            out[key] = str(value)
    except Exception:
        return {}
    return out
