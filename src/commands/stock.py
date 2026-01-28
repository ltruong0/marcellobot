import discord
from discord import app_commands
from discord.ext import commands

from ..services import N8NClient

LOGS_CHANNEL = "logs"
UBIQUITI_ALERTS_CHANNEL = "ubiquiti-stock-alerts"
BESTBUY_ALERTS_CHANNEL = "bestbuy-stock-alerts"
UNIVERSAL_ALERTS_CHANNEL = "stock-alerts"


class StockCommands(commands.Cog):
    """Commands for checking product stock status (Ubiquiti, Best Buy, Universal)."""

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

    async def send_stock_alert(
        self, guild: discord.Guild, message: str, channel_name: str
    ):
        """Send a stock alert to the specified alerts channel."""
        channel = await self.get_or_create_channel(guild, channel_name)
        await channel.send(message)

    async def get_channel_ids(
        self, guild: discord.Guild, alerts_channel_name: str
    ) -> tuple[str, str]:
        """Get or create the logs and alerts channels, return their IDs."""
        logs_channel = await self.get_or_create_channel(guild, LOGS_CHANNEL)
        alerts_channel = await self.get_or_create_channel(guild, alerts_channel_name)
        return str(logs_channel.id), str(alerts_channel.id)

    async def get_logs_channel_id(self, guild: discord.Guild) -> str:
        """Get or create the logs channel, return its ID."""
        logs_channel = await self.get_or_create_channel(guild, LOGS_CHANNEL)
        return str(logs_channel.id)

    @app_commands.command(
        name="ubiquiti-stock", description="Check Ubiquiti product stock"
    )
    @app_commands.describe(
        url="URL of the Ubiquiti product page to check",
    )
    async def check_ubiquiti_stock(
        self,
        interaction: discord.Interaction,
        url: str,
    ):
        """Check a Ubiquiti product for stock availability."""
        await interaction.response.defer(thinking=True)

        try:
            await self.log_to_channel(
                interaction.guild,
                f"`[Stock Check]` Checking <{url}> requested by {interaction.user.mention}",
            )

            payload = {
                "url": url,
                "guild_id": str(interaction.guild_id),
            }

            result = await self.n8n.trigger_webhook("ubiquiti-stock-check", payload)

            if result.get("error"):
                error_msg = f"Failed to check stock: {result.get('message', 'Unknown error')}"
                await self.log_to_channel(
                    interaction.guild, f"`[Stock Check]` Error: {error_msg}"
                )
                await interaction.followup.send(error_msg)
                return

            message = result.get("message", "Stock check complete")

            await self.log_to_channel(
                interaction.guild,
                f"`[Stock Check]` {result.get('productName', 'Unknown')}: "
                f"{'In Stock' if result.get('inStock') else 'Out of Stock'}",
            )

            if result.get("inStock"):
                alert_msg = (
                    f"**{result.get('productName', 'Product')}** is in stock!\n"
                    f"**Price:** {result.get('price', 'Unknown')}\n"
                    f"**Link:** <{url}>"
                )
                await self.send_stock_alert(
                    interaction.guild, alert_msg, UBIQUITI_ALERTS_CHANNEL
                )

            await interaction.followup.send(message)

        except Exception as e:
            error_msg = f"Error checking stock: {e}"
            await self.log_to_channel(
                interaction.guild, f"`[Stock Check]` Error: {error_msg}"
            )
            await interaction.followup.send(error_msg)

    @app_commands.command(
        name="ubiquiti-watch", description="Add a Ubiquiti product to the watch list"
    )
    @app_commands.describe(
        url="URL of the Ubiquiti product page to monitor",
        interval="Check interval in minutes (default: 5)",
    )
    async def add_to_watch_list(
        self,
        interaction: discord.Interaction,
        url: str,
        interval: int = 5,
    ):
        """Add a product to the stock watch list."""
        await interaction.response.defer(thinking=True)

        try:
            # Get channel IDs for n8n to use
            logs_channel_id, alerts_channel_id = await self.get_channel_ids(
                interaction.guild, UBIQUITI_ALERTS_CHANNEL
            )

            await self.log_to_channel(
                interaction.guild,
                f"`[Watch List]` Adding <{url}> (every {interval}m) by {interaction.user.mention}",
            )

            payload = {
                "action": "add",
                "url": url,
                "interval_minutes": interval,
                "guild_id": str(interaction.guild_id),
                "added_by": str(interaction.user),
                "logs_channel_id": logs_channel_id,
                "alerts_channel_id": alerts_channel_id,
            }

            result = await self.n8n.trigger_webhook("ubiquiti-stock-watch", payload)

            if result.get("error"):
                error_msg = f"Failed to add to watch list: {result.get('message', 'Unknown error')}"
                await self.log_to_channel(
                    interaction.guild, f"`[Watch List]` Error: {error_msg}"
                )
                await interaction.followup.send(error_msg)
                return

            message = result.get("message", f"Added to watch list: {url}")
            await interaction.followup.send(
                f"Added to watch list. Checking every {interval} minutes."
            )

        except Exception as e:
            error_msg = f"Error adding to watch list: {e}"
            await self.log_to_channel(
                interaction.guild, f"`[Watch List]` Error: {error_msg}"
            )
            await interaction.followup.send(error_msg)

    @app_commands.command(
        name="ubiquiti-unwatch",
        description="Remove a Ubiquiti product from the watch list",
    )
    @app_commands.describe(
        url="URL of the Ubiquiti product to stop monitoring",
    )
    async def remove_from_watch_list(
        self,
        interaction: discord.Interaction,
        url: str,
    ):
        """Remove a product from the stock watch list."""
        await interaction.response.defer(thinking=True)

        try:
            await self.log_to_channel(
                interaction.guild,
                f"`[Watch List]` Removing <{url}> by {interaction.user.mention}",
            )

            payload = {
                "action": "remove",
                "url": url,
                "guild_id": str(interaction.guild_id),
            }

            result = await self.n8n.trigger_webhook("ubiquiti-stock-watch", payload)

            if result.get("error"):
                error_msg = f"Failed to remove from watch list: {result.get('message', 'Unknown error')}"
                await self.log_to_channel(
                    interaction.guild, f"`[Watch List]` Error: {error_msg}"
                )
                await interaction.followup.send(error_msg)
                return

            message = result.get("message", f"Removed from watch list: {url}")
            await interaction.followup.send(f"Removed from watch list.")

        except Exception as e:
            error_msg = f"Error removing from watch list: {e}"
            await self.log_to_channel(
                interaction.guild, f"`[Watch List]` Error: {error_msg}"
            )
            await interaction.followup.send(error_msg)

    @app_commands.command(
        name="ubiquiti-watchlist", description="List all monitored Ubiquiti products"
    )
    async def list_watch_list(self, interaction: discord.Interaction):
        """List all products in the stock watch list."""
        await interaction.response.defer(thinking=True)

        try:
            payload = {
                "action": "list",
                "guild_id": str(interaction.guild_id),
            }

            result = await self.n8n.trigger_webhook("ubiquiti-stock-watch", payload)

            if result.get("error"):
                error_msg = f"Failed to get watch list: {result.get('message', 'Unknown error')}"
                await interaction.followup.send(error_msg)
                return

            message = result.get("message", "No products in watch list")
            await interaction.followup.send(message)

        except Exception as e:
            await interaction.followup.send(f"Error getting watch list: {e}")

    @app_commands.command(
        name="bestbuy-stock", description="Check Best Buy product stock"
    )
    @app_commands.describe(
        url="URL of the Best Buy product page to check",
    )
    async def check_bestbuy_stock(
        self,
        interaction: discord.Interaction,
        url: str,
    ):
        """Check a Best Buy product for stock availability."""
        await interaction.response.defer(thinking=True)

        try:
            await self.log_to_channel(
                interaction.guild,
                f"`[Stock Check]` Checking <{url}> requested by {interaction.user.mention}",
            )

            payload = {
                "url": url,
                "guild_id": str(interaction.guild_id),
            }

            result = await self.n8n.trigger_webhook("bestbuy-stock-check", payload)

            if result.get("error"):
                error_msg = f"Failed to check stock: {result.get('message', 'Unknown error')}"
                await self.log_to_channel(
                    interaction.guild, f"`[Stock Check]` Error: {error_msg}"
                )
                await interaction.followup.send(error_msg)
                return

            message = result.get("message", "Stock check complete")

            await self.log_to_channel(
                interaction.guild,
                f"`[Stock Check]` {result.get('productName', 'Unknown')}: "
                f"{'In Stock' if result.get('inStock') else 'Out of Stock'}",
            )

            if result.get("inStock"):
                alert_msg = (
                    f"**{result.get('productName', 'Product')}** is in stock!\n"
                    f"**Price:** {result.get('price', 'Unknown')}\n"
                    f"**Link:** <{url}>"
                )
                await self.send_stock_alert(
                    interaction.guild, alert_msg, BESTBUY_ALERTS_CHANNEL
                )

            await interaction.followup.send(message)

        except Exception as e:
            error_msg = f"Error checking stock: {e}"
            await self.log_to_channel(
                interaction.guild, f"`[Stock Check]` Error: {error_msg}"
            )
            await interaction.followup.send(error_msg)

    @app_commands.command(
        name="bestbuy-watch", description="Add a Best Buy product to the watch list"
    )
    @app_commands.describe(
        url="URL of the Best Buy product page to monitor",
        interval="Check interval in minutes (default: 5)",
    )
    async def add_bestbuy_to_watch_list(
        self,
        interaction: discord.Interaction,
        url: str,
        interval: int = 5,
    ):
        """Add a Best Buy product to the stock watch list."""
        await interaction.response.defer(thinking=True)

        try:
            # Get channel IDs for n8n to use
            logs_channel_id, alerts_channel_id = await self.get_channel_ids(
                interaction.guild, BESTBUY_ALERTS_CHANNEL
            )

            await self.log_to_channel(
                interaction.guild,
                f"`[Watch List]` Adding <{url}> (every {interval}m) by {interaction.user.mention}",
            )

            payload = {
                "action": "add",
                "url": url,
                "interval_minutes": interval,
                "guild_id": str(interaction.guild_id),
                "added_by": str(interaction.user),
                "logs_channel_id": logs_channel_id,
                "alerts_channel_id": alerts_channel_id,
            }

            result = await self.n8n.trigger_webhook("bestbuy-stock-watch", payload)

            if result.get("error"):
                error_msg = f"Failed to add to watch list: {result.get('message', 'Unknown error')}"
                await self.log_to_channel(
                    interaction.guild, f"`[Watch List]` Error: {error_msg}"
                )
                await interaction.followup.send(error_msg)
                return

            message = result.get("message", f"Added to watch list: {url}")
            await interaction.followup.send(
                f"Added to watch list. Checking every {interval} minutes."
            )

        except Exception as e:
            error_msg = f"Error adding to watch list: {e}"
            await self.log_to_channel(
                interaction.guild, f"`[Watch List]` Error: {error_msg}"
            )
            await interaction.followup.send(error_msg)

    @app_commands.command(
        name="bestbuy-unwatch",
        description="Remove a Best Buy product from the watch list",
    )
    @app_commands.describe(
        url="URL of the Best Buy product to stop monitoring",
    )
    async def remove_bestbuy_from_watch_list(
        self,
        interaction: discord.Interaction,
        url: str,
    ):
        """Remove a Best Buy product from the stock watch list."""
        await interaction.response.defer(thinking=True)

        try:
            await self.log_to_channel(
                interaction.guild,
                f"`[Watch List]` Removing <{url}> by {interaction.user.mention}",
            )

            payload = {
                "action": "remove",
                "url": url,
                "guild_id": str(interaction.guild_id),
            }

            result = await self.n8n.trigger_webhook("bestbuy-stock-watch", payload)

            if result.get("error"):
                error_msg = f"Failed to remove from watch list: {result.get('message', 'Unknown error')}"
                await self.log_to_channel(
                    interaction.guild, f"`[Watch List]` Error: {error_msg}"
                )
                await interaction.followup.send(error_msg)
                return

            message = result.get("message", f"Removed from watch list: {url}")
            await interaction.followup.send(f"Removed from watch list.")

        except Exception as e:
            error_msg = f"Error removing from watch list: {e}"
            await self.log_to_channel(
                interaction.guild, f"`[Watch List]` Error: {error_msg}"
            )
            await interaction.followup.send(error_msg)

    @app_commands.command(
        name="bestbuy-watchlist", description="List all monitored Best Buy products"
    )
    async def list_bestbuy_watch_list(self, interaction: discord.Interaction):
        """List all Best Buy products in the stock watch list."""
        await interaction.response.defer(thinking=True)

        try:
            payload = {
                "action": "list",
                "guild_id": str(interaction.guild_id),
            }

            result = await self.n8n.trigger_webhook("bestbuy-stock-watch", payload)

            if result.get("error"):
                error_msg = f"Failed to get watch list: {result.get('message', 'Unknown error')}"
                await interaction.followup.send(error_msg)
                return

            message = result.get("message", "No products in watch list")
            await interaction.followup.send(message)

        except Exception as e:
            await interaction.followup.send(f"Error getting watch list: {e}")

    @app_commands.command(
        name="stock-check",
        description="Universal stock checker using AI (works with any website)",
    )
    @app_commands.describe(
        url="URL of any product page to check",
    )
    async def check_universal_stock(
        self,
        interaction: discord.Interaction,
        url: str,
    ):
        """Check any product stock using AI analysis."""
        await interaction.response.defer(thinking=True)

        try:
            # Get logs channel ID for n8n to use
            logs_channel_id = await self.get_logs_channel_id(interaction.guild)

            await self.log_to_channel(
                interaction.guild,
                f"`[AI Stock Check]` Analyzing <{url}> requested by {interaction.user.mention}",
            )

            payload = {
                "url": url,
                "logs_channel_id": logs_channel_id,
            }

            result = await self.n8n.trigger_webhook("universal-stock-check", payload)

            if result.get("error"):
                error_msg = f"Failed to check stock: {result.get('message', 'Unknown error')}"
                await self.log_to_channel(
                    interaction.guild, f"`[AI Stock Check]` Error: {error_msg}"
                )
                await interaction.followup.send(error_msg)
                return

            message = result.get("message", "Stock check complete")
            confidence = result.get("confidence", "unknown")

            # Add confidence indicator to response
            confidence_emoji = {
                "high": "✓",
                "medium": "~",
                "low": "?",
            }.get(confidence.lower(), "")

            response_msg = f"{message}\n_Confidence: {confidence} {confidence_emoji}_"
            await interaction.followup.send(response_msg)

        except Exception as e:
            error_msg = f"Error checking stock: {e}"
            await self.log_to_channel(
                interaction.guild, f"`[AI Stock Check]` Error: {error_msg}"
            )
            await interaction.followup.send(error_msg)

    @app_commands.command(
        name="stock-watch", description="Add any product to AI-powered watch list"
    )
    @app_commands.describe(
        url="URL of any product page to monitor",
        interval="Check interval in minutes (default: 5)",
    )
    async def add_universal_to_watch_list(
        self,
        interaction: discord.Interaction,
        url: str,
        interval: int = 5,
    ):
        """Add any product to the universal AI stock watch list."""
        await interaction.response.defer(thinking=True)

        try:
            # Get channel IDs for n8n to use
            logs_channel_id, alerts_channel_id = await self.get_channel_ids(
                interaction.guild, UNIVERSAL_ALERTS_CHANNEL
            )

            await self.log_to_channel(
                interaction.guild,
                f"`[Universal Watch]` Adding <{url}> (every {interval}m) by {interaction.user.mention}",
            )

            payload = {
                "action": "add",
                "url": url,
                "interval_minutes": interval,
                "guild_id": str(interaction.guild_id),
                "added_by": str(interaction.user),
                "logs_channel_id": logs_channel_id,
                "alerts_channel_id": alerts_channel_id,
            }

            result = await self.n8n.trigger_webhook("universal-stock-watch", payload)

            if result.get("error"):
                error_msg = f"Failed to add to watch list: {result.get('message', 'Unknown error')}"
                await self.log_to_channel(
                    interaction.guild, f"`[Universal Watch]` Error: {error_msg}"
                )
                await interaction.followup.send(error_msg)
                return

            await interaction.followup.send(
                f"Added to AI watch list. Checking every {interval} minutes."
            )

        except Exception as e:
            error_msg = f"Error adding to watch list: {e}"
            await self.log_to_channel(
                interaction.guild, f"`[Universal Watch]` Error: {error_msg}"
            )
            await interaction.followup.send(error_msg)

    @app_commands.command(
        name="stock-unwatch",
        description="Remove a product from AI-powered watch list",
    )
    @app_commands.describe(
        url="URL of the product to stop monitoring",
    )
    async def remove_universal_from_watch_list(
        self,
        interaction: discord.Interaction,
        url: str,
    ):
        """Remove a product from the universal AI stock watch list."""
        await interaction.response.defer(thinking=True)

        try:
            await self.log_to_channel(
                interaction.guild,
                f"`[Universal Watch]` Removing <{url}> by {interaction.user.mention}",
            )

            payload = {
                "action": "remove",
                "url": url,
                "guild_id": str(interaction.guild_id),
            }

            result = await self.n8n.trigger_webhook("universal-stock-watch", payload)

            if result.get("error"):
                error_msg = f"Failed to remove from watch list: {result.get('message', 'Unknown error')}"
                await self.log_to_channel(
                    interaction.guild, f"`[Universal Watch]` Error: {error_msg}"
                )
                await interaction.followup.send(error_msg)
                return

            await interaction.followup.send(f"Removed from AI watch list.")

        except Exception as e:
            error_msg = f"Error removing from watch list: {e}"
            await self.log_to_channel(
                interaction.guild, f"`[Universal Watch]` Error: {error_msg}"
            )
            await interaction.followup.send(error_msg)

    @app_commands.command(
        name="stock-watchlist", description="List all AI-monitored products"
    )
    async def list_universal_watch_list(self, interaction: discord.Interaction):
        """List all products in the universal AI stock watch list."""
        await interaction.response.defer(thinking=True)

        try:
            payload = {
                "action": "list",
                "guild_id": str(interaction.guild_id),
            }

            result = await self.n8n.trigger_webhook("universal-stock-watch", payload)

            if result.get("error"):
                error_msg = f"Failed to get watch list: {result.get('message', 'Unknown error')}"
                await interaction.followup.send(error_msg)
                return

            message = result.get("message", "No products in watch list")
            await interaction.followup.send(message)

        except Exception as e:
            await interaction.followup.send(f"Error getting watch list: {e}")


async def setup(bot: commands.Bot, n8n: N8NClient):
    await bot.add_cog(StockCommands(bot, n8n))
