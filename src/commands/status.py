import discord
from discord import app_commands
from discord.ext import commands

from ..services import N8NClient


class StatusCommands(commands.Cog):
    """Commands for checking server/service status."""

    def __init__(self, bot: commands.Bot, n8n: N8NClient):
        self.bot = bot
        self.n8n = n8n

    @app_commands.command(name="status", description="Check homelab service status")
    @app_commands.describe(service="Specific service to check (optional)")
    async def check_status(
        self, interaction: discord.Interaction, service: str | None = None
    ):
        """Check homelab service status."""
        await interaction.response.defer(thinking=True)

        try:
            payload = {}
            if service:
                payload["service"] = service

            result = await self.n8n.trigger_webhook("server-status", payload)

            if result.get("error"):
                await interaction.followup.send(
                    f"Failed to get status: {result.get('message', 'Unknown error')}"
                )
                return

            # Format status response
            if isinstance(result, dict) and "services" in result:
                embed = discord.Embed(
                    title="Homelab Status",
                    color=discord.Color.green(),
                )
                for svc, status in result["services"].items():
                    emoji = "✅" if status.get("healthy", False) else "❌"
                    embed.add_field(
                        name=f"{emoji} {svc}",
                        value=status.get("message", "Unknown"),
                        inline=True,
                    )
                await interaction.followup.send(embed=embed)
            else:
                message = result.get("message") or result.get("response") or str(result)
                await interaction.followup.send(message)

        except Exception as e:
            await interaction.followup.send(f"Error: {e}")


async def setup(bot: commands.Bot, n8n: N8NClient):
    await bot.add_cog(StatusCommands(bot, n8n))
