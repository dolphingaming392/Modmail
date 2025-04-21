import os
import discord
from discord.ext import commands
import asyncio
import json
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ModmailBot")

# Load environment variables
load_dotenv()

# Default configuration
DEFAULT_CONFIG = {
    "prefix": "!",
    "status": "DM me for help!",
    "guild_id": None,
    "modmail_category": None,
    "log_channel": None,
    "staff_roles": [],
    "blocked_users": [],
    "thread_close_time": 12,  # Hours
    "color": {
        "default": 0x5865F2,
        "user": 0x2ECC71,
        "staff": 0x3498DB,
        "error": 0xE74C3C,
        "success": 0x2ECC71,
        "warning": 0xF1C40F
    }
}

class ModMailBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None
        )
        
        self.config = self.load_config()
        self.threads = {}
        self.closed_threads = {}
        
    async def get_prefix(self, message):
        return self.config.get("prefix", "!")
        
    def load_config(self):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                # Merge with defaults in case of missing fields
                return {**DEFAULT_CONFIG, **config}
        except FileNotFoundError:
            logger.warning("Config file not found. Creating default config.")
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        except json.JSONDecodeError:
            logger.error("Invalid config file. Using default config.")
            return DEFAULT_CONFIG
    
    def save_config(self, config=None):
        if config is None:
            config = self.config
        
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
            
    async def setup_hook(self):
        # Load cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('_'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f"Loaded extension: {filename[:-3]}")
                except Exception as e:
                    logger.error(f"Failed to load extension {filename}: {e}")
    
    async def on_ready(self):
        logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=self.config.get("status", "DM me for help!")
        )
        await self.change_presence(activity=activity)
        
        # Create config.json if it doesn't exist
        if not os.path.exists("config.json"):
            self.save_config()
            
        # Create threads.json if it doesn't exist
        if not os.path.exists("threads.json"):
            with open("threads.json", "w") as f:
                json.dump({"active": {}, "closed": {}}, f, indent=4)
        else:
            # Load existing threads
            self.load_threads()
    
    def load_threads(self):
        try:
            with open("threads.json", "r") as f:
                data = json.load(f)
                self.threads = data.get("active", {})
                self.closed_threads = data.get("closed", {})
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("Failed to load threads. Starting with empty threads.")
            self.threads = {}
            self.closed_threads = {}
    
    def save_threads(self):
        with open("threads.json", "w") as f:
            json.dump({
                "active": self.threads,
                "closed": self.closed_threads
            }, f, indent=4)

async def main():
    bot = ModMailBot()
    async with bot:
        await bot.start(os.getenv("TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())