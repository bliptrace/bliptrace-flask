"""Unit tests for the duck-typed context builder (no live Flask request)."""

from g8scope_flask import build_context


class FakeRequest:
    def __init__(self, method="GET", url="http://x/y", path="/y", headers=None):
        self.method = method
        self.url = url
        self.path = path
        self.headers = headers or {}


def test_returns_custom_fallback_when_no_request():
    ctx = build_context(None)
    assert ctx == {"custom": {}}


def test_extracts_method_and_url():
    ctx = build_context(FakeRequest(method="POST", url="http://x/y?z=1"))
    assert ctx["request"]["method"] == "POST"
    assert ctx["request"]["url"] == "http://x/y?z=1"
    assert ctx["request"]["path"] == "/y"
    assert ctx["custom"] == {}


def test_strips_authorization_and_cookie_headers():
    req = FakeRequest(
        headers={
            "Authorization": "Bearer secret",
            "Cookie": "session=abc",
            "Set-Cookie": "x=y",
            "Content-Type": "application/json",
            "X-Request-Id": "r-1",
        }
    )
    headers = build_context(req)["request"]["headers"]
    assert "Authorization" not in headers
    assert "Cookie" not in headers
    assert "Set-Cookie" not in headers
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Request-Id"] == "r-1"


def test_header_stripping_is_case_insensitive():
    req = FakeRequest(headers={"authorization": "x", "COOKIE": "y", "Ok": "1"})
    headers = build_context(req)["request"]["headers"]
    assert headers == {"Ok": "1"}


def test_tolerates_broken_request_object():
    class Broken:
        @property
        def method(self):
            raise RuntimeError("nope")

    ctx = build_context(Broken())
    assert ctx == {"custom": {}}
