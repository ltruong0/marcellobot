import os
from dataclasses import dataclass


@dataclass
class Config:
    discord_token: str
    n8n_base_url: str
    n8n_webhook_secret: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            discord_token=os.environ["DISCORD_TOKEN"],
            n8n_base_url=os.environ.get("N8N_BASE_URL", "https://n8n.marcellolab.com"),
            n8n_webhook_secret=os.environ.get("N8N_WEBHOOK_SECRET"),
        )
