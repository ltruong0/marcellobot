import aiohttp
from typing import Any


class N8NClient:
    """Client for calling n8n webhooks."""

    def __init__(self, base_url: str, webhook_secret: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.webhook_secret = webhook_secret

    async def trigger_webhook(
        self,
        webhook_path: str,
        payload: dict[str, Any] | None = None,
        method: str = "POST",
    ) -> dict[str, Any]:
        """
        Trigger an n8n webhook and return the response.

        Args:
            webhook_path: The webhook path (e.g., "utr-stock-check")
            payload: Data to send to the webhook
            method: HTTP method (GET or POST)

        Returns:
            Response data from n8n workflow
        """
        url = f"{self.base_url}/webhook/{webhook_path}"
        headers = {"Content-Type": "application/json"}

        if self.webhook_secret:
            headers["X-Webhook-Secret"] = self.webhook_secret

        async with aiohttp.ClientSession() as session:
            if method.upper() == "GET":
                async with session.get(url, headers=headers, params=payload) as resp:
                    return await self._handle_response(resp)
            else:
                async with session.post(url, headers=headers, json=payload or {}) as resp:
                    return await self._handle_response(resp)

    async def _handle_response(self, resp: aiohttp.ClientResponse) -> dict[str, Any]:
        """Handle the response from n8n."""
        if resp.status >= 400:
            text = await resp.text()
            return {"error": True, "status": resp.status, "message": text}

        try:
            return await resp.json()
        except aiohttp.ContentTypeError:
            # n8n might return plain text
            text = await resp.text()
            return {"response": text}
