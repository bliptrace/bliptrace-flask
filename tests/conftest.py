"""Shared test helpers: a fake transport that records envelopes (no network)."""

from g8scope import Transport


class FakeTransport(Transport):
    """Records sent envelopes instead of shipping them over the wire."""

    def __init__(self):
        self.sent = []

    def send(self, endpoint, key, envelope, timeout):
        self.sent.append(
            {
                "endpoint": endpoint,
                "key": key,
                "envelope": envelope,
                "timeout": timeout,
            }
        )
