"""Integration tests: a real Flask app wired with the Bliptrace extension."""

import pytest

from bliptrace_flask import Bliptrace

from conftest import FakeTransport

flask = pytest.importorskip("flask")
from flask import Flask  # noqa: E402


def _make_app(**config):
    app = Flask(__name__)
    # Leave TESTING off so Flask renders a 500 (and fires got_request_exception)
    # rather than re-raising the exception out of the test client.
    app.config["PROPAGATE_EXCEPTIONS"] = False
    g8 = Bliptrace(app, **config)
    # Swap in a recording transport so nothing hits the network.
    if g8.client is not None:
        g8.transport = FakeTransport()
        g8.client.transport = g8.transport

    @app.route("/boom")
    def boom():
        raise RuntimeError("kaboom")

    @app.route("/ok")
    def ok():
        return "ok"

    return app, g8


def test_unhandled_exception_is_captured_and_shipped():
    app, g8 = _make_app(key="k", base_path="/srv/app")
    client = app.test_client()

    resp = client.get("/boom")
    assert resp.status_code == 500  # host app behaviour unchanged

    sent = g8.transport.sent
    assert len(sent) == 1
    env = sent[0]["envelope"]
    assert env["runtime"]["name"] == "python"
    assert env["sdk"]["name"] == "bliptrace-python"
    assert env["exception"]["type"] == "RuntimeError"
    assert env["exception"]["message"] == "kaboom"
    assert "project" not in env  # resolved server-side from the key
    # request context was enriched
    assert env["context"]["request"]["method"] == "GET"
    assert "/boom" in env["context"]["request"]["url"]


def test_successful_request_sends_nothing():
    app, g8 = _make_app(key="k")
    resp = app.test_client().get("/ok")
    assert resp.status_code == 200
    assert g8.transport.sent == []


def test_no_key_sends_nothing():
    app, g8 = _make_app(key=None)
    # No key -> client built but produces no envelope. Attach a recorder anyway.
    g8.transport = FakeTransport()
    if g8.client is not None:
        g8.client.transport = g8.transport
    resp = app.test_client().get("/boom")
    assert resp.status_code == 500
    assert g8.transport.sent == []


def test_disabled_sends_nothing():
    app, g8 = _make_app(key="k", enabled=False)
    app.test_client().get("/boom")
    assert g8.transport.sent == []


def test_config_read_from_app_config():
    app = Flask(__name__)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.config["BLIPTRACE_KEY"] = "from-config"
    app.config["BLIPTRACE_ENVIRONMENT"] = "staging"
    g8 = Bliptrace(app)
    g8.transport = FakeTransport()
    g8.client.transport = g8.transport

    @app.route("/boom")
    def boom():
        raise ValueError("x")

    app.test_client().get("/boom")
    assert len(g8.transport.sent) == 1
    assert g8.transport.sent[0]["envelope"]["environment"] == "staging"


def test_bliptrace_config_wins_over_deprecated_keys():
    app = Flask(__name__)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.config["BLIPTRACE_KEY"] = "new-key"
    app.config["G8SCOPE_KEY"] = "old-key"
    app.config["BLIPTRACE_ENVIRONMENT"] = "new-env"
    app.config["G8SCOPE_ENVIRONMENT"] = "old-env"
    app.config["G8SCOPE_RELEASE"] = "old-rel"  # no BLIPTRACE_RELEASE: falls back
    g8 = Bliptrace(app)
    assert g8.client.config.key == "new-key"
    assert g8.client.config.environment == "new-env"
    assert g8.client.config.release == "old-rel"


def test_init_app_factory_pattern():
    g8 = Bliptrace()
    app = Flask(__name__)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.config["BLIPTRACE_KEY"] = "k"
    g8.init_app(app)
    g8.transport = FakeTransport()
    g8.client.transport = g8.transport

    @app.route("/boom")
    def boom():
        raise RuntimeError("factory")

    app.test_client().get("/boom")
    assert len(g8.transport.sent) == 1
    assert g8.transport.sent[0]["envelope"]["exception"]["message"] == "factory"


def test_manual_capture_outside_request_context():
    app = Flask(__name__)
    g8 = Bliptrace(app, key="k")
    g8.transport = FakeTransport()
    g8.client.transport = g8.transport

    try:
        raise KeyError("manual")
    except KeyError as exc:
        g8.capture_exception(exc, context={"custom": {"user_id": 7}})

    assert len(g8.transport.sent) == 1
    env = g8.transport.sent[0]["envelope"]
    assert env["exception"]["type"] == "KeyError"
    assert env["context"]["custom"]["user_id"] == 7


def test_extension_registered_on_app():
    app, g8 = _make_app(key="k")
    assert app.extensions["bliptrace"] is g8


def test_capture_never_raises_with_no_client():
    g8 = Bliptrace()  # never init_app'd -> no client
    try:
        raise RuntimeError("x")
    except RuntimeError as exc:
        g8.capture_exception(exc)  # must not raise
