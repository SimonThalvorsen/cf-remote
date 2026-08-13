import urllib.error
from email.message import Message
from unittest.mock import patch

from cf_remote.web import is_transient_error, urlopen_retry


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("url", code, "reason", Message(), None)


def test_is_transient_error() -> None:
    assert is_transient_error(http_error(408))
    assert is_transient_error(http_error(429))
    assert is_transient_error(http_error(502))
    assert is_transient_error(http_error(503))

    assert not is_transient_error(http_error(400))
    assert not is_transient_error(http_error(404))
    assert not is_transient_error(urllib.error.URLError("connection refused"))


def test_urlopen_retry_transient_error() -> None:
    calls = 0

    def urlopen(_: str) -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise http_error(502)
        return "response"

    with patch("urllib.request.urlopen", urlopen):
        assert urlopen_retry("url", delay=0) == "response"
    assert calls == 3


def test_urlopen_retry_out_of_attempts() -> None:
    calls = 0

    def urlopen(_: str) -> str:
        nonlocal calls
        calls += 1
        raise http_error(502)

    with patch("urllib.request.urlopen", urlopen):
        try:
            urlopen_retry("url", attempts=3, delay=0)
            assert False
        except urllib.error.HTTPError:
            pass
    assert calls == 3


def test_urlopen_retry_permanent_error() -> None:
    calls = 0

    def urlopen(_: str) -> str:
        nonlocal calls
        calls += 1
        raise http_error(404)

    with patch("urllib.request.urlopen", urlopen):
        try:
            urlopen_retry("url", delay=0)
            assert False
        except urllib.error.HTTPError:
            pass
    assert calls == 1
