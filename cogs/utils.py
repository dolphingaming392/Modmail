import discord
from discord.ext import commands
import datetime
import io
import json

class ThreadLogView(discord.ui.View):
    def __init__(self, thread_id, bot):
        super().__init__(timeout=None)
        self.thread_id = thread_id
        self.bot = bot
    
    @discord.ui.button(label="Export Thread", style=discord.ButtonStyle.primary, emoji="📤", custom_id="thread:export")
    async def export_thread(self, interaction: discord.Interaction, button: discord.ui.Button):
        utils_cog = self.bot.get_cog("Utils")
        if utils_cog:
            await utils_cog.export_thread(interaction, self.thread_id)
        else:
            await interaction.response.send_message("Error: Utils cog not found.", ephemeral=True)

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_group(name="thread", description="Thread management commands")
    @commands.has_permissions(manage_messages=True)
    async def thread_group(self, ctx):
        """Thread management commands"""
        if ctx.invoked_subcommand is None:
            await self.list_threads(ctx)
    
    @thread_group.command(name="list", description="List all active threads")
    @commands.has_permissions(manage_messages=True)
    async def list_threads(self, ctx):
        """List all active threads"""
        if not self.bot.threads:
            embed = discord.Embed(
                title="No Active Threads",
                description="There are no active threads.",
                color=self.bot.config["color"]["warning"]
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="Active ModMail Threads",
            color=self.bot.config["color"]["default"]
        )
        
        for user_id, thread_data in self.bot.threads.items():
            user = self.bot.get_user(int(user_id))
            channel_id = thread_data["channel_id"]
            channel = self.bot.get_channel(int(channel_id))
            
            created_at = datetime.datetime.fromisoformat(thread_data["created_at"])
            time_diff = datetime.datetime.utcnow() - created_at
            
            user_name = user.name if user else f"Unknown User ({user_id})"
            channel_name = channel.mention if channel else f"Unknown Channel ({channel_id})"
            
            embed.add_field(
                name=f"{user_name} ({user_id})",
                value=f"Channel: {channel_name}\nCreated: {time_diff.days} days, {time_diff.seconds // 3600} hours ago",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @thread_group.command(name="closed", description="List closed threads")
    @commands.has_permissions(manage_messages=True)
    async def list_closed_threads(self, ctx):
        """List closed threads"""
        if not self.bot.closed_threads:
            embed = discord.Embed(
                title="No Closed Threads",
                description="There are no closed threads.",
                color=self.bot.config["color"]["warning"]
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="Closed ModMail Threads",
            color=self.bot.config["color"]["default"]
        )
        
        # Only show the 25 most recent closed threads to avoid embed field limit
        sorted_threads = sorted(
            self.bot.closed_threads.items(),
            key=lambda x: datetime.datetime.fromisoformat(x[1].get("closed_at", x[1]["created_at"])),
            reverse=True
        )[:25]
        
        for user_id, thread_data in sorted_threads:
            user = self.bot.get_user(int(user_id))
            
            closed_at = datetime.datetime.fromisoformat(thread_data.get("closed_at", thread_data["created_at"]))
            time_diff = datetime.datetime.utcnow() - closed_at
            
            user_name = user.name if user else f"Unknown User ({user_id})"
            
            closed_by_id = thread_data.get("closed_by")
            closed_by = None
            if closed_by_id:
                closed_by = self.bot.get_user(int(closed_by_id))
            closed_by_name = closed_by.name if closed_by else "Unknown"
            
            embed.add_field(
                name=f"{user_name} ({user_id})",
                value=f"Closed by: {closed_by_name}\nClosed: {time_diff.days} days, {time_diff.seconds // 3600} hours ago",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @thread_group.command(name="info", description="Get information about a thread")
    @commands.has_permissions(manage_messages=True)
    async def thread_info(self, ctx, user_id: str):
        """Get information about a thread"""
        thread_data = self.bot.threads.get(user_id) or self.bot.closed_threads.get(user_id)
        
        if not thread_data:
            embed = discord.Embed(
                title="Thread Not Found",
                description=f"No thread found for user ID: {user_id}",
                color=self.bot.config["color"]["error"]
            )
            await ctx.send(embed=embed)
            return
        
        user = None
        try:
            user = await self.bot.fetch_user(int(user_id))
        except discord.HTTPException:
            pass
        
        embed = discord.Embed(
            title=f"Thread Info: {user.name if user else 'Unknown User'} ({user_id})",
            color=self.bot.config["color"]["default"]
        )
        
        created_at = datetime.datetime.fromisoformat(thread_data["created_at"])
        
        # Get channel info
        channel_id = thread_data["channel_id"]
        channel = self.bot.get_channel(int(channel_id))
        channel_status = f"{channel.mention} (active)" if channel else f"Not found ({channel_id})"
        
        # Thread status
        status = "Active" if user_id in self.bot.threads else "Closed"
        
        # Additional closed info
        closed_info = ""
        if status == "Closed" and "closed_at" in thread_data:
            closed_at = datetime.datetime.fromisoformat(thread_data["closed_at"])
            closed_by_id = thread_data.get("closed_by")
            closed_by = None
            if closed_by_id:
                try:
                    closed_by = await self.bot.fetch_user(int(closed_by_id))
                except discord.HTTPException:
                    pass
            
            closed_info = f"\nClosed at: {closed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\nClosed by: {closed_by.name if closed_by else 'Unknown'}"
        
        # Message count
        message_count = len(thread_data.get("messages", []))
        
        embed.add_field(name="User", value=f"{user.mention if user else 'Unknown'} ({user_id})", inline=False)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Channel", value=channel_status, inline=True)
        embed.add_field(name="Created", value=created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
        embed.add_field(name="Message Count", value=str(message_count), inline=True)
        
        if closed_info:
            embed.add_field(name="Closure Info", value=closed_info, inline=False)
        
        # Thumbnail
        if user and user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        view = ThreadLogView(thread_id=user_id, bot=self.bot)
        await ctx.send(embed=embed, view=view)
    
    async def export_thread(self, interaction, thread_id):
        thread_data = self.bot.threads.get(thread_id) or self.bot.closed_threads.get(thread_id)
        
        if not thread_data:
            await interaction.response.send_message(
                "Thread not found. It may have been deleted.",
                ephemeral=True
            )
            return
        
        user = None
        try:
            user = await self.bot.fetch_user(int(thread_id))
        except discord.HTTPException:
            pass
        
        user_name = user.name if user else f"Unknown_{thread_id}"
        
        # Create transcript
        messages = thread_data.get("messages", [])
        
        if not messages:
            await interaction.response.send_message(
                "This thread has no messages to export.",
                ephemeral=True
            )
            return
        
        transcript_text = f"# ModMail Thread Transcript\n\n"
        transcript_text += f"User: {user_name} ({thread_id})\n"
        transcript_text += f"Created: {thread_data['created_at']}\n"
        
        if "closed_at" in thread_data:
            transcript_text += f"Closed: {thread_data['closed_at']}\n"
        
        transcript_text += f"Total Messages: {len(messages)}\n\n"
        transcript_text += "---\n\n"
        
        for msg in messages:
            author_id = msg.get("author_id", "unknown")
            is_staff = msg.get("is_staff", False)
            
            try:
                author = await self.bot.fetch_user(int(author_id))
                author_name = f"{author.name} {'(Staff)' if is_staff else ''}"
            except:
                author_name = f"Unknown User ({author_id}) {'(Staff)' if is_staff else ''}"
            
            created_at = datetime.datetime.fromisoformat(msg.get("created_at", datetime.datetime.utcnow().isoformat()))
            content = msg.get("content", "[No content]")
            
            transcript_text += f"## {author_name} - {created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            transcript_text += f"{content}\n\n"
            transcript_text += "---\n\n"
        
        # Create file and send
        file = discord.File(
            io.StringIO(transcript_text),
            filename=f"transcript_{user_name}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
        )
        
        await interaction.response.send_message(
            "Here's the transcript of the thread:",
            file=file
        )
    
    @commands.hybrid_command(name="ping", description="Check the bot's latency")
    async def ping(self, ctx):
        """Check the bot's latency"""
        start_time = datetime.datetime.utcnow()
        message = await ctx.send("Pinging...")
        end_time = datetime.datetime.utcnow()
        
        bot_latency = self.bot.latency * 1000  # Convert to ms
        api_latency = (end_time - start_time).total_seconds() * 1000
        
        embed = discord.Embed(
            title="🏓 Pong!",
            color=self.bot.config["color"]["default"]
        )
        embed.add_field(name="Bot Latency", value=f"{bot_latency:.2f} ms", inline=True)
        embed.add_field(name="API Latency", value=f"{api_latency:.2f} ms", inline=True)
        
        await message.edit(content=None, embed=embed)
    
    @commands.hybrid_command(name="help", description="Show help information")
    async def help_command(self, ctx):
        """Show help information"""
        prefix = self.bot.config.get("prefix", "!")
        
        embed = discord.Embed(
            title="ModMail Bot Help",
            description=f"Here's a list of available commands. Use `{prefix}help [command]` for more details.",
            color=self.bot.config["color"]["default"]
        )
        
        # User commands
        user_cmds = [
            f"`{prefix}help` - Show this help message",
            f"`{prefix}ping` - Check the bot's latency"
        ]
        embed.add_field(name="User Commands", value="\n".join(user_cmds), inline=False)
        
        # Staff commands
        if await self._check_staff_perms(ctx):
            staff_cmds = [
                f"`{prefix}thread list` - List all active threads",
                f"`{prefix}thread closed` - List closed threads",
                f"`{prefix}thread info [user_id]` - Get thread info"
            ]
            embed.add_field(name="Staff Commands", value="\n".join(staff_cmds), inline=False)
        
        # Admin commands
        if ctx.author.guild_permissions.administrator:
            admin_cmds = [
                f"`{prefix}setup` - Interactive setup",
                f"`{prefix}config show` - Show current configuration",
                f"`{prefix}config prefix [prefix]` - Change command prefix",
                f"`{prefix}config status [status]` - Change bot status",
                f"`{prefix}config category [id]` - Set modmail category",
                f"`{prefix}config log_channel [id]` - Set log channel",
                f"`{prefix}config add_staff [role_id]` - Add staff role",
                f"`{prefix}config remove_staff [role_id]` - Remove staff role", 
                f"`{prefix}config unblock [user_id]` - Unblock a user",
                f"`{prefix}config close_time [hours]` - Set thread auto-close time"
            ]
            embed.add_field(name="Admin Commands", value="\n".join(admin_cmds), inline=False)
        
        embed.set_footer(text="To use the ModMail, simply send a DM to the bot.")
        await ctx.send(embed=embed)
    
    async def _check_staff_perms(self, ctx):
        if not ctx.guild:
            return False
            
        # Check if the member has any of the staff roles
        staff_roles = self.bot.config.get("staff_roles", [])
        return any(str(role.id) in staff_roles for role in ctx.author.roles)

async def setup(bot):
    await bot.add_cog(Utils(bot))