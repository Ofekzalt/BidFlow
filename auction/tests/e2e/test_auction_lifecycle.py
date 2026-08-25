import uuid
from datetime import UTC, datetime, timedelta

import httpx

from auction.constants import USER_ID_HEADER


def _auction_body(**overrides: object) -> dict:
    now = datetime.now(UTC)
    body: dict = {
        "title": "Vintage watch",
        "description": "A timed English auction listing",
        "starting_price_cents": 1000,
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(days=1)).isoformat(),
    }
    body.update(overrides)
    return body


def test_create_and_public_reads(client: httpx.Client) -> None:
    seller_id = str(uuid.uuid4())
    headers = {USER_ID_HEADER: seller_id}

    unauthorized = client.post("/auctions", json=_auction_body())
    assert unauthorized.status_code == 401

    invalid = client.post(
        "/auctions",
        headers=headers,
        json=_auction_body(starting_price_cents=0),
    )
    assert invalid.status_code == 422

    created = client.post("/auctions", headers=headers, json=_auction_body())
    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "DRAFT"
    assert payload["current_price_cents"] == payload["starting_price_cents"] == 1000
    assert payload["seller_id"] == seller_id
    auction_id = payload["id"]

    listed = client.get("/auctions")
    assert listed.status_code == 200
    assert any(item["id"] == auction_id for item in listed.json())

    detail = client.get(f"/auctions/{auction_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == auction_id

    current_bid = client.get(f"/auctions/{auction_id}/current-bid")
    assert current_bid.status_code == 200
    bid = current_bid.json()
    assert bid["amount_cents"] == 1000
    assert bid["bidder_id"] is None


def test_seller_edit_and_open(client: httpx.Client) -> None:
    seller_id = str(uuid.uuid4())
    other_id = str(uuid.uuid4())
    seller_headers = {USER_ID_HEADER: seller_id}
    other_headers = {USER_ID_HEADER: other_id}

    created = client.post("/auctions", headers=seller_headers, json=_auction_body())
    assert created.status_code == 201
    auction_id = created.json()["id"]

    patched = client.patch(
        f"/auctions/{auction_id}",
        headers=seller_headers,
        json={"title": "Updated title"},
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Updated title"

    forbidden_patch = client.patch(
        f"/auctions/{auction_id}",
        headers=other_headers,
        json={"title": "Hijacked"},
    )
    assert forbidden_patch.status_code == 403

    opened = client.post(f"/auctions/{auction_id}/open", headers=seller_headers)
    assert opened.status_code == 200
    assert opened.json()["status"] == "OPEN"

    forbidden_open = client.post(
        f"/auctions/{auction_id}/open",
        headers=other_headers,
    )
    assert forbidden_open.status_code == 403

    immutable = client.patch(
        f"/auctions/{auction_id}",
        headers=seller_headers,
        json={"title": "Too late"},
    )
    assert immutable.status_code == 409
