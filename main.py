import discord
from discord.ext import commands, tasks
import config
from database import Database
from trakt_api import TraktAPI
from datetime import datetime, timedelta
import pytz

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

# Import command modules and initialize them BEFORE on_ready
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

@bot.event
async def on_ready():
    print(f'{config.BOT_NAME} is connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
        
        # List all commands for debugging
        print("Registered commands:")
        for command in bot.tree.get_commands():
            print(f"  - /{command.name}: {command.description}")
            
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    # Start background tasks
    check_reminders.start()
    arena_task.start()

@tasks.loop(hours=6)
async def check_reminders():
    """Check for new episodes and send reminders."""
    print("🔔 Checking for episode reminders...")
    
    try:
        # Get all user reminders
        all_reminders = db.get_all_reminders()
        
        if not all_reminders:
            print("No active reminders to check")
            return
        
        notification_count = 0
        
        for discord_id, user_reminders in all_reminders.items():
            # Get user data to access their Trakt account
            user = db.get_user(discord_id)
            if not user or not user.get('trakt_username'):
                continue
            
            try:
                # Get user's upcoming episodes (next 3 days)
                username = user['trakt_username']
                upcoming_episodes = trakt_api.get_calendar(username, 3)
                
                if not upcoming_episodes:
                    continue
                
                # Check each reminder against upcoming episodes
                for show_id, reminder_data in user_reminders.items():
                    show_name = reminder_data['show_name']
                    hours_before = reminder_data.get('hours_before', 1)
                    custom_message = reminder_data.get('message', '')
                    
                    # Find matching episodes for this show
                    for episode_data in upcoming_episodes:
                        try:
                            episode = episode_data.get('episode', {})
                            show = episode_data.get('show', {})
                            
                            # Check if this episode matches the reminder show
                            if str(show.get('ids', {}).get('trakt')) == show_id:
                                first_aired = episode.get('first_aired')
                                if not first_aired:
                                    continue
                                
                                # Parse air date and calculate notification time
                                from datetime import datetime, timedelta
                                import pytz
                                
                                try:
                                    # Parse the air date (usually in UTC)
                                    if first_aired.endswith('Z'):
                                        air_date = datetime.fromisoformat(first_aired.replace('Z', '+00:00'))
                                    else:
                                        air_date = datetime.fromisoformat(first_aired)
                                    
                                    # Convert to UTC if not already
                                    if air_date.tzinfo is None:
                                        air_date = pytz.UTC.localize(air_date)
                                    
                                    # Calculate when to send notification
                                    notification_time = air_date - timedelta(hours=hours_before)
                                    current_time = datetime.now(pytz.UTC)
                                    
                                    # Check if it's time to send notification (within the last 6 hours)
                                    time_diff = current_time - notification_time
                                    
                                    if timedelta(0) <= time_diff <= timedelta(hours=6):
                                        # Time to send notification!
                                        discord_user = bot.get_user(int(discord_id))
                                        
                                        if discord_user:
                                            # Create notification embed
                                            embed = discord.Embed(
                                                title="🔔 Episode Reminder!",
                                                description=f"**{show_name}** has a new episode airing soon!",
                                                color=0xff6600
                                            )
                                            
                                            # Episode details
                                            season = episode.get('season', 0)
                                            number = episode.get('number', 0)
                                            title = episode.get('title', 'Untitled')
                                            
                                            embed.add_field(
                                                name="📺 Episode",
                                                value=f"S{season:02d}E{number:02d}: {title}",
                                                inline=False
                                            )
                                            
                                            # Air time
                                            air_time_local = air_date.strftime('%A, %B %d at %I:%M %p UTC')
                                            embed.add_field(
                                                name="📅 Airs",
                                                value=air_time_local,
                                                inline=False
                                            )
                                            
                                            # Custom message if provided
                                            if custom_message:
                                                embed.add_field(
                                                    name="💬 Your Note",
                                                    value=f"*{custom_message}*",
                                                    inline=False
                                                )
                                            
                                            # Time until air
                                            time_until = air_date - current_time
                                            if time_until.total_seconds() > 0:
                                                hours_left = int(time_until.total_seconds() // 3600)
                                                minutes_left = int((time_until.total_seconds() % 3600) // 60)
                                                
                                                if hours_left > 0:
                                                    time_str = f"⏰ Airs in **{hours_left}h {minutes_left}m**"
                                                else:
                                                    time_str = f"⏰ Airs in **{minutes_left}m**"
                                            else:
                                                time_str = "🔥 **Airing now!**"
                                            
                                            embed.add_field(
                                                name="⏳ Countdown",
                                                value=time_str,
                                                inline=False
                                            )
                                            
                                            embed.set_footer(text="💡 Use /reminders to manage your notifications")
                                            
                                            # Send DM
                                            try:
                                                await discord_user.send(embed=embed)
                                                notification_count += 1
                                                print(f"✅ Sent reminder to {discord_user.name} for {show_name} S{season:02d}E{number:02d}")
                                                
                                                # Optional: Remove this specific reminder after sending
                                                # db.remove_reminder(discord_id, show_id)
                                                
                                            except discord.Forbidden:
                                                print(f"❌ Couldn't send DM to {discord_user.name} (DMs disabled)")
                                            except Exception as dm_error:
                                                print(f"❌ Error sending DM to {discord_user.name}: {dm_error}")
                                
                                except Exception as date_error:
                                    print(f"Error parsing air date {first_aired}: {date_error}")
                                    continue
                        
                        except Exception as episode_error:
                            print(f"Error processing episode: {episode_error}")
                            continue
            
            except Exception as user_error:
                print(f"Error checking reminders for user {discord_id}: {user_error}")
                continue
        
        if notification_count > 0:
            print(f"🔔 Sent {notification_count} episode reminder(s)")
        else:
            print("📅 No reminders needed at this time")
    
    except Exception as e:
        print(f"❌ Error in reminder check: {e}")

# Arena auto-rotation task
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