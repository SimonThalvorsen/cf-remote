import os
import urllib.error
from email.message import Message
from pathlib import Path
from unittest.mock import patch

import pytest

from cf_remote.web import (
    get_json,
    is_transient_error,
    json_cache_path,
    urlopen_retry,
)


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("url", code, "reason", Message(), None)


class FakeResponse:
    """Just enough of an HTTPResponse for get_json()"""

    def __init__(self, payload: str) -> None:
        self.status = 200
        self.payload = payload

    def read(self) -> bytes:
        return self.payload.encode()

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None


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


ENTERPRISE_URL = "https://cfengine.com/release-data/enterprise/releases.json"
COMMUNITY_URL = "https://cfengine.com/release-data/community/releases.json"


@pytest.fixture
def cache_dir(tmp_path, monkeypatch) -> Path:
    """Keep the JSON cache of these tests out of the real one"""

    # get_json() uses the default delay, so don't wait for the retries
    monkeypatch.setattr("time.sleep", lambda _: None)
    directory = tmp_path / "cf-remote"
    monkeypatch.setenv("CF_REMOTE_DIR", str(directory))
    return directory / "json"


def test_json_cache_path_is_unique_per_edition(cache_dir: Path) -> None:
    assert json_cache_path(ENTERPRISE_URL) != json_cache_path(COMMUNITY_URL)


def test_get_json_caches(cache_dir: Path) -> None:
    calls = 0

    def urlopen(_: str) -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse('{"version": "3.27.1"}')

    with patch("urllib.request.urlopen", urlopen):
        assert get_json(ENTERPRISE_URL) == {"version": "3.27.1"}
        assert calls == 1

        # Recently cached, so the server is left alone
        assert get_json(ENTERPRISE_URL) == {"version": "3.27.1"}
        assert calls == 1

        # Cache too old to be trusted
        assert get_json(ENTERPRISE_URL, max_age=0) == {"version": "3.27.1"}
        assert calls == 2


def test_get_json_falls_back_on_stale_cache(cache_dir: Path) -> None:
    def urlopen(_: str) -> FakeResponse:
        return FakeResponse('{"version": "3.27.1"}')

    with patch("urllib.request.urlopen", urlopen):
        get_json(ENTERPRISE_URL)

    def urlopen_502(_: str) -> FakeResponse:
        raise http_error(502)

    with patch("urllib.request.urlopen", urlopen_502):
        assert get_json(ENTERPRISE_URL, max_age=0) == {"version": "3.27.1"}


def test_get_json_without_cache_raises(cache_dir: Path) -> None:
    def urlopen(_: str) -> FakeResponse:
        raise http_error(502)

    with patch("urllib.request.urlopen", urlopen):
        try:
            get_json(ENTERPRISE_URL)
            assert False
        except urllib.error.HTTPError:
            pass

    assert not os.path.exists(json_cache_path(ENTERPRISE_URL))
