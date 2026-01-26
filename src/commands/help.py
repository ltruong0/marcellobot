import discord
from discord import app_commands
from discord.ext import commands

from ..services import N8NClient


class HelpCommands(commands.Cog):
    """Help command for listing all available bot commands."""

    def __init__(self, bot: commands.Bot, n8n: N8NClient):
        self.bot = bot
        self.n8n = n8n

    @app_commands.command(name="help", description="Show all available commands")
    async def show_help(self, interaction: discord.Interaction):
        """Display all available bot commands and their usage."""
        embed = discord.Embed(
            title="MarcelloBot Commands",
            description="Homelab automation bot commands",
            color=discord.Color.blue(),
        )

        # Ubiquiti Stock Commands
        embed.add_field(
            name="Ubiquiti Stock Monitoring",
            value=(
                "`/ubiquiti-stock <url>` - Check if a product is in stock\n"
                "`/ubiquiti-watch <url> [interval]` - Add product to watch list (default: 5 min)\n"
                "`/ubiquiti-unwatch <url>` - Remove product from watch list\n"
                "`/ubiquiti-watchlist` - List all monitored products"
            ),
            inline=False,
        )

        # Best Buy Stock Commands
        embed.add_field(
            name="Best Buy Stock Monitoring",
            value=(
                "`/bestbuy-stock <url>` - Check if a product is in stock\n"
                "`/bestbuy-watch <url> [interval]` - Add product to watch list (default: 5 min)\n"
                "`/bestbuy-unwatch <url>` - Remove product from watch list\n"
                "`/bestbuy-watchlist` - List all monitored products"
            ),
            inline=False,
        )

        # Home Automation Commands
        embed.add_field(
            name="Home Automation",
            value=(
                "`/home <action> [target]` - Control home devices\n"
                "  Actions: `lights on`, `lights off`, `status`"
            ),
            inline=False,
        )

        # Status Commands
        embed.add_field(
            name="Status",
            value="`/status [service]` - Check homelab service status",
            inline=False,
        )

        # Recipe Commands
        embed.add_field(
            name="Recipe Book",
            value=(
                "`/recipe url:<url>` - Parse a recipe from a URL and save to recipe book\n"
                "`/recipe recipe_text:<text>` - Parse pasted recipe text and save to recipe book\n"
                "  Supports unstructured text with ingredients and instructions"
            ),
            inline=False,
        )

        # Workflow Commands
        embed.add_field(
            name="Workflows",
            value="`/trigger <workflow> [data]` - Trigger a custom n8n workflow",
            inline=False,
        )

        embed.set_footer(text="<required> [optional]")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot, n8n: N8NClient):
    await bot.add_cog(HelpCommands(bot, n8n))
