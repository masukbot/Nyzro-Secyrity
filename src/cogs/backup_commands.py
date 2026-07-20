"""
Rinox Sentinel - Backup Commands
/backup, /restore
"""

import discord
from discord import app_commands
from discord.ext import commands
import json

from ..ui.embeds import RinoxEmbed


class BackupCommands(commands.Cog):
    """Backup and restore"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="backup", description="💾 Create Server Backup")
    @app_commands.describe(name="Backup name")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup(self, interaction: discord.Interaction,
                    name: str = None):
        """Create backup"""
        await interaction.response.defer(ephemeral=True)
        
        embed = RinoxEmbed.loading("Creating backup...")
        msg = await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Gather data
        guild = interaction.guild
        
        backup_data = {
            "channels": [
                {
                    "name": c.name,
                    "type": str(c.type),
                    "position": c.position,
                    "category": c.category.name if c.category else None
                }
                for c in guild.channels
            ],
            "roles": [
                {
                    "name": r.name,
                    "color": str(r.color),
                    "permissions": r.permissions.value,
                    "position": r.position
                }
                for r in guild.roles
                if not r.is_default()
            ],
            "settings": await self.bot.db.get_guild_settings(guild.id)
        }
        
        backup_json = json.dumps(backup_data)
        
        await self.bot.db.create_backup(
            guild.id,
            name or f"Backup_{discord.utils.utcnow().strftime('%Y%m%d_%H%M%S')}",
            backup_data,
            len(backup_json),
            interaction.user.id
        )
        
        embed = RinoxEmbed.success(
            f"**Channels:** `{len(backup_data['channels'])}`\n"
            f"**Roles:** `{len(backup_data['roles'])}`\n"
            f"**Size:** `{len(backup_json):,} bytes`",
            "💾 Backup Created"
        )
        await msg.edit(embed=embed)
        
    @app_commands.command(name="restore", description="📥 Restore Guild Settings from Backup")
    @app_commands.describe(backup_id="Backup ID (use /backup list to find)")
    @app_commands.checks.has_permissions(administrator=True)
    async def restore(self, interaction: discord.Interaction,
                     backup_id: str = None):
        """Restore from backup"""
        await interaction.response.defer(ephemeral=True)
        
        backups = await self.bot.db.get_backups(interaction.guild_id)
        
        if not backups:
            embed = RinoxEmbed.error("No backups found.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if not backup_id:
            lines = []
            for b in backups[:10]:
                bid = b.get("id", "?")
                bname = b.get("backup_name", "Unnamed")
                bdate = str(b.get("created_at", "?"))[:10]
                lines.append(f"`{bid}` — {bname} ({bdate})")
            embed = RinoxEmbed.info(
                "Available backups:\n" + "\n".join(lines) + 
                "\n\nUse `/restore backup_id:<ID>` to restore.",
                "📥 Restore"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        backup = None
        for b in backups:
            if str(b.get("id")) == backup_id:
                backup = b
                break
        
        if not backup:
            embed = RinoxEmbed.error(f"No backup found with ID `{backup_id}`.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        data = backup.get("backup_data")
        if isinstance(data, str):
            try: data = json.loads(data)
            except:
                embed = RinoxEmbed.error("Failed to parse backup data.")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        settings = data.get("settings") if data else None
        if not settings:
            embed = RinoxEmbed.error("Backup contains no guild settings data.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Restore settings (skip guild_id and primary keys)
        safe_keys = {"ai_provider", "ai_model", "temperature", "max_tokens",
                     "security_config", "moderation_config", "log_channel_id",
                     "language", "custom_prompts", "enabled_features"}
        update = {k: v for k, v in settings.items() if k in safe_keys and not k.startswith("_")}
        
        if update:
            await self.bot.db.update_guild_settings(interaction.guild_id, **update)
            embed = RinoxEmbed.success(
                f"Restored {len(update)} settings from backup `{backup_id}`.",
                "📥 Restore Complete"
            )
        else:
            embed = RinoxEmbed.error("No compatible settings found in this backup.")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(BackupCommands(bot))
