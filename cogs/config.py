import discord
from discord.ext import commands
import asyncio
import json

class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_group(name="config", description="Configure ModMail settings")
    @commands.has_permissions(administrator=True)
    async def config_group(self, ctx):
        """Configure ModMail settings"""
        if ctx.invoked_subcommand is None:
            await self.show_config(ctx)
    
    @config_group.command(name="show", description="Show current ModMail configuration")
    @commands.has_permissions(administrator=True)
    async def show_config(self, ctx):
        """Show current ModMail configuration"""
        config = self.bot.config
        
        embed = discord.Embed(
            title="ModMail Configuration",
            color=config["color"]["default"]
        )
        
        # Get guild name
        guild_id = config.get("guild_id")
        guild_name = "Not set"
        if guild_id:
            guild = self.bot.get_guild(int(guild_id))
            if guild:
                guild_name = f"{guild.name} ({guild_id})"
        
        # Get category name
        category_id = config.get("modmail_category")
        category_name = "Not set"
        if category_id and guild_id:
            guild = self.bot.get_guild(int(guild_id))
            if guild:
                category = guild.get_channel(int(category_id))
                if category:
                    category_name = f"{category.name} ({category_id})"
        
        # Get log channel name
        log_channel_id = config.get("log_channel")
        log_channel_name = "Not set"
        if log_channel_id and guild_id:
            guild = self.bot.get_guild(int(guild_id))
            if guild:
                channel = guild.get_channel(int(log_channel_id))
                if channel:
                    log_channel_name = f"{channel.name} ({log_channel_id})"
        
        # Get staff role names
        staff_roles = config.get("staff_roles", [])
        staff_role_names = []
        if staff_roles and guild_id:
            guild = self.bot.get_guild(int(guild_id))
            if guild:
                for role_id in staff_roles:
                    role = guild.get_role(int(role_id))
                    if role:
                        staff_role_names.append(f"{role.name} ({role_id})")
        
        staff_roles_text = "\n".join(staff_role_names) if staff_role_names else "None"
        
        # Get blocked users
        blocked_users = config.get("blocked_users", [])
        blocked_users_text = ""
        for user_id in blocked_users:
            user = self.bot.get_user(int(user_id))
            if user:
                blocked_users_text += f"{user.name} ({user_id})\n"
            else:
                blocked_users_text += f"Unknown User ({user_id})\n"
        
        if not blocked_users_text:
            blocked_users_text = "None"
        
        # Add fields
        embed.add_field(name="Prefix", value=config.get("prefix", "!"), inline=True)
        embed.add_field(name="Status", value=config.get("status", "DM me for help!"), inline=True)
        embed.add_field(name="Thread Close Time", value=f"{config.get('thread_close_time', 12)} hours", inline=True)
        embed.add_field(name="Guild", value=guild_name, inline=False)
        embed.add_field(name="ModMail Category", value=category_name, inline=False)
        embed.add_field(name="Log Channel", value=log_channel_name, inline=False)
        embed.add_field(name="Staff Roles", value=staff_roles_text, inline=False)
        
        # Create a second embed for blocked users to avoid hitting the field limit
        blocked_embed = discord.Embed(
            title="Blocked Users",
            description=blocked_users_text,
            color=config["color"]["default"]
        )
        
        await ctx.send(embeds=[embed, blocked_embed])
    
    @config_group.command(name="prefix", description="Set the command prefix")
    @commands.has_permissions(administrator=True)
    async def set_prefix(self, ctx, prefix: str):
        """Set the command prefix"""
        self.bot.config["prefix"] = prefix
        self.bot.save_config()
        
        embed = discord.Embed(
            title="Prefix Updated",
            description=f"Command prefix has been updated to: `{prefix}`",
            color=self.bot.config["color"]["success"]
        )
        await ctx.send(embed=embed)
    
    @config_group.command(name="status", description="Set the bot status message")
    @commands.has_permissions(administrator=True)
    async def set_status(self, ctx, *, status: str):
        """Set the bot status message"""
        self.bot.config["status"] = status
        self.bot.save_config()
        
        # Update presence
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=status
        )
        await self.bot.change_presence(activity=activity)
        
        embed = discord.Embed(
            title="Status Updated",
            description=f"Bot status has been updated to: `{status}`",
            color=self.bot.config["color"]["success"]
        )
        await ctx.send(embed=embed)
    
    @config_group.command(name="category", description="Set the ModMail category")
    @commands.has_permissions(administrator=True)
    async def set_category(self, ctx, category_id: str):
        """Set the ModMail category"""
        try:
            category_id = int(category_id)
            category = ctx.guild.get_channel(category_id)
            
            if not category or not isinstance(category, discord.CategoryChannel):
                raise ValueError("Invalid category")
                
            self.bot.config["modmail_category"] = str(category_id)
            self.bot.save_config()
            
            embed = discord.Embed(
                title="Category Updated",
                description=f"ModMail category has been set to: {category.name}",
                color=self.bot.config["color"]["success"]
            )
            await ctx.send(embed=embed)
            
        except (ValueError, discord.HTTPException):
            embed = discord.Embed(
                title="Error",
                description="Please provide a valid category ID.",
                color=self.bot.config["color"]["error"]
            )
            await ctx.send(embed=embed)
    
    @config_group.command(name="log_channel", description="Set the log channel")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx, channel_id: str):
        """Set the log channel"""
        try:
            channel_id = int(channel_id)
            channel = ctx.guild.get_channel(channel_id)
            
            if not channel or not isinstance(channel, discord.TextChannel):
                raise ValueError("Invalid channel")
                
            self.bot.config["log_channel"] = str(channel_id)
            self.bot.save_config()
            
            embed = discord.Embed(
                title="Log Channel Updated",
                description=f"Log channel has been set to: {channel.mention}",
                color=self.bot.config["color"]["success"]
            )
            await ctx.send(embed=embed)
            
        except (ValueError, discord.HTTPException):
            embed = discord.Embed(
                title="Error",
                description="Please provide a valid text channel ID.",
                color=self.bot.config["color"]["error"]
            )
            await ctx.send(embed=embed)
    
    @config_group.command(name="add_staff", description="Add a staff role")
    @commands.has_permissions(administrator=True)
    async def add_staff_role(self, ctx, role_id: str):
        """Add a staff role"""
        try:
            role_id = int(role_id)
            role = ctx.guild.get_role(role_id)
            
            if not role:
                raise ValueError("Invalid role")
                
            if str(role_id) not in self.bot.config["staff_roles"]:
                self.bot.config["staff_roles"].append(str(role_id))
                self.bot.save_config()
                
                embed = discord.Embed(
                    title="Staff Role Added",
                    description=f"Added {role.name} to staff roles.",
                    color=self.bot.config["color"]["success"]
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Role Already Added",
                    description=f"{role.name} is already a staff role.",
                    color=self.bot.config["color"]["warning"]
                )
                await ctx.send(embed=embed)
            
        except (ValueError, discord.HTTPException):
            embed = discord.Embed(
                title="Error",
                description="Please provide a valid role ID.",
                color=self.bot.config["color"]["error"]
            )
            await ctx.send(embed=embed)
    
    @config_group.command(name="remove_staff", description="Remove a staff role")
    @commands.has_permissions(administrator=True)
    async def remove_staff_role(self, ctx, role_id: str):
        """Remove a staff role"""
        try:
            role_id = int(role_id)
            role = ctx.guild.get_role(role_id)
            
            if str(role_id) in self.bot.config["staff_roles"]:
                self.bot.config["staff_roles"].remove(str(role_id))
                self.bot.save_config()
                
                role_name = role.name if role else f"Unknown Role ({role_id})"
                
                embed = discord.Embed(
                    title="Staff Role Removed",
                    description=f"Removed {role_name} from staff roles.",
                    color=self.bot.config["color"]["success"]
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Role Not Found",
                    description=f"Role ID {role_id} is not in the staff roles list.",
                    color=self.bot.config["color"]["warning"]
                )
                await ctx.send(embed=embed)
            
        except (ValueError, discord.HTTPException):
            embed = discord.Embed(
                title="Error",
                description="Please provide a valid role ID.",
                color=self.bot.config["color"]["error"]
            )
            await ctx.send(embed=embed)
    
    @config_group.command(name="unblock", description="Unblock a user")
    @commands.has_permissions(administrator=True)
    async def unblock_user(self, ctx, user_id: str):
        """Unblock a user"""
        try:
            user_id = int(user_id)
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            
            if str(user_id) in self.bot.config["blocked_users"]:
                self.bot.config["blocked_users"].remove(str(user_id))
                self.bot.save_config()
                
                embed = discord.Embed(
                    title="User Unblocked",
                    description=f"Unblocked {user.name} ({user_id}) from using ModMail.",
                    color=self.bot.config["color"]["success"]
                )
                await ctx.send(embed=embed)
                
                # Notify user they are unblocked
                try:
                    user_embed = discord.Embed(
                        title="You Have Been Unblocked",
                        description="You have been unblocked from using the ModMail system.",
                        color=self.bot.config["color"]["success"],
                        timestamp=discord.utils.utcnow()
                    )
                    await user.send(embed=user_embed)
                except discord.HTTPException:
                    pass
            else:
                embed = discord.Embed(
                    title="User Not Blocked",
                    description=f"User {user.name} ({user_id}) is not blocked.",
                    color=self.bot.config["color"]["warning"]
                )
                await ctx.send(embed=embed)
            
        except (ValueError, discord.HTTPException):
            embed = discord.Embed(
                title="Error",
                description="Please provide a valid user ID.",
                color=self.bot.config["color"]["error"]
            )
            await ctx.send(embed=embed)
    
    @config_group.command(name="close_time", description="Set thread auto-close time (in hours)")
    @commands.has_permissions(administrator=True)
    async def set_close_time(self, ctx, hours: int):
        """Set thread auto-close time (in hours)"""
        if hours < 0:
            embed = discord.Embed(
                title="Error",
                description="Please provide a positive number of hours.",
                color=self.bot.config["color"]["error"]
            )
            await ctx.send(embed=embed)
            return
            
        self.bot.config["thread_close_time"] = hours
        self.bot.save_config()
        
        embed = discord.Embed(
            title="Close Time Updated",
            description=f"Thread auto-close time set to {hours} hours.",
            color=self.bot.config["color"]["success"]
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Config(bot))