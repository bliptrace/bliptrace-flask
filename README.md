# g8scope-flask

Flask adapter for the [g8scope](https://scope.g8suite.com) error-capture and
observability platform. A **thin** integration layer over the runtime
[`g8scope`](../g8scope-python) Python SDK: it registers a Flask error handler,
enriches captured errors with request context, and ships them to the g8scope
ingest API.

It is designed to **never break your application** — every capture path is
guard-wrapped, and the send is fire-and-forget.

> The `project` is never sent in the payload. g8scope resolves it server-side
> from your ingest key (anti-spoof).

## Installation

The runtime SDK is currently unpublished, so install it from a local checkout
first, then install this adapter:

```bash
python3 -m pip install -e ../g8scope-python
python3 -m pip install -e .
```

Flask itself is an optional dependency (you almost certainly already have it):

```bash
python3 -m pip install "g8scope-flask[flask]"
```

## Quick start

```python
from flask import Flask
from g8scope_flask import G8Scope

app = Flask(__name__)
g8 = G8Scope(app, key="your-ingest-key")
```

### Application-factory pattern

```python
from g8scope_flask import G8Scope

g8 = G8Scope()

def create_app():
    app = Flask(__name__)
    g8.init_app(app)
    return app
```

Once registered, any unhandled exception raised while handling a request is
captured automatically (via Flask's `got_request_exception` signal) and
shipped, enriched with request method, URL, path, and headers. Your app's own
error handling proceeds unchanged — g8scope only observes.

## Configuration

Pass settings as keyword arguments, or via `app.config` using `G8SCOPE_*`
keys. Explicit keyword arguments take precedence over `app.config`.

```python
app.config.update(
    G8SCOPE_KEY="your-ingest-key",
    G8SCOPE_ENDPOINT="https://ingest.scope.g8suite.com",
    G8SCOPE_ENVIRONMENT="production",
    G8SCOPE_RELEASE="1.4.2",
    G8SCOPE_BASE_PATH="/srv/app",        # marks your code as in-app frames
    G8SCOPE_SCRUB_KEYS=["password", "token"],
    G8SCOPE_IGNORE_EXCEPTIONS=["KeyError"],
    G8SCOPE_ENABLED=True,
)
G8Scope(app)
```

| Config key | Maps to | Notes |
|---|---|---|
| `G8SCOPE_KEY` | `key` | Ingest key. Nothing is sent without it. |
| `G8SCOPE_ENDPOINT` | `endpoint` | Ingest base URL. |
| `G8SCOPE_ENVIRONMENT` | `environment` | e.g. `production`, `staging`. |
| `G8SCOPE_RELEASE` | `release` | Release / version identifier. |
| `G8SCOPE_TIMEOUT` | `timeout` | Send timeout (seconds). |
| `G8SCOPE_MAX_FRAMES` | `max_frames` | Max stack frames kept. |
| `G8SCOPE_MAX_MESSAGE` | `max_message` | Max message length. |
| `G8SCOPE_IGNORE_EXCEPTIONS` | `ignore_exceptions` | Classes or class names. |
| `G8SCOPE_SCRUB_KEYS` | `scrub_keys` | Context keys to redact. |
| `G8SCOPE_BASE_PATH` | `base_path` | Project root for in-app detection. |
| `G8SCOPE_ENABLED` | `enabled` | Set `False` to disable. |
| `G8SCOPE_SDK_NAME` | `sdk_name` | Override SDK name. |
| `G8SCOPE_SDK_VERSION` | `sdk_version` | Override SDK version. |

## Manual capture

To capture a handled exception, call `capture_exception`. Live request context
is merged in automatically; pass extra data under `custom`:

```python
g8 = app.extensions["g8scope"]

try:
    risky()
except Exception as exc:
    g8.capture_exception(exc, context={"custom": {"user_id": 42}})
```

## Privacy

The `authorization`, `cookie`, `set-cookie`, and `proxy-authorization` request
headers are stripped before the envelope leaves your process. Additional PII is
redacted server-side, and you can redact more locally with `G8SCOPE_SCRUB_KEYS`.

## Licence

MIT © Developers Hub Sdn Bhd
