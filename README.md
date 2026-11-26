# bliptrace-flask

Flask adapter for the [Bliptrace](https://scope.g8suite.com) error-capture and
observability platform. A **thin** integration layer over the runtime
[`bliptrace`](../bliptrace-python) Python SDK: it registers a Flask error handler,
enriches captured errors with request context, and ships them to the Bliptrace
ingest API.

It is designed to **never break your application** — every capture path is
guard-wrapped, and the send is fire-and-forget.

> The `project` is never sent in the payload. Bliptrace resolves it server-side
> from your ingest key (anti-spoof).

## Installation

The runtime SDK is currently unpublished, so install it from a local checkout
first, then install this adapter:

```bash
python3 -m pip install -e ../bliptrace-python
python3 -m pip install -e .
```

Flask itself is an optional dependency (you almost certainly already have it):

```bash
python3 -m pip install "bliptrace-flask[flask]"
```

## Quick start

```python
from flask import Flask
from bliptrace_flask import Bliptrace

app = Flask(__name__)
g8 = Bliptrace(app, key="your-ingest-key")
```

### Application-factory pattern

```python
from bliptrace_flask import Bliptrace

g8 = Bliptrace()

def create_app():
    app = Flask(__name__)
    g8.init_app(app)
    return app
```

Once registered, any unhandled exception raised while handling a request is
captured automatically (via Flask's `got_request_exception` signal) and
shipped, enriched with request method, URL, path, and headers. Your app's own
error handling proceeds unchanged — Bliptrace only observes.

## Configuration

Pass settings as keyword arguments, or via `app.config` using `BLIPTRACE_*`
keys. Explicit keyword arguments take precedence over `app.config`.

```python
app.config.update(
    BLIPTRACE_KEY="your-ingest-key",
    BLIPTRACE_ENDPOINT="https://ingest.scope.g8suite.com",
    BLIPTRACE_ENVIRONMENT="production",
    BLIPTRACE_RELEASE="1.4.2",
    BLIPTRACE_BASE_PATH="/srv/app",        # marks your code as in-app frames
    BLIPTRACE_SCRUB_KEYS=["password", "token"],
    BLIPTRACE_IGNORE_EXCEPTIONS=["KeyError"],
    BLIPTRACE_ENABLED=True,
)
Bliptrace(app)
```

| Config key | Maps to | Notes |
|---|---|---|
| `BLIPTRACE_KEY` | `key` | Ingest key. Nothing is sent without it. |
| `BLIPTRACE_ENDPOINT` | `endpoint` | Ingest base URL. |
| `BLIPTRACE_ENVIRONMENT` | `environment` | e.g. `production`, `staging`. |
| `BLIPTRACE_RELEASE` | `release` | Release / version identifier. |
| `BLIPTRACE_TIMEOUT` | `timeout` | Send timeout (seconds). |
| `BLIPTRACE_MAX_FRAMES` | `max_frames` | Max stack frames kept. |
| `BLIPTRACE_MAX_MESSAGE` | `max_message` | Max message length. |
| `BLIPTRACE_IGNORE_EXCEPTIONS` | `ignore_exceptions` | Classes or class names. |
| `BLIPTRACE_SCRUB_KEYS` | `scrub_keys` | Context keys to redact. |
| `BLIPTRACE_BASE_PATH` | `base_path` | Project root for in-app detection. |
| `BLIPTRACE_ENABLED` | `enabled` | Set `False` to disable. |
| `BLIPTRACE_SDK_NAME` | `sdk_name` | Override SDK name. |
| `BLIPTRACE_SDK_VERSION` | `sdk_version` | Override SDK version. |

> **Deprecated:** the old `G8SCOPE_*` keys are still read as a fallback when
> the matching `BLIPTRACE_*` key is unset. They will be removed in the next
> major version.

## Manual capture

To capture a handled exception, call `capture_exception`. Live request context
is merged in automatically; pass extra data under `custom`:

```python
g8 = app.extensions["bliptrace"]

try:
    risky()
except Exception as exc:
    g8.capture_exception(exc, context={"custom": {"user_id": 42}})
```

## Privacy

The `authorization`, `cookie`, `set-cookie`, and `proxy-authorization` request
headers are stripped before the envelope leaves your process. Additional PII is
redacted server-side, and you can redact more locally with `BLIPTRACE_SCRUB_KEYS`.

## Licence

MIT © Developers Hub Sdn Bhd
