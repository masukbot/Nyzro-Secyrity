"""
Rinox Sentinel - Security Commands
/scan, /security, /whitelist, /blacklist
"""

import discord
from discord import app_commands
from discord.ext import commands

from ..ui.embeds import RinoxEmbed
from ..ui.views import ConfirmView
from ..core.security_engine import ScanType, ActionType


class SecurityCommands(commands.Cog):
    """Security and scanning commands"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="scan", description="🔍 Scan Message, Image, or User")
    @app_commands.describe(
        target="Message ID, User mention, or attachment URL",
        type="What to scan"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="Message", value="message"),
        app_commands.Choice(name="Image", value="image"),
        app_commands.Choice(name="User", value="user"),
        app_commands.Choice(name="Attachment", value="attachment"),
        app_commands.Choice(name="Server", value="server"),
        app_commands.Choice(name="Channel", value="channel"),
    ])
    @app_commands.checks.has_permissions(manage_messages=True)
    async def scan(self, interaction: discord.Interaction,
                  type: app_commands.Choice[str],
                  target: str = None):
        """Scan something for threats"""
        await interaction.response.defer(ephemeral=True)

        settings = await self.bot.db.get_guild_settings(interaction.guild_id)

        embed = RinoxEmbed.loading(f"Scanning {type.name}...")
        msg = await interaction.followup.send(embed=embed, ephemeral=True)

        try:
            if type.value == "message":
                if not target:
                    result = await self.bot.security.scan_message(
                        interaction.message or await self._get_last_message(interaction),
                        settings or {}
                    )
                else:
                    try:
                        msg_id = int(target)
                        channel = interaction.channel
                        message = await channel.fetch_message(msg_id)
                        result = await self.bot.security.scan_message(message, settings or {})
                    except ValueError:
                        embed = RinoxEmbed.error("Please provide a valid message ID.", "Invalid Input")
                        await msg.edit(embed=embed)
                        return

            elif type.value == "image":
                if not target:
                    ref = interaction.message or await self._get_last_message(interaction)
                    result = await self.bot.security.scan_image(
                        ref.attachments[0].url if ref and ref.attachments else None,
                        settings or {},
                        ref
                    )
                else:
                    result = await self.bot.security.scan_image(target, settings or {})

            elif type.value == "user":
                user = interaction.user
                if target:
                    user_id = target.strip("<@!>")
                    try:
                        user = await interaction.guild.fetch_member(int(user_id))
                    except:
                        pass
                result = await self.bot.security.scan_user(user, settings or {})

            elif type.value == "attachment":
                ref = interaction.message or await self._get_last_message(interaction)
                if not ref or not ref.attachments:
                    embed = RinoxEmbed.error("No attachments found in the referenced message.", "Scan Error")
                    await msg.edit(embed=embed)
                    return
                result = await self.bot.security.scan_attachment(
                    ref.attachments[0], settings or {}
                )

            elif type.value == "server":
                await self._scan_server(interaction, msg, settings or {})
                return

            elif type.value == "channel":
                await self._scan_channel(interaction, msg, target, settings or {})
                return

            else:
                embed = RinoxEmbed.error(f"Scan type '{type.name}' not yet implemented.", "Not Available")
                await msg.edit(embed=embed)
                return

            scan_embed = RinoxEmbed.scan_result(result)
            await msg.edit(embed=scan_embed)

        except Exception as e:
            self.bot.logger.error(f"Scan error: {e}")
            embed = RinoxEmbed.error(f"Scan failed: {str(e)[:200]}", "Scan Error")
            await msg.edit(embed=embed)

    @app_commands.command(name="security", description="🔒 Configure Security Settings")
    @app_commands.checks.has_permissions(administrator=True)
    async def security(self, interaction: discord.Interaction):
        """Open security configuration"""
        await interaction.response.defer(ephemeral=True)
        embed = RinoxEmbed.info("Security configuration panel", "🔒 Security")
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _scan_server(self, interaction: discord.Interaction,
                            msg: discord.WebhookMessage, settings: dict):
        """Scan ALL text channels in the server for threats"""
        embed = RinoxEmbed.loading("🔍 Scanning entire server for threats...")
        await msg.edit(embed=embed)

        total_scanned = 0
        threats_found = 0
        deleted = 0
        errors = 0

        for channel in interaction.guild.text_channels:
            if not channel.permissions_for(interaction.guild.me).read_message_history:
                continue
            try:
                async for message in channel.history(limit=50):
                    total_scanned += 1
                    result = await self.bot.security.scan_message(message, settings)
                    if result.is_threat:
                        threats_found += 1
                        if ActionType.DELETE in result.actions:
                            try:
                                await message.delete()
                                deleted += 1
                            except:
                                pass
                        # Log
                        await self.bot.db.log_security_event(
                            interaction.guild.id, "mass_scan",
                            user_id=message.author.id,
                            channel_id=channel.id,
                            message_id=message.id,
                            threat_level=result.threat_level,
                            risk_score=result.risk_score,
                            action_taken="delete" if ActionType.DELETE in result.actions else "log"
                        )
            except Exception as e:
                errors += 1
                continue

        embed = RinoxEmbed.create(
            title="📊 Server Scan Complete",
            color=RinoxEmbed.SUCCESS if threats_found == 0 else RinoxEmbed.WARNING
        )
        embed.add_field(name="📝 Messages Scanned", value=f"`{total_scanned}`", inline=True)
        embed.add_field(name="⚠️ Threats Found", value=f"`{threats_found}`", inline=True)
        embed.add_field(name="🗑️ Deleted", value=f"`{deleted}`", inline=True)
        if errors:
            embed.add_field(name="⚠️ Channels Skipped", value=f"`{errors}` (no permission)", inline=True)
        await msg.edit(embed=embed)

    async def _scan_channel(self, interaction: discord.Interaction,
                             msg: discord.WebhookMessage,
                             target: Optional[str], settings: dict):
        """Scan a specific channel for threats"""
        channel = None
        if target:
            try:
                channel_id = int(target.strip("<#>"))
                channel = interaction.guild.get_channel(channel_id)
            except:
                pass
        if not channel:
            channel = interaction.channel

        embed = RinoxEmbed.loading(f"🔍 Scanning {channel.mention}...")
        await msg.edit(embed=embed)

        total_scanned = 0
        threats_found = 0
        deleted = 0

        try:
            async for message in channel.history(limit=100):
                total_scanned += 1
                result = await self.bot.security.scan_message(message, settings)
                if result.is_threat:
                    threats_found += 1
                    if ActionType.DELETE in result.actions:
                        try:
                            await message.delete()
                            deleted += 1
                        except:
                            pass
        except Exception as e:
            embed = RinoxEmbed.error(f"Failed to scan channel: {str(e)[:200]}", "Scan Error")
            await msg.edit(embed=embed)
            return

        embed = RinoxEmbed.create(
            title=f"📊 Channel Scan Complete",
            color=RinoxEmbed.SUCCESS if threats_found == 0 else RinoxEmbed.WARNING
        )
        embed.add_field(name="📝 Scanned", value=f"`{total_scanned}`", inline=True)
        embed.add_field(name="⚠️ Threats", value=f"`{threats_found}`", inline=True)
        embed.add_field(name="🗑️ Deleted", value=f"`{deleted}`", inline=True)
        await msg.edit(embed=embed)

    async def _get_last_message(self, interaction: discord.Interaction):
        """Get the last non-bot message in channel before the command"""
        try:
            async for msg in interaction.channel.history(limit=5):
                if not msg.author.bot:
                    return msg
        except Exception:
            pass
        return None


async def setup(bot):
    await bot.add_cog(SecurityCommands(bot))