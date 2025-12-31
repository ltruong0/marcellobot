import discord
from discord import app_commands
from discord.ext import commands

from ..services import N8NClient


class HomeCommands(commands.Cog):
    """Commands for home automation."""

    def __init__(self, bot: commands.Bot, n8n: N8NClient):
        self.bot = bot
        self.n8n = n8n

    @app_commands.command(name="home", description="Control home automation")
    @app_commands.describe(
        action="Action to perform",
        target="Target device or area",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="lights on", value="lights_on"),
            app_commands.Choice(name="lights off", value="lights_off"),
            app_commands.Choice(name="status", value="status"),
        ]
    )
    async def home_control(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        target: str | None = None,
    ):
        """Control home automation devices."""
        await interaction.response.defer(thinking=True)

        try:
            payload = {
                "action": action.value,
                "target": target,
                "user": str(interaction.user),
            }

            result = await self.n8n.trigger_webhook("home-control", payload)

            if result.get("error"):
                await interaction.followup.send(
                    f"Failed: {result.get('message', 'Unknown error')}"
                )
                return

            message = result.get("message") or result.get("response") or "Done!"
            await interaction.followup.send(message)

        except Exception as e:
            await interaction.followup.send(f"Error: {e}")


async def setup(bot: commands.Bot, n8n: N8NClient):
    await bot.add_cog(HomeCommands(bot, n8n))
