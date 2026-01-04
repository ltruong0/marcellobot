import discord
from discord import app_commands
from discord.ext import commands

from ..services import N8NClient

LOGS_CHANNEL = "logs"


class RecipeCommands(commands.Cog):
    """Commands for parsing and saving recipes to the recipe book."""

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
        name="recipe", description="Parse a recipe from a URL and save to recipe book"
    )
    @app_commands.describe(
        url="URL of the recipe page to parse",
    )
    async def parse_recipe(
        self,
        interaction: discord.Interaction,
        url: str,
    ):
        """Parse a recipe from URL and save to GitHub recipe book."""
        await interaction.response.defer(thinking=True)

        try:
            await self.log_to_channel(
                interaction.guild,
                f"`[Recipe]` Parsing <{url}> requested by {interaction.user.mention}",
            )

            payload = {
                "url": url,
                "guild_id": str(interaction.guild_id),
                "requested_by": str(interaction.user),
            }

            result = await self.n8n.trigger_webhook("recipe-parser", payload)

            if result.get("error"):
                error_msg = f"Failed to parse recipe: {result.get('message', 'Unknown error')}"
                await self.log_to_channel(
                    interaction.guild, f"`[Recipe]` Error: {error_msg}"
                )
                await interaction.followup.send(error_msg)
                return

            # Check for duplicate
            if result.get("duplicate"):
                await self.log_to_channel(
                    interaction.guild,
                    f"`[Recipe]` Duplicate detected: {result.get('title', 'Unknown')}",
                )
                await interaction.followup.send(
                    f"This recipe already exists in the recipe book: **{result.get('title')}**\n"
                    f"View it here: {result.get('existingUrl', 'N/A')}"
                )
                return

            # Success case
            title = result.get("title", "Unknown Recipe")
            commit_url = result.get("commitUrl", "")

            await self.log_to_channel(
                interaction.guild,
                f"`[Recipe]` Successfully saved: {title}",
            )

            # Build success message
            embed = discord.Embed(
                title=f"Recipe Saved: {title}",
                color=discord.Color.green(),
            )
            if result.get("description"):
                desc = result.get("description")
                embed.description = desc[:200] + "..." if len(desc) > 200 else desc
            if result.get("imageUrl"):
                embed.set_thumbnail(url=result.get("imageUrl"))
            embed.add_field(
                name="Ingredients",
                value=f"{result.get('ingredientCount', 0)} items",
                inline=True,
            )
            embed.add_field(
                name="Steps",
                value=f"{result.get('stepCount', 0)} steps",
                inline=True,
            )
            if commit_url:
                embed.add_field(
                    name="GitHub",
                    value=f"[View Commit]({commit_url})",
                    inline=False,
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            error_msg = f"Error parsing recipe: {e}"
            await self.log_to_channel(
                interaction.guild, f"`[Recipe]` Error: {error_msg}"
            )
            await interaction.followup.send(error_msg)


async def setup(bot: commands.Bot, n8n: N8NClient):
    await bot.add_cog(RecipeCommands(bot, n8n))
