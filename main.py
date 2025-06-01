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
    arena_task.start()

@tasks.loop(hours=6)
async def check_reminders():
    """Check for new episodes and send reminders."""
    print("Checking for new episodes...")

# Import command modules and initialize them
import views
import commands
import social
import management

# Initialize modules with shared objects
views.init_views(trakt_api, db)
commands.init_commands(bot, trakt_api, db)
social.init_social(bot, trakt_api, db)
management.init_management(bot, trakt_api, db)

# Register error handler
commands.register_error_handler()

# Arena auto-rotation task
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    # Start arena management task
    arena_task.start()

from discord.ext import tasks
import time
import random

@tasks.loop(hours=1)  # Check every hour
async def arena_task():
    """Auto-rotate arena challenges and cleanup."""
    try:
        # Check if current challenge expired
        challenge = db.get_arena_challenge()
        if challenge and time.time() > challenge.get('end_time', 0):
            # Challenge expired, rotate to new one
            participants = db.get_arena_participants()
            
            if len(participants) >= 2:  # Only if people are playing
                challenges = [
                    {
                        "name": "Genre Master",
                        "description": "Watch any **Horror** movie you haven't seen",
                        "points": 10,
                        "type": "genre",
                        "target": "horror"
                    },
                    {
                        "name": "Decade Dive", 
                        "description": "Watch a movie from the **1990s**",
                        "points": 15,
                        "type": "decade",
                        "target": "1990s"
                    },
                    {
                        "name": "Rating Rush",
                        "description": "Watch a movie with **8.0+ rating** on Trakt",
                        "points": 20,
                        "type": "rating", 
                        "target": 8.0
                    },
                    {
                        "name": "Speed Run",
                        "description": "Watch the **shortest movie** (under 90 min)",
                        "points": 12,
                        "type": "runtime",
                        "target": 90
                    },
                    {
                        "name": "Classic Quest",
                        "description": "Watch a movie from **before 1980**",
                        "points": 18,
                        "type": "classic",
                        "target": 1980
                    }
                ]
                
                new_challenge = random.choice(challenges)
                new_challenge['end_time'] = int(time.time()) + (24 * 60 * 60)
                
                db.set_arena_challenge(new_challenge)
                print(f"Auto-rotated to new challenge: {new_challenge['name']}")
        
        # Cleanup old data
        db.cleanup_arena_data()
        
    except Exception as e:
        print(f"Arena task error: {e}")

@arena_task.before_loop
async def before_arena_task():
    await bot.wait_until_ready()

if __name__ == "__main__":
    bot.run(config.DISCORD_TOKEN) 