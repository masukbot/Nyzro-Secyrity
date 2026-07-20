"""
Rinox Sentinel - Server Management Commands
Purge, Lockdown, Clone, Slowmode, Roles, Info
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List

from ..ui.embeds import RinoxEmbed
from ..ui.views import ConfirmView


class ManagementCommands(commands.Cog):
    """Advanced server management"""

    def __init__(self, bot):
        self.bot = bot

    # ========================
    # PURGE
    # ========================
    @app_commands.command(name="purge", description="🧹 Bulk delete messages")
    @app_commands.describe(
        count="Number of messages to delete (1-100)",
        user="Only delete messages from this user (optional)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction,
                    count: app_commands.Range[int, 1, 100],
                    user: Optional[discord.Member] = None):
        """Bulk delete messages"""
        await interaction.response.defer(ephemeral=True)

        def check(msg):
            if user and msg.author.id != user.id:
                return False
            return True

        try:
            deleted = await interaction.channel.purge(limit=count, check=check, bulk=True)
            embed = RinoxEmbed.success(
                f"Deleted `{len(deleted)}` messages{f' from {user.mention}' if user else ''}.",
                "🧹 Purge Complete"
            )
        except discord.Forbidden:
            embed = RinoxEmbed.error("I don't have permission to delete messages here.", "❌ No Permission")
        except Exception as e:
            embed = RinoxEmbed.error(f"Purge failed: {str(e)[:100]}", "❌ Error")

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ========================
    # SLOWMODE
    # ========================
    @app_commands.command(name="slowmode", description="⏱️ Set slowmode for a channel")
    @app_commands.describe(
        seconds="Slowmode in seconds (0=off, 1-21600)",
        channel="Channel to apply to (default: current)"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction,
                       seconds: app_commands.Range[int, 0, 21600],
                       channel: Optional[discord.TextChannel] = None):
        """Set channel slowmode"""
        await interaction.response.defer(ephemeral=True)

        target = channel or interaction.channel
        try:
            await target.edit(slowmode_delay=seconds)
            if seconds > 0:
                embed = RinoxEmbed.success(
                    f"Slowmode set to `{seconds}s` in {target.mention}.",
                    "⏱️ Slowmode Updated"
                )
            else:
                embed = RinoxEmbed.success(
                    f"Slowmode **disabled** in {target.mention}.",
                    "⏱️ Slowmode Off"
                )
        except discord.Forbidden:
            embed = RinoxEmbed.error("No permission to edit this channel.", "❌ Error")
        except Exception as e:
            embed = RinoxEmbed.error(str(e)[:100], "❌ Error")

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ========================
    # LOCKDOWN / UNLOCK
    # ========================
    @app_commands.command(name="lockdown", description="🔒 Lock a channel (deny send messages for @everyone)")
    @app_commands.describe(
        channel="Channel to lock (default: current)",
        reason="Reason for lockdown"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown(self, interaction: discord.Interaction,
                       channel: Optional[discord.TextChannel] = None,
                       reason: str = "No reason provided"):
        """Lock a channel"""
        await interaction.response.defer(ephemeral=True)

        target = channel or interaction.channel
        try:
            everyone = interaction.guild.default_role
            current_perms = target.overwrites_for(everyone)
            current_perms.send_messages = False
            await target.set_permissions(everyone, overwrite=current_perms, reason=reason)

            embed = RinoxEmbed.create(
                title="🔒 Channel Locked",
                description=f"{target.mention} has been locked.\n**Reason:** {reason}",
                color=RinoxEmbed.DANGER
            )
            await target.send(embed=embed)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = RinoxEmbed.error("No permission to lock this channel.", "❌ Error")
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="unlock", description="🔓 Unlock a channel")
    @app_commands.describe(
        channel="Channel to unlock (default: current)",
        reason="Reason"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def unlock(self, interaction: discord.Interaction,
                     channel: Optional[discord.TextChannel] = None,
                     reason: str = "No reason provided"):
        """Unlock a channel"""
        await interaction.response.defer(ephemeral=True)

        target = channel or interaction.channel
        try:
            everyone = interaction.guild.default_role
            current_perms = target.overwrites_for(everyone)
            current_perms.send_messages = None
            await target.set_permissions(everyone, overwrite=current_perms, reason=reason)

            embed = RinoxEmbed.create(
                title="🔓 Channel Unlocked",
                description=f"{target.mention} has been unlocked.\n**Reason:** {reason}",
                color=RinoxEmbed.SUCCESS
            )
            await target.send(embed=embed)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = RinoxEmbed.error("No permission to unlock this channel.", "❌ Error")
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ========================
    # CLONE CHANNEL
    # ========================
    @app_commands.command(name="clone", description="📋 Clone a channel")
    @app_commands.describe(
        channel="Channel to clone",
        name="New channel name (optional)",
        reason="Reason"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def clone(self, interaction: discord.Interaction,
                    channel: discord.TextChannel,
                    name: Optional[str] = None,
                    reason: str = "Channel cloned by moderator"):
        """Clone a channel with all settings"""
        await interaction.response.defer(ephemeral=True)

        try:
            new_channel = await channel.clone(name=name, reason=reason)

            # Maintain position
            await new_channel.edit(position=channel.position + 1)

            embed = RinoxEmbed.success(
                f"Cloned {channel.mention} → {new_channel.mention}",
                "📋 Channel Cloned"
            )
        except discord.Forbidden:
            embed = RinoxEmbed.error("No permission to clone channels.", "❌ Error")
        except Exception as e:
            embed = RinoxEmbed.error(str(e)[:100], "❌ Error")

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ========================
    # NICKNAME
    # ========================
    @app_commands.command(name="nick", description="✏️ Change a user's nickname")
    @app_commands.describe(
        user="User to rename",
        nickname="New nickname (leave empty to reset)"
    )
    @app_commands.checks.has_permissions(manage_nicknames=True)
    async def nick(self, interaction: discord.Interaction,
                   user: discord.Member,
                   nickname: Optional[str] = None):
        """Change or reset a nickname"""
        await interaction.response.defer(ephemeral=True)

        try:
            await user.edit(nick=nickname)
            if nickname:
                embed = RinoxEmbed.success(
                    f"{user.mention} nickname set to: `{nickname}`",
                    "✏️ Nickname Changed"
                )
            else:
                embed = RinoxEmbed.success(
                    f"{user.mention} nickname has been **reset**.",
                    "✏️ Nickname Reset"
                )
        except discord.Forbidden:
            embed = RinoxEmbed.error("No permission to change this user's nickname.", "❌ Error")
        except Exception as e:
            embed = RinoxEmbed.error(str(e)[:100], "❌ Error")

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ========================
    # ROLE MANAGEMENT
    # ========================
    @app_commands.command(name="giverole", description="🎭 Give a role to a user")
    @app_commands.describe(
        user="User to give role to",
        role="Role to give"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def giverole(self, interaction: discord.Interaction,
                       user: discord.Member,
                       role: discord.Role):
        """Give a role to a user"""
        await interaction.response.defer(ephemeral=True)

        if role >= interaction.guild.me.top_role:
            embed = RinoxEmbed.error("That role is higher than my highest role!", "❌ Cannot Assign")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            await user.add_roles(role, reason=f"Given by {interaction.user}")
            embed = RinoxEmbed.success(
                f"Gave {role.mention} to {user.mention}.",
                "🎭 Role Added"
            )
        except discord.Forbidden:
            embed = RinoxEmbed.error("No permission to assign this role.", "❌ Error")
        except Exception as e:
            embed = RinoxEmbed.error(str(e)[:100], "❌ Error")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="takerole", description="🎭 Remove a role from a user")
    @app_commands.describe(
        user="User to remove role from",
        role="Role to remove"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def takerole(self, interaction: discord.Interaction,
                       user: discord.Member,
                       role: discord.Role):
        """Remove a role from a user"""
        await interaction.response.defer(ephemeral=True)

        try:
            await user.remove_roles(role, reason=f"Removed by {interaction.user}")
            embed = RinoxEmbed.success(
                f"Removed {role.mention} from {user.mention}.",
                "🎭 Role Removed"
            )
        except discord.Forbidden:
            embed = RinoxEmbed.error("No permission to remove this role.", "❌ Error")
        except Exception as e:
            embed = RinoxEmbed.error(str(e)[:100], "❌ Error")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="massrole", description="👥 Bulk role management")
    @app_commands.describe(
        action="Add or remove role",
        role="Role to add/remove",
        users="Users to modify (space-separated mentions or IDs)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add Role", value="add"),
        app_commands.Choice(name="Remove Role", value="remove"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def massrole(self, interaction: discord.Interaction,
                       action: app_commands.Choice[str],
                       role: discord.Role,
                       users: str):
        """Bulk add/remove roles"""
        await interaction.response.defer(ephemeral=True)

        member_ids = []
        for part in users.split():
            part = part.strip("<@!>")
            try:
                member_ids.append(int(part))
            except ValueError:
                continue

        if not member_ids:
            embed = RinoxEmbed.error("No valid users found.", "❌ Invalid Users")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        success = 0
        failed = 0
        is_add = action.value == "add"

        for mid in member_ids:
            member = interaction.guild.get_member(mid)
            if not member:
                failed += 1
                continue
            try:
                if is_add:
                    await member.add_roles(role)
                else:
                    await member.remove_roles(role)
                success += 1
            except:
                failed += 1

        embed = RinoxEmbed.success(
            f"{'Added' if is_add else 'Removed'} {role.mention}\n"
            f"✅ Success: `{success}`\n"
            f"❌ Failed: `{failed}`",
            "👥 Mass Role Complete"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ========================
    # INFO COMMANDS
    # ========================
    @app_commands.command(name="serverinfo", description="📊 Show server information")
    async def serverinfo(self, interaction: discord.Interaction):
        """Show detailed server info"""
        guild = interaction.guild
        embed = RinoxEmbed.create(
            title=f"📊 {guild.name}",
            color=RinoxEmbed.PRIMARY
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="🆔 ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="📅 Created", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)

        embed.add_field(name="👥 Members", value=f"`{guild.member_count}`", inline=True)
        embed.add_field(name="💬 Channels", value=f"`{len(guild.channels)}`", inline=True)
        embed.add_field(name="🎭 Roles", value=f"`{len(guild.roles)}`", inline=True)

        embed.add_field(name="🚀 Boost Level", value=f"`{guild.premium_tier}`", inline=True)
        embed.add_field(name="⭐ Boosts", value=f"`{guild.premium_subscription_count}`", inline=True)
        embed.add_field(name="🌍 Locale", value=f"`{guild.preferred_locale}`", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="👤 Show user information")
    @app_commands.describe(user="User to check (default: yourself)")
    async def userinfo(self, interaction: discord.Interaction,
                       user: Optional[discord.Member] = None):
        """Show user details"""
        user = user or interaction.user
        embed = RinoxEmbed.create(
            title=f"👤 {user.name}",
            color=user.color or RinoxEmbed.PRIMARY
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(name="🆔 ID", value=f"`{user.id}`", inline=True)
        embed.add_field(name="📛 Display Name", value=user.display_name, inline=True)
        embed.add_field(name="🤖 Bot", value="Yes" if user.bot else "No", inline=True)

        embed.add_field(name="📅 Joined", value=f"<t:{int(user.joined_at.timestamp())}:R>" if user.joined_at else "Unknown", inline=True)
        embed.add_field(name="📅 Registered", value=f"<t:{int(user.created_at.timestamp())}:R>", inline=True)

        roles = [r.mention for r in user.roles if r != interaction.guild.default_role]
        if roles:
            embed.add_field(name=f"🎭 Roles ({len(roles)})", value=" ".join(roles[:10]), inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roleinfo", description="🎭 Show role information")
    @app_commands.describe(role="Role to check")
    async def roleinfo(self, interaction: discord.Interaction, role: discord.Role):
        """Show role details"""
        embed = RinoxEmbed.create(
            title=f"🎭 {role.name}",
            color=role.color or RinoxEmbed.NEUTRAL
        )
        embed.add_field(name="🆔 ID", value=f"`{role.id}`", inline=True)
        embed.add_field(name="🎨 Color", value=str(role.color).upper(), inline=True)
        embed.add_field(name="📌 Position", value=f"`{role.position}`", inline=True)
        embed.add_field(name="👥 Members", value=f"`{len(role.members)}`", inline=True)
        embed.add_field(name="🔒 Managed", value="Yes" if role.managed else "No", inline=True)
        embed.add_field(name="📢 Hoist", value="Yes" if role.hoist else "No", inline=True)
        embed.add_field(name="📅 Created", value=f"<t:{int(role.created_at.timestamp())}:R>", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="channelinfo", description="💬 Show channel information")
    @app_commands.describe(channel="Channel to check (default: current)")
    async def channelinfo(self, interaction: discord.Interaction,
                          channel: Optional[discord.TextChannel] = None):
        """Show channel details"""
        channel = channel or interaction.channel
        embed = RinoxEmbed.create(
            title=f"💬 #{channel.name}",
            color=RinoxEmbed.INFO
        )
        embed.add_field(name="🆔 ID", value=f"`{channel.id}`", inline=True)
        embed.add_field(name="📁 Category", value=channel.category.name if channel.category else "None", inline=True)
        embed.add_field(name="📌 Position", value=f"`{channel.position}`", inline=True)
        embed.add_field(name="👥 Topic", value=channel.topic or "No topic", inline=False)
        embed.add_field(name="⏱️ Slowmode", value=f"`{channel.slowmode_delay}s`", inline=True)
        embed.add_field(name="📅 Created", value=f"<t:{int(channel.created_at.timestamp())}:R>", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="boostinfo", description="⭐ Show server boost information")
    async def boostinfo(self, interaction: discord.Interaction):
        """Show boost status"""
        guild = interaction.guild
        embed = RinoxEmbed.create(
            title="⭐ Server Boost Status",
            color=RinoxEmbed.PREMIUM
        )
        embed.add_field(name="🚀 Level", value=f"`{guild.premium_tier}`", inline=True)
        embed.add_field(name="⭐ Boosts", value=f"`{guild.premium_subscription_count}`", inline=True)
        embed.add_field(name="👑 Booster Role", value=guild.premium_subscriber_role.mention if guild.premium_subscriber_role else "None", inline=False)

        boosters = sorted(guild.premium_subscribers, key=lambda m: m.premium_since or discord.utils.utcnow())[:10]
        if boosters:
            booster_list = "\n".join([f"• {m.mention}" for m in boosters])
            embed.add_field(name="Top Boosters", value=booster_list, inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(ManagementCommands(bot))