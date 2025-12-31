import discord
from discord import app_commands
from discord.ext import commands

from ..services import N8NClient

LOGS_CHANNEL = "logs"
VETTIX_CHANNEL = "vettix-scraper"


class VetTixCommands(commands.Cog):
    """Commands for scraping VetTix events."""

    def __init__(self, bot: commands.Bot, n8n: N8NClient):
        self.bot = bot
        self.n8n = n8n

    async def get_or_create_channel(
        self, guild: discord.Guild, channel_name: str
    ) -> discord.TextChannel:
        """Get an existing channel or create it if it doesn't exist."""
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if channel is None:
            channel = await guild.create_text_channel(channel_name)
        return channel

    async def log_to_channel(self, guild: discord.Guild, message: str):
        """Send a log message to the logs channel."""
        channel = await self.get_or_create_channel(guild, LOGS_CHANNEL)
        await channel.send(message)

    @app_commands.command(
        name="vettix", description="Scrape VetTix events for a state"
    )
    @app_commands.describe(
        state="Two-letter state code (e.g., tx, tn, ca, nv)",
        status="Event status filter",
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Open tickets only", value="open"),
            app_commands.Choice(name="All events", value="all"),
        ]
    )
    async def scrape_vettix(
        self,
        interaction: discord.Interaction,
        state: str,
        status: str = "open",
    ):
        """Scrape VetTix events for a given state."""
        await interaction.response.defer(thinking=True)

        state = state.lower().strip()
        if len(state) != 2:
            await interaction.followup.send(
                "Please provide a two-letter state code (e.g., tx, tn, ca)"
            )
            return

        try:
            await self.log_to_channel(
                interaction.guild,
                f"`[VetTix]` Scraping {state.upper()} events requested by {interaction.user.mention}",
            )

            # Get or create the vettix channel
            vettix_channel = await self.get_or_create_channel(
                interaction.guild, VETTIX_CHANNEL
            )

            payload = {
                "state": state,
                "status": status,
                "guild_id": str(interaction.guild_id),
                "channel_id": str(vettix_channel.id),
            }

            result = await self.n8n.trigger_webhook("vettix-scraper", payload)

            if result.get("error"):
                error_msg = f"Failed to scrape VetTix: {result.get('message', 'Unknown error')}"
                await self.log_to_channel(
                    interaction.guild, f"`[VetTix]` Error: {error_msg}"
                )
                await interaction.followup.send(error_msg)
                return

            # n8n handles posting to Discord with threading
            # Just log and respond to the user
            event_count = result.get("count", 0)

            await self.log_to_channel(
                interaction.guild,
                f"`[VetTix]` Scraped {event_count} events for {state.upper()}",
            )

            await interaction.followup.send(
                f"Scraped {event_count} events for {state.upper()}. "
                f"Results posted to {vettix_channel.mention}"
            )

        except Exception as e:
            error_msg = f"Error scraping VetTix: {e}"
            await self.log_to_channel(
                interaction.guild, f"`[VetTix]` Error: {error_msg}"
            )
            await interaction.followup.send(error_msg)


async def setup(bot: commands.Bot, n8n: N8NClient):
    await bot.add_cog(VetTixCommands(bot, n8n))
