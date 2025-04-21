# Discord ModMail Bot

A fully-featured Discord ModMail bot that allows users to contact server staff through direct messages.

## Features

- Users can DM the bot to create support threads
- Staff can respond to user messages from a designated channel
- Thread management with interactive buttons (close, block, delete)
- Modular cog-based architecture for better code organization
- Logging system for moderation actions
- Configuration commands to customize bot settings
- Support for attachments and embeds
- Thread persistence across bot restarts

## Setup

1. Create a Discord bot on the [Discord Developer Portal](https://discord.com/developers/applications)
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Edit the `.env` file with your bot token
4. Run the bot:
   ```
   python bot.py
   ```
5. Use the `!setup` command in your Discord server to configure the bot

## Commands

### User Commands
- `!help` - Show help information
- `!ping` - Check the bot's latency

### Staff Commands
- `!thread list` - List all active threads
- `!thread closed` - List closed threads
- `!thread info [user_id]` - Get thread info

### Admin Commands
- `!setup` - Interactive setup
- `!config show` - Show current configuration
- `!config prefix [prefix]` - Change command prefix
- `!config status [status]` - Change bot status
- `!config category [id]` - Set modmail category
- `!config log_channel [id]` - Set log channel
- `!config add_staff [role_id]` - Add staff role
- `!config remove_staff [role_id]` - Remove staff role
- `!config unblock [user_id]` - Unblock a user
- `!config close_time [hours]` - Set thread auto-close time

## How It Works

1. When a user DMs the bot, a new thread is created in the configured category
2. Staff can respond to the user by typing in the thread channel
3. Messages are relayed between the user and staff
4. Staff can use buttons to manage the thread (close, block, delete)
5. Threads can be exported for record-keeping

## License

This project is licensed under the MIT License - see the LICENSE file for details.