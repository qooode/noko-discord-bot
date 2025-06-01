import discord
from discord.ext import commands, tasks
import config
from database import Database
from trakt_api import TraktAPI

# Validate configuration
config.validate_config()

# Initialize components
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

try:
    bot = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents)
except Exception as e:
    print(f"Error creating bot: {e}")
    print("Make sure you have enabled the 'Message Content Intent' in the Discord Developer Portal!")
    exit(1)

# Initialize shared components
trakt_api = TraktAPI()
db = Database()

@bot.event
async def on_ready():
    print(f'{config.BOT_NAME} is connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    # Start background tasks
    check_reminders.start()

@tasks.loop(hours=6)
async def check_reminders():
    """Check for new episodes and send reminders."""
    print("Checking for new episodes...")

# Import command modules (this registers all commands)
import commands
import social
import management

if __name__ == "__main__":
    bot.run(config.DISCORD_TOKEN) 