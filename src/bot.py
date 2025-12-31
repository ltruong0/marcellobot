import logging

import discord
from discord.ext import commands
from dotenv import load_dotenv

from .config import Config
from .services import N8NClient
from .commands import stock, home, status, webhook, help, vettix

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("marcellobot")


class MarcelloBot(commands.Bot):
    """Discord bot for homelab automation."""

    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",  # Fallback prefix, mainly using slash commands
            intents=intents,
            description="Marcello homelab automation bot",
        )

        self.config = config
        self.n8n = N8NClient(
            base_url=config.n8n_base_url,
            webhook_secret=config.n8n_webhook_secret,
        )

    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info("Loading command cogs...")

        # Load all command modules
        await stock.setup(self, self.n8n)
        await home.setup(self, self.n8n)
        await status.setup(self, self.n8n)
        await webhook.setup(self, self.n8n)
        await help.setup(self, self.n8n)
        await vettix.setup(self, self.n8n)

        logger.info("Syncing slash commands...")
        await self.tree.sync()
        logger.info("Commands synced!")

    async def on_ready(self):
        """Called when the bot is fully connected."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        logger.info(f"n8n base URL: {self.config.n8n_base_url}")

        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="the homelab",
            )
        )


def main():
    """Entry point for the bot."""
    load_dotenv()
    config = Config.from_env()
    bot = MarcelloBot(config)

    logger.info("Starting MarcelloBot...")
    bot.run(config.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
