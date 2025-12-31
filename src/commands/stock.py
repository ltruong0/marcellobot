import discord
from discord import app_commands
from discord.ext import commands

from ..services import N8NClient


class StockCommands(commands.Cog):
    """Commands for checking product stock status."""

    def __init__(self, bot: commands.Bot, n8n: N8NClient):
        self.bot = bot
        self.n8n = n8n

    @app_commands.command(name="utr", description="Check UTR stock status")
    @app_commands.describe(product="Product name or SKU to check (optional)")
    async def check_utr_stock(
        self, interaction: discord.Interaction, product: str | None = None
    ):
        """Check UTR product stock status."""
        await interaction.response.defer(thinking=True)

        try:
            payload = {}
            if product:
                payload["product"] = product

            result = await self.n8n.trigger_webhook("utr-stock-check", payload)

            if result.get("error"):
                await interaction.followup.send(
                    f"Failed to check stock: {result.get('message', 'Unknown error')}"
                )
                return

            # Format the response based on what n8n returns
            message = result.get("message") or result.get("response") or str(result)
            await interaction.followup.send(message)

        except Exception as e:
            await interaction.followup.send(f"Error checking stock: {e}")


async def setup(bot: commands.Bot, n8n: N8NClient):
    await bot.add_cog(StockCommands(bot, n8n))
