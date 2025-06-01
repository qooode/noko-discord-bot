import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import re
from typing import Optional

import config
from trakt_api import TraktAPI
from database import Database

# Validate configuration
config.validate_config()

# Initialize components with proper intents
intents = discord.Intents.default()
intents.message_content = True  # Required for reading message content
intents.guilds = True           # Required for guild information

try:
    bot = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents)
except Exception as e:
    print(f"Error creating bot: {e}")
    print("Make sure you have enabled the 'Message Content Intent' in the Discord Developer Portal!")
    exit(1)

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
    
    # Start reminder checking task
    check_reminders.start()

@bot.tree.command(name="connect", description="Connect your Trakt.tv account to the bot")
async def connect_trakt(interaction: discord.Interaction):
    """Connect your Trakt.tv account to the bot."""
    auth_url = trakt_api.get_auth_url()
    
    embed = discord.Embed(
        title="🔗 Connect Your Trakt.tv Account",
        description=f"1. Click [here]({auth_url}) to authorize with Trakt.tv\n"
                   f"2. Copy the authorization code\n"
                   f"3. Use `/authorize <code>` with your code",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="authorize", description="Authorize with Trakt.tv using the provided code")
@app_commands.describe(code="The authorization code from Trakt.tv")
async def authorize_trakt(interaction: discord.Interaction, code: str):
    """Authorize with Trakt.tv using the provided code."""
    await interaction.response.defer()
    
    try:
        # Exchange code for token
        token_data = trakt_api.exchange_code_for_token(code)
        if not token_data:
            await interaction.followup.send("❌ Invalid authorization code. Please try again.")
            return
        
        # Get user profile
        user_profile = trakt_api.get_user_profile(token_data['access_token'])
        if not user_profile:
            await interaction.followup.send("❌ Failed to get user profile. Please try again.")
            return
        
        # Save user data
        success = db.add_user(
            str(interaction.user.id),
            user_profile['username'],
            token_data['access_token'],
            token_data['refresh_token']
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Successfully Connected!",
                description=f"Your account **{user_profile['username']}** is now connected to {config.BOT_NAME}!",
                color=0x00ff00
            )
            embed.add_field(
                name="Privacy",
                value="Your profile is **private** by default. Use `/public` to make it visible to others.",
                inline=False
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Failed to save your account data. Please try again.")
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error during authorization: {str(e)}")

@bot.tree.command(name="public", description="Make your profile public so others can see your activity")
async def set_public(interaction: discord.Interaction):
    """Make your profile public so others can see your activity."""
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.response.send_message("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    if db.set_user_privacy(str(interaction.user.id), True):
        await interaction.response.send_message("✅ Your profile is now **public**! Others can see your watching activity.")
    else:
        await interaction.response.send_message("❌ Failed to update your privacy settings.")

@bot.tree.command(name="private", description="Make your profile private")
async def set_private(interaction: discord.Interaction):
    """Make your profile private."""
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.response.send_message("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    if db.set_user_privacy(str(interaction.user.id), False):
        await interaction.response.send_message("✅ Your profile is now **private**.")
    else:
        await interaction.response.send_message("❌ Failed to update your privacy settings.")

@bot.tree.command(name="search", description="Search for shows or movies")
@app_commands.describe(query="What to search for (show or movie name)")
async def search_content(interaction: discord.Interaction, query: str):
    """Search for shows or movies."""
    await interaction.response.defer()
    
    results = trakt_api.search_content(query)
    
    if not results:
        await interaction.followup.send(f"❌ No results found for '{query}'")
        return
    
    embed = discord.Embed(
        title=f"🔍 Search Results for '{query}'",
        color=0x0099ff
    )
    
    for i, result in enumerate(results[:5], 1):
        content = result.get('show') or result.get('movie')
        content_type = 'Show' if 'show' in result else 'Movie'
        year = content.get('year', 'N/A')
        rating = content.get('rating', 0)
        
        embed.add_field(
            name=f"{i}. {content['title']} ({year}) - {content_type}",
            value=f"⭐ {rating}/10\n{content.get('overview', 'No description available')[:100]}...",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="info", description="Get detailed information about a show or movie")
@app_commands.describe(query="Show or movie name to get info about")
async def get_info(interaction: discord.Interaction, query: str):
    """Get detailed information about a show or movie."""
    await interaction.response.defer()
    
    results = trakt_api.search_content(query)
    
    if not results:
        await interaction.followup.send(f"❌ No results found for '{query}'")
        return
    
    # Get the first result
    result = results[0]
    content = result.get('show') or result.get('movie')
    content_type = 'show' if 'show' in result else 'movie'
    content_id = content['ids']['trakt']
    
    # Get detailed info
    if content_type == 'show':
        detailed_info = trakt_api.get_show_info(str(content_id))
    else:
        detailed_info = trakt_api.get_movie_info(str(content_id))
    
    if not detailed_info:
        await interaction.followup.send("❌ Failed to get detailed information.")
        return
    
    embed = discord.Embed(
        title=f"{detailed_info['title']} ({detailed_info.get('year', 'N/A')})",
        description=detailed_info.get('overview', 'No description available'),
        color=0x0099ff
    )
    
    embed.add_field(name="Type", value=content_type.title(), inline=True)
    embed.add_field(name="Rating", value=f"⭐ {detailed_info.get('rating', 0)}/10", inline=True)
    embed.add_field(name="Runtime", value=f"{detailed_info.get('runtime', 'N/A')} min", inline=True)
    
    if content_type == 'show':
        embed.add_field(name="Status", value=detailed_info.get('status', 'N/A'), inline=True)
        embed.add_field(name="Network", value=detailed_info.get('network', 'N/A'), inline=True)
    
    genres = detailed_info.get('genres', [])
    if genres:
        embed.add_field(name="Genres", value=", ".join(genres[:3]), inline=True)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="watched", description="Mark a show or movie as watched")
@app_commands.describe(query="Show or movie name to mark as watched")
async def mark_watched(interaction: discord.Interaction, query: str):
    """Mark a show or movie as watched."""
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    # Search for content
    results = trakt_api.search_content(query)
    if not results:
        await interaction.followup.send(f"❌ No results found for '{query}'")
        return
    
    # Get the first result
    result = results[0]
    content = result.get('show') or result.get('movie')
    content_type = 'show' if 'show' in result else 'movie'
    content_id = str(content['ids']['trakt'])
    
    # Mark as watched
    success = trakt_api.mark_as_watched(user['access_token'], content_type, content_id)
    
    if success:
        embed = discord.Embed(
            title="✅ Marked as Watched",
            description=f"**{content['title']}** has been marked as watched!",
            color=0x00ff00
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ Failed to mark as watched. Please try again.")

@bot.tree.command(name="unwatch", description="Remove a show or movie from watched history")
@app_commands.describe(query="Show or movie name to remove from watched")
async def unmark_watched(interaction: discord.Interaction, query: str):
    """Remove a show or movie from watched history."""
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    # Search for content
    results = trakt_api.search_content(query)
    if not results:
        await interaction.followup.send(f"❌ No results found for '{query}'")
        return
    
    # Get the first result
    result = results[0]
    content = result.get('show') or result.get('movie')
    content_type = 'show' if 'show' in result else 'movie'
    content_id = str(content['ids']['trakt'])
    
    # Unmark as watched
    success = trakt_api.unmark_as_watched(user['access_token'], content_type, content_id)
    
    if success:
        embed = discord.Embed(
            title="✅ Removed from Watched",
            description=f"**{content['title']}** has been removed from your watched history!",
            color=0x00ff00
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ Failed to remove from watched. Please try again.")

@bot.tree.command(name="watchlist", description="Add a show or movie to your watchlist")
@app_commands.describe(query="Show or movie name to add to watchlist")
async def add_to_watchlist(interaction: discord.Interaction, query: str):
    """Add a show or movie to your watchlist."""
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    # Search for content
    results = trakt_api.search_content(query)
    if not results:
        await interaction.followup.send(f"❌ No results found for '{query}'")
        return
    
    # Get the first result
    result = results[0]
    content = result.get('show') or result.get('movie')
    content_type = 'show' if 'show' in result else 'movie'
    content_id = str(content['ids']['trakt'])
    
    # Add to watchlist
    success = trakt_api.add_to_watchlist(user['access_token'], content_type, content_id)
    
    if success:
        embed = discord.Embed(
            title="✅ Added to Watchlist",
            description=f"**{content['title']}** has been added to your watchlist!",
            color=0x00ff00
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ Failed to add to watchlist. Please try again.")

@bot.tree.command(name="watching", description="See what you or another user is currently watching")
@app_commands.describe(user="User to check (leave empty for yourself)")
async def get_watching(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    """See what you or another user is currently watching."""
    await interaction.response.defer()
    
    if user:
        target_user = db.get_user(str(user.id))
        
        if not target_user:
            await interaction.followup.send("❌ That user hasn't connected their Trakt.tv account.")
            return
        
        if not target_user.get('is_public', False):
            await interaction.followup.send("❌ That user's profile is private.")
            return
        
        username = target_user['trakt_username']
    else:
        current_user = db.get_user(str(interaction.user.id))
        if not current_user:
            await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
            return
        username = current_user['trakt_username']
    
    # Get currently watching
    watching = trakt_api.get_watching_now(username)
    
    if not watching:
        name = f"**{username}**" if user else "You"
        await interaction.followup.send(f"📺 {name} are not watching anything right now.")
        return
    
    content = watching.get('show') or watching.get('movie')
    content_type = 'Show' if 'show' in watching else 'Movie'
    
    embed = discord.Embed(
        title=f"📺 Currently Watching",
        description=f"**{username}** is watching:",
        color=0xff6600
    )
    
    if 'episode' in watching:
        episode = watching['episode']
        embed.add_field(
            name=f"{content['title']}",
            value=f"S{episode['season']}E{episode['number']}: {episode.get('title', 'Episode')}",
            inline=False
        )
    else:
        embed.add_field(
            name=f"{content['title']} ({content_type})",
            value=content.get('overview', 'No description available')[:200] + "...",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="last", description="See what you or another user watched recently")
@app_commands.describe(
    user="User to check (leave empty for yourself)",
    count="Number of recent items to show (1-10)"
)
async def get_last_watched(interaction: discord.Interaction, user: Optional[discord.Member] = None, count: int = 5):
    """See what you or another user watched recently."""
    await interaction.response.defer()
    
    if count < 1 or count > 10:
        count = 5
    
    if user:
        target_user = db.get_user(str(user.id))
        
        if not target_user:
            await interaction.followup.send("❌ That user hasn't connected their Trakt.tv account.")
            return
        
        if not target_user.get('is_public', False):
            await interaction.followup.send("❌ That user's profile is private.")
            return
        
        username = target_user['trakt_username']
    else:
        current_user = db.get_user(str(interaction.user.id))
        if not current_user:
            await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
            return
        username = current_user['trakt_username']
    
    # Get watch history
    history = trakt_api.get_user_history(username, count)
    
    if not history:
        name = f"**{username}**" if user else "You"
        await interaction.followup.send(f"📺 {name} haven't watched anything recently.")
        return
    
    embed = discord.Embed(
        title=f"📺 Recent Watches",
        description=f"Last {len(history)} items watched by **{username}**:",
        color=0x0099ff
    )
    
    for item in history:
        content = item.get('show') or item.get('movie')
        content_type = 'Show' if 'show' in item else 'Movie'
        watched_at = datetime.fromisoformat(item['watched_at'].replace('Z', '+00:00'))
        
        if 'episode' in item:
            episode = item['episode']
            title = f"{content['title']} - S{episode['season']}E{episode['number']}"
            if episode.get('title'):
                title += f": {episode['title']}"
        else:
            title = f"{content['title']} ({content_type})"
        
        embed.add_field(
            name=title,
            value=f"Watched {watched_at.strftime('%m/%d/%Y at %I:%M %p')}",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="remind", description="Set up reminders for new episodes of a show")
@app_commands.describe(show_name="Name of the show to get reminders for")
async def add_reminder(interaction: discord.Interaction, show_name: str):
    """Set up reminders for new episodes of a show."""
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    # Search for the show
    results = trakt_api.search_content(show_name, 'show')
    if not results:
        await interaction.followup.send(f"❌ No shows found for '{show_name}'")
        return
    
    # Get the first result
    show = results[0]['show']
    show_id = str(show['ids']['trakt'])
    
    # Add reminder
    success = db.add_reminder(str(interaction.user.id), show_id, show['title'])
    
    if success:
        embed = discord.Embed(
            title="🔔 Reminder Added",
            description=f"You'll be notified when new episodes of **{show['title']}** are released!",
            color=0x00ff00
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ Failed to add reminder. You might already have one for this show.")

@bot.tree.command(name="unremind", description="Remove reminders for a show")
@app_commands.describe(show_name="Name of the show to stop reminders for")
async def remove_reminder(interaction: discord.Interaction, show_name: str):
    """Remove reminders for a show."""
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    # Search for the show
    results = trakt_api.search_content(show_name, 'show')
    if not results:
        await interaction.followup.send(f"❌ No shows found for '{show_name}'")
        return
    
    # Get the first result
    show = results[0]['show']
    show_id = str(show['ids']['trakt'])
    
    # Remove reminder
    success = db.remove_reminder(str(interaction.user.id), show_id)
    
    if success:
        embed = discord.Embed(
            title="🔕 Reminder Removed",
            description=f"You'll no longer receive notifications for **{show['title']}**.",
            color=0xff6600
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ You don't have a reminder set for this show.")

@bot.tree.command(name="reminders", description="List all your active reminders")
async def list_reminders(interaction: discord.Interaction):
    """List all your active reminders."""
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.response.send_message("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    reminders = db.get_user_reminders(str(interaction.user.id))
    
    if not reminders:
        await interaction.response.send_message("🔔 You don't have any active reminders.")
        return
    
    embed = discord.Embed(
        title="🔔 Your Active Reminders",
        description=f"You have {len(reminders)} active reminder(s):",
        color=0x0099ff
    )
    
    for show_id, reminder_data in reminders.items():
        show_name = reminder_data['show_name']
        added_at = datetime.fromisoformat(reminder_data['added_at'])
        embed.add_field(
            name=show_name,
            value=f"Added on {added_at.strftime('%m/%d/%Y')}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@tasks.loop(hours=6)  # Check every 6 hours
async def check_reminders():
    """Check for new episodes and send reminders."""
    # This is a simplified version - in production you'd want more sophisticated logic
    print("Checking for new episodes...")
    # Implementation would check calendar for each user's reminded shows
    # and send notifications if new episodes are available

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle slash command errors."""
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"❌ Command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ An error occurred: {str(error)}", ephemeral=True)
        print(f"Error in {interaction.command}: {error}")

if __name__ == "__main__":
    bot.run(config.DISCORD_TOKEN) 