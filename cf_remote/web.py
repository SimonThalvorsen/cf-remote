import os
import fcntl
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import json
import tempfile
from collections import OrderedDict
from cf_remote.utils import (
    is_different_checksum,
    read_json,
    write_json,
    mkdir,
)
from cf_remote import log
from cf_remote.paths import cf_remote_dir, cf_remote_packages_dir
from cf_remote.utils import CFRChecksumError

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Attempts and seconds to wait before retrying a transient error.
# The delay is doubled between each attempt.
ATTEMPTS = 3
DELAY = 2

# Seconds before cached JSON is considered stale and fetched again.
MAX_AGE = 3600


def is_transient_error(error: BaseException) -> bool:
    """Decide whether a failed request is worth retrying

    408 Request Timeout, 429 Too Many Requests and the 5xx server errors can
    all succeed if we simply ask again. Everything else is treated as
    permanent, retrying it would only delay the failure.
    """

    if not isinstance(error, urllib.error.HTTPError):
        return False
    return error.code in (408, 429) or error.code >= 500


def urlopen_retry(url: str, attempts: int = ATTEMPTS, delay: float = DELAY):
    """urlopen(), retrying requests which fail with a transient error"""

    assert attempts >= 1

    while True:
        try:
            return urllib.request.urlopen(url)
        except Exception as e:
            attempts -= 1
            if attempts < 1 or not is_transient_error(e):
                raise
            log.warning(
                "Failed to fetch '{}' ({}), retrying in {} seconds ({} attempts left)".format(
                    url, e, delay, attempts
                )
            )
            time.sleep(delay)
            delay *= 2


def json_cache_path(url: str) -> str:
    # The basename alone is not unique, enterprise and community both have a
    # releases.json, so name the file after the whole path of the URL.
    filename = urllib.parse.urlparse(url).path.strip("/").replace("/", "_")
    return os.path.join(cf_remote_dir("json", in_cache=True), filename)


def is_cache_recent(path: str, max_age: int) -> bool:
    """Whether the file was written less than max_age seconds ago"""

    try:
        return time.time() - os.path.getmtime(path) < max_age
    except OSError:
        return False


def get_json(url: str, max_age: int = MAX_AGE):
    """Get JSON from a URL, using a cached copy when possible

    A cached copy younger than max_age seconds is used without contacting the
    server at all. An older copy is only used if the server cannot be reached
    due to a transient error, since stale release data beats no release data.
    """

    path = json_cache_path(url)

    if is_cache_recent(path, max_age):
        cached = read_json(path)
        if cached is not None:
            log.debug("Using recently cached '{}'".format(path))
            return cached

    try:
        with urlopen_retry(url) as r:
            assert r.status >= 200 and r.status < 300
            data = json.loads(r.read().decode(), object_pairs_hook=OrderedDict)
    except Exception as e:
        cached = read_json(path)
        if cached is None or not is_transient_error(e):
            raise
        log.warning(
            "Failed to fetch '{}' ({}), falling back on '{}'".format(url, e, path)
        )
        return cached

    log.debug("Saving '{}' to '{}'".format(url, path))
    write_json(path, data)

    return data


def has_downloaded_package(path, filename, checksum, insecure):
    # Use "ab" to prevent truncation of the file in case it is already being
    # downloaded by a different thread.
    with open(path, "ab+") as f:
        # Get an exclusive lock. If the file size is != 0 then it's already
        # downloaded, otherwise we download.
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        st = os.stat(path)
        if st.st_size != 0:
            print("Package '{}' already downloaded".format(path))

            f.seek(0)
            content = f.read()
            if checksum and is_different_checksum(checksum, content):
                log.warning(
                    "Downloaded file '{}' does not match expected checksum '{}'. ".format(
                        filename, checksum
                    )
                )
                if insecure:
                    log.warning("Continuing due to insecure flag")
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    return True
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return True

        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return False


def download_package(url, path=None, checksum=None, insecure=False):
    assert path is None or type(path) is str and len(path) > 0

    if checksum and not SHA256_RE.match(checksum):
        raise CFRChecksumError(
            "Invalid checksum or unsupported checksum algorithm: '%s'" % checksum
        )

    if not path:
        filename = os.path.basename(url)
        directory = cf_remote_packages_dir()
        mkdir(directory)
        path = os.path.join(directory, filename)

    assert type(path) is str and len(path) > 0
    filename = os.path.basename(path)
    assert type(filename) is str and len(filename) > 0

    if has_downloaded_package(path, filename, checksum, insecure):
        return path

    print("Downloading package: '{}'".format(path))
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    answer = urlopen_retry(url).read()
    os.write(fd, answer)
    os.close(fd)

    if checksum and is_different_checksum(checksum, answer):

        if not insecure:
            log.debug("Mismatching checksums. Removing '{}'".format(tmp))
            os.remove(tmp)
            raise CFRChecksumError(
                "Temp file '{}' does not match expected checksum '{}'.".format(
                    tmp, checksum
                )
            )
        else:
            log.warning(
                "Downloaded file '{}' does not match expected checksum '{}'. Continuing due to insecure flag".format(
                    filename, checksum
                )
            )
    else:
        log.debug("Matching checksums. Renaming '{}' to '{}'".format(tmp, path))

    with open(path, "a") as f:
        fd = f.fileno()

        fcntl.flock(fd, fcntl.LOCK_EX)
        os.rename(tmp, path)
        fcntl.flock(fd, fcntl.LOCK_UN)

    return path
