import os
import time
from collections.abc import Iterator

import httpx
import pytest

RETRY_URL = os.environ.get("GATEWAY_RETRY_URL", "http://127.0.0.1:8081")


@pytest.fixture(scope="module")
def retry_client() -> Iterator[httpx.Client]:
    deadline = time.time() + 60
    last_error = None
    while time.time() < deadline:
        try:
            with httpx.Client(base_url=RETRY_URL, timeout=5.0) as probe:
                probe.get("/count").raise_for_status()
            break
        except httpx.HTTPError as exc:
            last_error = exc
            time.sleep(0.5)
    else:
        raise RuntimeError(f"retry kong did not become ready: {last_error}")
    client = httpx.Client(base_url=RETRY_URL, timeout=10.0)
    yield client
    client.close()


def test_safe_get_retries_on_502(retry_client: httpx.Client) -> None:
    reset = retry_client.get("/reset", params={"fail": "2"})
    assert reset.status_code == 200
    response = retry_client.get("/retry-get")
    assert response.status_code == 200
    count = int(retry_client.get("/count").text)
    assert count == 3


def test_unsafe_post_is_not_retried(retry_client: httpx.Client) -> None:
    reset = retry_client.get("/reset", params={"fail": "5"})
    assert reset.status_code == 200
    response = retry_client.post("/retry-post")
    assert response.status_code == 502
    count = int(retry_client.get("/count").text)
    assert count == 1
