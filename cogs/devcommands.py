import discord
from discord import app_commands
from discord.ext import commands

from helpers.embed import embedder


class DevCommands(commands.Cog, name="dev_commands"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Dev Commands cog loaded.")

    @commands.command(name="sync", description="sync up")
    async def sync(self, interaction: discord.Interaction) -> None:
        await self.bot.tree.sync()
        print("synced")

    @app_commands.command(name="test", description="Test command")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Test passed and tree synced.", delete_after=3
        )

    @app_commands.command(name="reload", description="reload cog")
    async def reload(self, interaction: discord.Interaction, cog: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await interaction.response.send_message(
                embed=embedder(f"Reloaded `{cog}`"), delete_after=3
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=embedder(f"Failed to reload `{cog}`: {e}"), delete_after=5
            )


async def setup(bot):
    await bot.add_cog(DevCommands(bot))
