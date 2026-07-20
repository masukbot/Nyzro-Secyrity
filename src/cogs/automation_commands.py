"""
Rinox Sentinel - Automation Commands
"""

import discord
from discord import app_commands
from discord.ext import commands
import json

from ..ui.embeds import RinoxEmbed


class AutomationCommands(commands.Cog):
    """Automation rules configuration commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    automate_group = app_commands.Group(name="automate", description="⚙️ Configure automated security rules")
    
    @automate_group.command(name="threshold", description="📊 Set risk thresholds for automated moderation actions")
    @app_commands.describe(
        action="The action to configure (delete, warn, lockdown)",
        score="The minimum risk score (1-100) to trigger this action"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Auto-Delete Message", value="delete"),
        app_commands.Choice(name="Auto-Warn User", value="warn"),
        app_commands.Choice(name="Auto-Lockdown Channel", value="lockdown")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def set_threshold(self, interaction: discord.Interaction, 
                             action: app_commands.Choice[str], 
                             score: app_commands.Range[int, 1, 100]):
        """Set automated action thresholds"""
        await interaction.response.defer(ephemeral=True)
        
        settings = await self.bot.db.get_guild_settings(interaction.guild_id) or {}
        
        # Get moderation config dict
        mod_config = settings.get("moderation_config") or {}
        if isinstance(mod_config, str):
            try:
                mod_config = json.loads(mod_config)
            except:
                mod_config = {}
                
        # Update specific threshold
        key = f"auto_{action.value}_threshold"
        mod_config[key] = score
        
        await self.bot.db.update_guild_settings(
            interaction.guild_id,
            moderation_config=mod_config
        )
        
        embed = RinoxEmbed.success(
            f"Risk threshold for **{action.name}** set to `{score}/100`.",
            "⚙️ Threshold Updated"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @automate_group.command(name="toggle-module", description="🔒 Toggle security and anti-abuse modules")
    @app_commands.describe(
        module="The security module to toggle",
        enabled="Whether to enable or disable the module"
    )
    @app_commands.choices(module=[
        app_commands.Choice(name="Anti-Raid", value="anti_raid"),
        app_commands.Choice(name="Anti-Nuke", value="anti_nuke"),
        app_commands.Choice(name="Anti-Spam", value="anti_spam"),
        app_commands.Choice(name="Anti-Link", value="anti_link"),
        app_commands.Choice(name="Anti-Invite", value="anti_invite"),
        app_commands.Choice(name="Anti-Token Grabber", value="anti_token_grabber"),
        app_commands.Choice(name="Anti-Malware", value="anti_malware"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_module(self, interaction: discord.Interaction, 
                              module: app_commands.Choice[str], 
                              enabled: bool):
        """Toggle a security module"""
        await interaction.response.defer(ephemeral=True)
        
        settings = await self.bot.db.get_guild_settings(interaction.guild_id) or {}
        
        # Get security config dict
        sec_config = settings.get("security_config") or {}
        if isinstance(sec_config, str):
            try:
                sec_config = json.loads(sec_config)
            except:
                sec_config = {}
                
        # Update module status
        sec_config[module.value] = enabled
        
        await self.bot.db.update_guild_settings(
            interaction.guild_id,
            security_config=sec_config
        )
        
        status = "enabled" if enabled else "disabled"
        emoji = "🟢" if enabled else "🔴"
        
        embed = RinoxEmbed.success(
            f"{emoji} Module **{module.name}** has been **{status}**.",
            "⚙️ Module Settings Saved"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @automate_group.command(name="show", description="🔍 View current automation settings and active rules")
    @app_commands.checks.has_permissions(administrator=True)
    async def show_automation(self, interaction: discord.Interaction):
        """Show active automation settings"""
        await interaction.response.defer(ephemeral=True)
        
        settings = await self.bot.db.get_guild_settings(interaction.guild_id) or {}
        
        # Load configs
        mod_config = settings.get("moderation_config") or {}
        if isinstance(mod_config, str):
            try: mod_config = json.loads(mod_config)
            except: mod_config = {}
            
        sec_config = settings.get("security_config") or {}
        if isinstance(sec_config, str):
            try: sec_config = json.loads(sec_config)
            except: sec_config = {}
            
        embed = RinoxEmbed.create(
            title="⚙️ Automation Configuration",
            color=RinoxEmbed.PRIMARY
        )
        
        # Thresholds
        delete_t = mod_config.get("auto_delete_threshold", 60)
        warn_t = mod_config.get("auto_warn_threshold", 40)
        lockdown_t = mod_config.get("auto_lockdown_threshold", 80)
        
        thresholds_text = (
            f"🗑️ **Auto-Delete Messages:** Risk > `{delete_t}/100`\n"
            f"⚠️ **Auto-Warn Users:** Risk > `{warn_t}/100`\n"
            f"🔒 **Auto-Lockdown Channel:** Risk > `{lockdown_t}/100`"
        )
        embed.add_field(name="📊 Action Thresholds", value=thresholds_text, inline=False)
        
        # Modules
        modules = {
            "anti_raid": "Anti-Raid 🛡️",
            "anti_nuke": "Anti-Nuke 💥",
            "anti_spam": "Anti-Spam 📧",
            "anti_link": "Anti-Link 🔗",
            "anti_invite": "Anti-Invite 🎟️",
            "anti_token_grabber": "Anti-Token Grabber 🔑",
            "anti_malware": "Anti-Malware 🦠"
        }
        
        modules_text = ""
        for key, name in modules.items():
            is_enabled = sec_config.get(key, True)  # defaults to True
            status_emoji = "🟢 Enabled" if is_enabled else "🔴 Disabled"
            modules_text += f"**{name}:** {status_emoji}\n"
            
        embed.add_field(name="🔒 Protection Modules", value=modules_text, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AutomationCommands(bot))
