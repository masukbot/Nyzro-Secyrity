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
        
    @app_commands.command(name="restore", description="📥 Restore from Backup")
    @app_commands.checks.has_permissions(administrator=True)
    async def restore(self, interaction: discord.Interaction):
        """Restore from backup"""
        await interaction.response.defer(ephemeral=True)
        
        backups = await self.bot.db.get_backups(interaction.guild_id)
        
        if not backups:
            embed = RinoxEmbed.error("No backups found.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
            
        embed = RinoxEmbed.info(
            f"Found `{len(backups)}` backups. Use `/setup` to manage.",
            "📥 Restore"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(BackupCommands(bot))
