import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import datetime
import json

class ThreadView(discord.ui.View):
    def __init__(self, thread_id, bot):
        super().__init__(timeout=None)
        self.thread_id = thread_id
        self.bot = bot
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.gray, emoji="🔒", custom_id="thread:close")
    async def close_thread(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get cog instance
        modmail_cog = self.bot.get_cog("ModMail")
        if modmail_cog:
            await modmail_cog.close_thread(interaction, self.thread_id)
        else:
            await interaction.response.send_message("Error: ModMail cog not found.", ephemeral=True)
    
    @discord.ui.button(label="Block User", style=discord.ButtonStyle.red, emoji="🚫", custom_id="thread:block")
    async def block_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        modmail_cog = self.bot.get_cog("ModMail")
        if modmail_cog:
            await modmail_cog.block_user(interaction, self.thread_id)
        else:
            await interaction.response.send_message("Error: ModMail cog not found.", ephemeral=True)
    
    @discord.ui.button(label="Delete Thread", style=discord.ButtonStyle.danger, emoji="⛔", custom_id="thread:delete")
    async def delete_thread(self, interaction: discord.Interaction, button: discord.ui.Button):
        modmail_cog = self.bot.get_cog("ModMail")
        if modmail_cog:
            # Ask for confirmation
            confirm_view = ConfirmView()
            await interaction.response.send_message(
                "Are you sure you want to delete this thread? This action cannot be undone.",
                view=confirm_view,
                ephemeral=True
            )
            
            # Wait for confirmation
            await confirm_view.wait()
            if confirm_view.value:
                await modmail_cog.delete_thread(interaction, self.thread_id)
            else:
                await interaction.followup.send("Thread deletion cancelled.", ephemeral=True)
        else:
            await interaction.response.send_message("Error: ModMail cog not found.", ephemeral=True)

class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.value = None
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.edit_message(content="Action confirmed.", view=None)
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.edit_message(content="Action cancelled.", view=None)
        self.stop()

class ModMail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Handle DM messages
        if isinstance(message.channel, discord.DMChannel):
            await self.handle_dm(message)
        
        # Handle thread channel messages
        elif message.guild and self.is_thread_channel(message.channel):
            await self.handle_thread_message(message)
    
    def is_thread_channel(self, channel):
        # Check if the channel is in the modmail category and is a thread channel
        if not channel.guild:
            return False
            
        category_id = self.bot.config.get("modmail_category")
        if not category_id:
            return False
            
        return channel.category_id == int(category_id) and str(channel.id) in self.bot.threads
    
    async def handle_dm(self, message):
        author_id = str(message.author.id)
        
        # Check if user is blocked
        if author_id in self.bot.config.get("blocked_users", []):
            embed = discord.Embed(
                title="You are blocked",
                description="You have been blocked from using the modmail system.",
                color=self.bot.config["color"]["error"]
            )
            try:
                await message.author.send(embed=embed)
            except discord.HTTPException:
                pass
            return
        
        # Check if a thread already exists
        if author_id in self.bot.threads:
            thread_id = self.bot.threads[author_id]["channel_id"]
            await self.forward_to_thread(message, thread_id)
        else:
            # Create a new thread
            await self.create_thread(message)
    
    async def create_thread(self, message):
        guild_id = self.bot.config.get("guild_id")
        category_id = self.bot.config.get("modmail_category")
        
        if not guild_id or not category_id:
            embed = discord.Embed(
                title="ModMail Not Configured",
                description="The ModMail system has not been configured correctly. Please contact an administrator.",
                color=self.bot.config["color"]["error"]
            )
            await message.author.send(embed=embed)
            return
        
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return
            
        category = guild.get_channel(int(category_id))
        if not category:
            return
        
        # Create channel
        channel_name = f"{message.author.name}-{message.author.discriminator}"
        if message.author.discriminator == "0":  # Handle new username system
            channel_name = f"{message.author.name}"
            
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            topic=f"ModMail thread for {message.author.name} ({message.author.id})"
        )
        
        # Create thread object
        thread_data = {
            "user_id": str(message.author.id),
            "channel_id": str(channel.id),
            "created_at": datetime.datetime.utcnow().isoformat(),
            "messages": []
        }
        
        self.bot.threads[str(message.author.id)] = thread_data
        self.bot.save_threads()
        
        # Send welcome message to the channel
        embed = discord.Embed(
            title=f"New ModMail Thread",
            description=f"Thread created for {message.author.mention} ({message.author.id})",
            color=self.bot.config["color"]["default"],
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text=f"User ID: {message.author.id}")
        embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        
        thread_view = ThreadView(thread_id=str(message.author.id), bot=self.bot)
        await channel.send(embed=embed, view=thread_view)
        
        # Forward the initial message
        await self.forward_to_thread(message, str(channel.id))
        
        # Send confirmation to user
        user_embed = discord.Embed(
            title="ModMail Thread Created",
            description="Your message has been sent to the staff. Please wait for a response.",
            color=self.bot.config["color"]["success"],
            timestamp=datetime.datetime.now()
        )
        await message.author.send(embed=user_embed)
    
    async def forward_to_thread(self, message, thread_id):
        channel = self.bot.get_channel(int(thread_id))
        if not channel:
            return
        
        # Create embed
        embed = discord.Embed(
            description=message.content or "*No content*",
            color=self.bot.config["color"]["user"],
            timestamp=datetime.datetime.now()
        )
        embed.set_author(
            name=f"{message.author.name}",
            icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url
        )
        
        # Handle attachments
        files = []
        if message.attachments:
            attachment_text = []
            for i, attachment in enumerate(message.attachments):
                try:
                    file = await attachment.to_file()
                    files.append(file)
                    attachment_text.append(f"[Attachment {i+1}]")
                except discord.HTTPException:
                    attachment_text.append(f"[Attachment {i+1} (too large to forward)]")
            
            if attachment_text:
                embed.add_field(name="Attachments", value="\n".join(attachment_text))
        
        # Send the message
        sent_message = await channel.send(embed=embed, files=files)
        
        # Store message in thread data
        user_id = None
        for uid, thread_data in self.bot.threads.items():
            if thread_data["channel_id"] == thread_id:
                user_id = uid
                break
        
        if user_id:
            if "messages" not in self.bot.threads[user_id]:
                self.bot.threads[user_id]["messages"] = []
            
            self.bot.threads[user_id]["messages"].append({
                "message_id": str(sent_message.id),
                "content": message.content,
                "author_id": str(message.author.id),
                "created_at": datetime.datetime.utcnow().isoformat(),
                "is_staff": False
            })
            
            self.bot.save_threads()
    
    async def handle_thread_message(self, message):
        # Get the user associated with this thread
        user_id = None
        for uid, thread_data in self.bot.threads.items():
            if thread_data["channel_id"] == str(message.channel.id):
                user_id = uid
                break
        
        if not user_id:
            return
        
        # Check if author has permission
        if not await self.check_staff_permissions(message.author):
            embed = discord.Embed(
                title="Permission Denied",
                description="You do not have permission to use this channel.",
                color=self.bot.config["color"]["error"]
            )
            await message.channel.send(embed=embed, delete_after=5)
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            return
        
        # Process staff message
        if message.content.startswith("!"):
            # It's a command, don't forward it
            return
        
        # Forward message to user
        await self.forward_to_user(message, user_id)
    
    async def forward_to_user(self, message, user_id):
        user = self.bot.get_user(int(user_id))
        if not user:
            try:
                user = await self.bot.fetch_user(int(user_id))
            except discord.HTTPException:
                await message.channel.send("Could not find the user associated with this thread.")
                return
        
        # Create embed
        embed = discord.Embed(
            description=message.content or "*No content*",
            color=self.bot.config["color"]["staff"],
            timestamp=datetime.datetime.now()
        )
        embed.set_author(
            name=f"{message.author.name} (Staff)",
            icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url
        )
        
        # Handle attachments
        files = []
        if message.attachments:
            attachment_text = []
            for i, attachment in enumerate(message.attachments):
                try:
                    file = await attachment.to_file()
                    files.append(file)
                    attachment_text.append(f"[Attachment {i+1}]")
                except discord.HTTPException:
                    attachment_text.append(f"[Attachment {i+1} (too large to forward)]")
            
            if attachment_text:
                embed.add_field(name="Attachments", value="\n".join(attachment_text))
        
        # Send message to user
        try:
            sent_message = await user.send(embed=embed, files=files)
            
            # Add reaction to original message to indicate it was sent
            await message.add_reaction("✅")
            
            # Save the message to the thread data
            if "messages" not in self.bot.threads[user_id]:
                self.bot.threads[user_id]["messages"] = []
            
            self.bot.threads[user_id]["messages"].append({
                "message_id": str(message.id),
                "content": message.content,
                "author_id": str(message.author.id),
                "created_at": datetime.datetime.utcnow().isoformat(),
                "is_staff": True
            })
            
            self.bot.save_threads()
            
        except discord.HTTPException as e:
            await message.add_reaction("❌")
            await message.channel.send(f"Failed to send message: {str(e)}")
    
    async def check_staff_permissions(self, member):
        # Check if the member has any of the staff roles
        staff_roles = self.bot.config.get("staff_roles", [])
        return any(str(role.id) in staff_roles for role in member.roles)
    
    async def close_thread(self, interaction, thread_id):
        # Get the channel
        thread_data = self.bot.threads.get(thread_id)
        if not thread_data:
            await interaction.response.send_message("Thread not found.", ephemeral=True)
            return
        
        channel_id = thread_data["channel_id"]
        channel = self.bot.get_channel(int(channel_id))
        
        # Notify user that thread is being closed
        try:
            user = await self.bot.fetch_user(int(thread_id))
            embed = discord.Embed(
                title="Thread Closed",
                description="This ModMail thread has been closed by a staff member. If you need further assistance, feel free to send another message to create a new thread.",
                color=self.bot.config["color"]["warning"],
                timestamp=datetime.datetime.now()
            )
            await user.send(embed=embed)
        except discord.HTTPException:
            pass
        
        # Move thread to closed threads
        self.bot.closed_threads[thread_id] = thread_data
        self.bot.closed_threads[thread_id]["closed_at"] = datetime.datetime.utcnow().isoformat()
        self.bot.closed_threads[thread_id]["closed_by"] = str(interaction.user.id)
        
        # Remove from active threads
        del self.bot.threads[thread_id]
        self.bot.save_threads()
        
        # Send closure notification to channel
        embed = discord.Embed(
            title="Thread Closed",
            description=f"This thread has been closed by {interaction.user.mention}.",
            color=self.bot.config["color"]["warning"],
            timestamp=datetime.datetime.now()
        )
        await interaction.response.send_message(embed=embed)
        
        # Archive the channel after a delay
        await asyncio.sleep(10)
        if channel:
            try:
                # Change channel name to indicate it's closed
                await channel.edit(name=f"closed-{channel.name}")
            except discord.HTTPException:
                pass
    
    async def block_user(self, interaction, thread_id):
        # Add user to blocked list
        if thread_id not in self.bot.config["blocked_users"]:
            self.bot.config["blocked_users"].append(thread_id)
            self.bot.save_config()
            
            # Notify user they are blocked
            try:
                user = await self.bot.fetch_user(int(thread_id))
                embed = discord.Embed(
                    title="You Have Been Blocked",
                    description="You have been blocked from using the ModMail system.",
                    color=self.bot.config["color"]["error"],
                    timestamp=datetime.datetime.now()
                )
                await user.send(embed=embed)
            except discord.HTTPException:
                pass
            
            # Close the thread
            await self.close_thread(interaction, thread_id)
            
            await interaction.response.send_message("User has been blocked from using ModMail.", ephemeral=True)
        else:
            await interaction.response.send_message("This user is already blocked.", ephemeral=True)
    
    async def delete_thread(self, interaction, thread_id):
        # Get the channel
        thread_data = self.bot.threads.get(thread_id) or self.bot.closed_threads.get(thread_id)
        if not thread_data:
            await interaction.followup.send("Thread not found.", ephemeral=True)
            return
        
        channel_id = thread_data["channel_id"]
        channel = self.bot.get_channel(int(channel_id))
        
        # Remove thread from both active and closed threads
        if thread_id in self.bot.threads:
            del self.bot.threads[thread_id]
        if thread_id in self.bot.closed_threads:
            del self.bot.closed_threads[thread_id]
        
        self.bot.save_threads()
        
        # Delete the channel
        if channel:
            try:
                await channel.delete(reason=f"Thread deleted by {interaction.user}")
            except discord.HTTPException:
                await interaction.followup.send("Failed to delete the channel.", ephemeral=True)
        
        await interaction.followup.send("Thread and channel have been deleted.", ephemeral=True)
    
    @commands.hybrid_command(name="setup", description="Setup the ModMail system")
    @commands.has_permissions(administrator=True)
    async def setup_modmail(self, ctx):
        """Setup the ModMail system"""
        
        # Interactive setup
        questions = [
            "What is the ID of your server?",
            "Please create a category for ModMail channels and enter its ID:",
            "Please create a channel for logs and enter its ID:",
            "Please enter the IDs of staff roles (comma-separated):"
        ]
        
        answers = []
        
        for question in questions:
            embed = discord.Embed(
                title="ModMail Setup",
                description=question,
                color=self.bot.config["color"]["default"]
            )
            await ctx.send(embed=embed)
            
            try:
                response = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                    timeout=60
                )
                answers.append(response.content)
            except asyncio.TimeoutError:
                await ctx.send("Setup timed out. Please try again.")
                return
        
        # Update config
        self.bot.config["guild_id"] = answers[0]
        self.bot.config["modmail_category"] = answers[1]
        self.bot.config["log_channel"] = answers[2]
        self.bot.config["staff_roles"] = [role.strip() for role in answers[3].split(",")]
        
        self.bot.save_config()
        
        embed = discord.Embed(
            title="ModMail Setup Complete",
            description="The ModMail system has been set up successfully!",
            color=self.bot.config["color"]["success"]
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ModMail(bot))