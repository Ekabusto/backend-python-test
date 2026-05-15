import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

PROVIDER_BASE_URL = "http://localhost:3001"
API_KEY = "test-dev-2026"


class ProviderError(Exception):
    pass


class RateLimitError(ProviderError):
    pass


@retry(
    retry=retry_if_exception_type(ProviderError),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def send_notification(to: str, message: str, notification_type: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{PROVIDER_BASE_URL}/v1/notify",
            headers={"X-API-Key": API_KEY},
            json={"to": to, "message": message, "type": notification_type},
        )

    if response.status_code == 429:
        raise RateLimitError("Rate limit alcanzado, reintentando...")

    if response.status_code >= 500:
        raise ProviderError(f"Error del provider: {response.status_code}")
