from stripe import HTTPXClient, StripeClient

from settlement.config import settings
from settlement.constants import STRIPE_TIMEOUT_SECONDS


def create_stripe_client() -> StripeClient:
    http_client = HTTPXClient(timeout=STRIPE_TIMEOUT_SECONDS)
    if settings.stripe_api_base:
        return StripeClient(
            settings.stripe_secret_key,
            http_client=http_client,
            base_addresses={"api": settings.stripe_api_base},
        )
    return StripeClient(
        settings.stripe_secret_key,
        http_client=http_client,
    )
