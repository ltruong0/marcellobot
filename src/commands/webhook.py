import discord
from discord import app_commands
from discord.ext import commands

from ..services import N8NClient


class WebhookCommands(commands.Cog):
    """Generic webhook trigger commands."""

    def __init__(self, bot: commands.Bot, n8n: N8NClient):
        self.bot = bot
        self.n8n = n8n

    @app_commands.command(name="trigger", description="Trigger a custom n8n workflow")
    @app_commands.describe(
        workflow="Webhook name/path to trigger",
        data="Optional JSON data to send",
    )
    async def trigger_workflow(
        self,
        interaction: discord.Interaction,
        workflow: str,
        data: str | None = None,
    ):
        """Trigger any n8n webhook by name."""
        await interaction.response.defer(thinking=True)

        try:
            import json

            payload = {"triggered_by": str(interaction.user)}

            if data:
                try:
                    extra = json.loads(data)
                    payload.update(extra)
                except json.JSONDecodeError:
                    # If not valid JSON, send as raw data
                    payload["data"] = data

            result = await self.n8n.trigger_webhook(workflow, payload)

            if result.get("error"):
                await interaction.followup.send(
                    f"Workflow failed: {result.get('message', 'Unknown error')}"
                )
                return

            message = result.get("message") or result.get("response")
            if message:
                await interaction.followup.send(f"**{workflow}**: {message}")
            else:
                await interaction.followup.send(
                    f"**{workflow}** triggered successfully!\n```json\n{json.dumps(result, indent=2)[:1800]}\n```"
                )

        except Exception as e:
            await interaction.followup.send(f"Error: {e}")


async def setup(bot: commands.Bot, n8n: N8NClient):
    await bot.add_cog(WebhookCommands(bot, n8n))
