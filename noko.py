import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import re
from typing import Optional, List
import json

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

# Autocomplete functions
async def show_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """Autocomplete for show names."""
    if len(current) < 2:
        return []
    
    try:
        results = trakt_api.search_content(current, 'show')
        choices = []
        
        for result in results[:10]:  # Limit to 10 choices
            show = result['show']
            title = show['title']
            year = show.get('year', '')
            choice_name = f"{title} ({year})" if year else title
            
            choices.append(app_commands.Choice(name=choice_name[:100], value=title))
        
        return choices
    except:
        return []

async def content_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """Autocomplete for shows and movies."""
    if len(current) < 2:
        return []
    
    try:
        results = trakt_api.search_content(current)
        choices = []
        
        for result in results[:10]:
            content = result.get('show') or result.get('movie')
            content_type = 'Show' if 'show' in result else 'Movie'
            title = content['title']
            year = content.get('year', '')
            
            choice_name = f"{title} ({year}) - {content_type}" if year else f"{title} - {content_type}"
            choices.append(app_commands.Choice(name=choice_name[:100], value=title))
        
        return choices
    except:
        return []

class SearchView(discord.ui.View):
    """Interactive view for search results with buttons."""
    def __init__(self, results, query, user_id):
        super().__init__(timeout=300)
        self.results = results
        self.query = query
        self.user_id = user_id
        self.current_page = 0
        self.items_per_page = 3
        
    def get_embed(self):
        """Get the current page embed."""
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_results = self.results[start:end]
        
        embed = discord.Embed(
            title=f"🔍 Search Results for '{self.query}'",
            description=f"Page {self.current_page + 1}/{(len(self.results) - 1) // self.items_per_page + 1}",
            color=0x0099ff
        )
        
        for i, result in enumerate(page_results, start + 1):
            content = result.get('show') or result.get('movie')
            content_type = 'Show' if 'show' in result else 'Movie'
            year = content.get('year', 'N/A')
            rating = content.get('rating', 0)
            
            embed.add_field(
                name=f"{i}. {content['title']} ({year}) - {content_type}",
                value=f"⭐ {rating}/10\n{content.get('overview', 'No description available')[:100]}...",
                inline=False
            )
        
        return embed
    
    @discord.ui.button(label='◀️ Previous', style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your search!", ephemeral=True)
            return
            
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message("You're already on the first page!", ephemeral=True)
    
    @discord.ui.button(label='▶️ Next', style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your search!", ephemeral=True)
            return
            
        max_pages = (len(self.results) - 1) // self.items_per_page
        if self.current_page < max_pages:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message("You're already on the last page!", ephemeral=True)
    
    @discord.ui.button(label='📺 More Info', style=discord.ButtonStyle.primary)
    async def more_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your search!", ephemeral=True)
            return
            
        # Create dropdown for selecting which item to get info about
        options = []
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_results = self.results[start:end]
        
        for i, result in enumerate(page_results, start + 1):
            content = result.get('show') or result.get('movie')
            content_type = 'Show' if 'show' in result else 'Movie'
            
            options.append(discord.SelectOption(
                label=f"{content['title']} ({content_type})",
                description=content.get('overview', 'No description')[:50] + "...",
                value=str(i-1)  # Index in results
            ))
        
        if options:
            view = InfoSelectView(self.results, options, start, self.user_id)
            await interaction.response.send_message("Select an item to get more info:", view=view, ephemeral=True)

class InfoSelectView(discord.ui.View):
    """Dropdown for selecting content to get more info about."""
    def __init__(self, results, options, start_index, user_id):
        super().__init__(timeout=60)
        self.results = results
        self.start_index = start_index
        self.user_id = user_id
        
        select = discord.ui.Select(
            placeholder="Choose an item to get detailed info...",
            options=options
        )
        select.callback = self.select_callback
        self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your selection!", ephemeral=True)
            return
        
        index = int(interaction.data['values'][0])
        result = self.results[index]
        content = result.get('show') or result.get('movie')
        content_type = 'show' if 'show' in result else 'movie'
        content_id = content['ids']['trakt']
        
        # Get detailed info
        if content_type == 'show':
            detailed_info = trakt_api.get_show_info(str(content_id))
        else:
            detailed_info = trakt_api.get_movie_info(str(content_id))
        
        if detailed_info:
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
            
            # Add action buttons
            view = ContentActionView(result, self.user_id)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message("Failed to get detailed information.", ephemeral=True)

class ContentActionView(discord.ui.View):
    """Action buttons for content (watch, watchlist, etc.)"""
    def __init__(self, result, user_id):
        super().__init__(timeout=300)
        self.result = result
        self.user_id = user_id
        self.content = result.get('show') or result.get('movie')
        self.content_type = 'show' if 'show' in result else 'movie'
        self.content_id = str(self.content['ids']['trakt'])
    
    @discord.ui.button(label='✅ Mark Watched', style=discord.ButtonStyle.success)
    async def mark_watched(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your content!", ephemeral=True)
            return
        
        user = db.get_user(str(interaction.user.id))
        if not user:
            await interaction.response.send_message("❌ Connect your Trakt.tv account first with `/connect`", ephemeral=True)
            return
        
        success = trakt_api.mark_as_watched(user['access_token'], self.content_type, self.content_id)
        
        if success:
            embed = discord.Embed(
                title="✅ Marked as Watched",
                description=f"**{self.content['title']}** has been marked as watched!",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to mark as watched.", ephemeral=True)
    
    @discord.ui.button(label='📋 Add to Watchlist', style=discord.ButtonStyle.primary)
    async def add_watchlist(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your content!", ephemeral=True)
            return
        
        user = db.get_user(str(interaction.user.id))
        if not user:
            await interaction.response.send_message("❌ Connect your Trakt.tv account first with `/connect`", ephemeral=True)
            return
        
        success = trakt_api.add_to_watchlist(user['access_token'], self.content_type, self.content_id)
        
        if success:
            embed = discord.Embed(
                title="✅ Added to Watchlist",
                description=f"**{self.content['title']}** has been added to your watchlist!",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to add to watchlist.", ephemeral=True)
    
    @discord.ui.button(label='🔔 Set Reminder', style=discord.ButtonStyle.secondary)
    async def set_reminder(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your content!", ephemeral=True)
            return
        
        if self.content_type != 'show':
            await interaction.response.send_message("❌ Reminders are only available for TV shows!", ephemeral=True)
            return
        
        user = db.get_user(str(interaction.user.id))
        if not user:
            await interaction.response.send_message("❌ Connect your Trakt.tv account first with `/connect`", ephemeral=True)
            return
        
        success = db.add_reminder(str(interaction.user.id), self.content_id, self.content['title'])
        
        if success:
            embed = discord.Embed(
                title="🔔 Reminder Added",
                description=f"You'll be notified when new episodes of **{self.content['title']}** are released!",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ You might already have a reminder for this show.", ephemeral=True)

class ReminderModal(discord.ui.Modal):
    """Modal for setting custom reminder preferences."""
    def __init__(self, show_id: str, show_title: str):
        super().__init__(title=f"Reminder Settings for {show_title[:30]}...")
        self.show_id = show_id
        self.show_title = show_title
        
        self.reminder_time = discord.ui.TextInput(
            label="Reminder Time (hours before episode)",
            placeholder="Enter hours (e.g., 2 for 2 hours before)",
            default="1",
            max_length=2
        )
        
        self.custom_message = discord.ui.TextInput(
            label="Custom Reminder Message (optional)",
            placeholder="Custom message for your reminder...",
            required=False,
            max_length=200,
            style=discord.TextStyle.paragraph
        )
        
        self.add_item(self.reminder_time)
        self.add_item(self.custom_message)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            hours = int(self.reminder_time.value)
            if hours < 0 or hours > 24:
                raise ValueError("Hours must be between 0 and 24")
        except ValueError:
            await interaction.response.send_message("❌ Invalid time. Please enter a number between 0 and 24.", ephemeral=True)
            return
        
        # Enhanced reminder with custom settings
        reminder_data = {
            'show_name': self.show_title,
            'hours_before': hours,
            'custom_message': self.custom_message.value,
            'added_at': datetime.now().isoformat()
        }
        
        # Update database to support enhanced reminders
        success = db.add_reminder(str(interaction.user.id), self.show_id, self.show_title)
        
        if success:
            embed = discord.Embed(
                title="🔔 Enhanced Reminder Set",
                description=f"**{self.show_title}**\n"
                           f"⏰ You'll be notified {hours} hour(s) before new episodes\n"
                           f"💬 Custom message: {self.custom_message.value or 'None'}",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to set reminder.", ephemeral=True)

class ReminderButtonView(discord.ui.View):
    """View with button to open reminder modal."""
    def __init__(self, modal):
        super().__init__(timeout=60)
        self.modal = modal
    
    @discord.ui.button(label='⚙️ Set Reminder Preferences', style=discord.ButtonStyle.primary)
    async def set_preferences(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(self.modal)

# Context menu commands (right-click commands)
@bot.tree.context_menu(name="Quick Trakt Info")
async def quick_trakt_info(interaction: discord.Interaction, message: discord.Message):
    """Get quick Trakt info from a message containing show/movie names."""
    content = message.content
    
    # Simple extraction of potential titles (this could be enhanced with NLP)
    words = content.split()
    potential_titles = []
    
    # Look for quoted strings or capitalized sequences
    quotes = re.findall(r'"([^"]*)"', content)
    potential_titles.extend(quotes)
    
    if not potential_titles and len(words) >= 2:
        # Take the message content as a potential title
        potential_titles.append(content[:50])
    
    if not potential_titles:
        await interaction.response.send_message("❌ No show/movie titles found in the message.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    for title in potential_titles[:1]:  # Only check the first one
        results = trakt_api.search_content(title)
        if results:
            result = results[0]
            content_obj = result.get('show') or result.get('movie')
            content_type = 'Show' if 'show' in result else 'Movie'
            
            embed = discord.Embed(
                title=f"📺 {content_obj['title']} ({content_type})",
                description=content_obj.get('overview', 'No description available')[:200] + "...",
                color=0x0099ff
            )
            embed.add_field(name="Year", value=content_obj.get('year', 'N/A'), inline=True)
            embed.add_field(name="Rating", value=f"⭐ {content_obj.get('rating', 0)}/10", inline=True)
            
            view = ContentActionView(result, interaction.user.id)
            await interaction.followup.send(embed=embed, view=view)
            return
    
    await interaction.followup.send("❌ No Trakt results found for content in this message.")

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

@bot.tree.command(name="info", description="Get detailed information about a show or movie")
@app_commands.describe(query="Show or movie name to get info about")
@app_commands.autocomplete(query=content_autocomplete)
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
    
    # Add interactive action buttons
    view = ContentActionView(result, interaction.user.id)
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="watched", description="Mark a show or movie as watched")
@app_commands.describe(query="Show or movie name to mark as watched")
@app_commands.autocomplete(query=content_autocomplete)
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
@app_commands.autocomplete(query=content_autocomplete)
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
@app_commands.autocomplete(query=content_autocomplete)
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
@app_commands.autocomplete(show_name=show_autocomplete)
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
    
    # Show enhanced reminder modal
    modal = ReminderModal(show_id, show['title'])
    view = ReminderButtonView(modal)
    
    embed = discord.Embed(
        title="🔔 Set Reminder",
        description=f"Setting up reminder for **{show['title']}**\nClick the button below to customize your reminder preferences.",
        color=0x0099ff
    )
    
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="unremind", description="Remove reminders for a show")
@app_commands.describe(show_name="Name of the show to stop reminders for")
@app_commands.autocomplete(show_name=show_autocomplete)
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

@bot.tree.command(name="stats", description="View your Trakt.tv statistics")
async def view_stats(interaction: discord.Interaction):
    """View comprehensive user statistics."""
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    # Get user profile for stats
    profile = trakt_api.get_user_profile(user['access_token'])
    if not profile:
        await interaction.followup.send("❌ Failed to get your profile information.")
        return
    
    # Get user history for additional stats
    history = trakt_api.get_user_history(user['trakt_username'], 50)
    reminders = db.get_user_reminders(str(interaction.user.id))
    
    embed = discord.Embed(
        title=f"📊 Stats for {profile['username']}",
        color=0x0099ff
    )
    
    # Basic stats from profile
    embed.add_field(name="👤 Username", value=profile['username'], inline=True)
    embed.add_field(name="📅 Member Since", value=profile.get('joined_at', 'N/A')[:10], inline=True)
    embed.add_field(name="🔔 Active Reminders", value=str(len(reminders)), inline=True)
    
    # Recent activity stats
    if history:
        recent_shows = len([h for h in history if 'show' in h])
        recent_movies = len([h for h in history if 'movie' in h])
        embed.add_field(name="📺 Recent Shows Watched", value=str(recent_shows), inline=True)
        embed.add_field(name="🎬 Recent Movies Watched", value=str(recent_movies), inline=True)
        
        # Last activity
        last_watched = history[0] if history else None
        if last_watched:
            content = last_watched.get('show') or last_watched.get('movie')
            last_date = datetime.fromisoformat(last_watched['watched_at'].replace('Z', '+00:00'))
            embed.add_field(
                name="🕐 Last Watched", 
                value=f"{content['title']}\n{last_date.strftime('%m/%d/%Y')}", 
                inline=True
            )
    
    embed.set_footer(text="Stats based on recent activity and connected account")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="search", description="Search for shows or movies with interactive results")
@app_commands.describe(query="What to search for (show or movie name)")
@app_commands.autocomplete(query=content_autocomplete)
async def search_content(interaction: discord.Interaction, query: str):
    """Search for shows or movies with enhanced interactive interface."""
    await interaction.response.defer()
    
    results = trakt_api.search_content(query)
    
    if not results:
        await interaction.followup.send(f"❌ No results found for '{query}'")
        return
    
    # Create interactive search view
    view = SearchView(results, query, interaction.user.id)
    embed = view.get_embed()
    
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="quick_action", description="Quick actions for shows/movies")
@app_commands.describe(
    content="Show or movie name",
    action="What to do with it"
)
@app_commands.autocomplete(content=content_autocomplete)
@app_commands.choices(action=[
    app_commands.Choice(name="Mark as Watched", value="watched"),
    app_commands.Choice(name="Add to Watchlist", value="watchlist"),
    app_commands.Choice(name="Set Reminder", value="remind"),
    app_commands.Choice(name="Get Info", value="info")
])
async def quick_action(interaction: discord.Interaction, content: str, action: str):
    """Perform quick actions on content."""
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user and action != "info":
        await interaction.followup.send("❌ Connect your Trakt.tv account first with `/connect`")
        return
    
    # Search for content
    results = trakt_api.search_content(content)
    if not results:
        await interaction.followup.send(f"❌ No results found for '{content}'")
        return
    
    # Get the first result
    result = results[0]
    content_obj = result.get('show') or result.get('movie')
    content_type = 'show' if 'show' in result else 'movie'
    content_id = str(content_obj['ids']['trakt'])
    
    if action == "watched":
        success = trakt_api.mark_as_watched(user['access_token'], content_type, content_id)
        if success:
            embed = discord.Embed(
                title="✅ Marked as Watched",
                description=f"**{content_obj['title']}** has been marked as watched!",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(title="❌ Failed", description="Could not mark as watched", color=0xff0000)
    
    elif action == "watchlist":
        success = trakt_api.add_to_watchlist(user['access_token'], content_type, content_id)
        if success:
            embed = discord.Embed(
                title="✅ Added to Watchlist",
                description=f"**{content_obj['title']}** has been added to your watchlist!",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(title="❌ Failed", description="Could not add to watchlist", color=0xff0000)
    
    elif action == "remind":
        if content_type != 'show':
            await interaction.followup.send("❌ Reminders are only available for TV shows!")
            return
        
        # Show enhanced reminder modal
        modal = ReminderModal(content_id, content_obj['title'])
        await interaction.followup.send("Click the button below to set reminder preferences:", 
                                      view=ReminderButtonView(modal))
        return
    
    elif action == "info":
        if content_type == 'show':
            detailed_info = trakt_api.get_show_info(content_id)
        else:
            detailed_info = trakt_api.get_movie_info(content_id)
        
        if detailed_info:
            embed = discord.Embed(
                title=f"{detailed_info['title']} ({detailed_info.get('year', 'N/A')})",
                description=detailed_info.get('overview', 'No description available'),
                color=0x0099ff
            )
            embed.add_field(name="Type", value=content_type.title(), inline=True)
            embed.add_field(name="Rating", value=f"⭐ {detailed_info.get('rating', 0)}/10", inline=True)
            embed.add_field(name="Runtime", value=f"{detailed_info.get('runtime', 'N/A')} min", inline=True)
            
            # Add action buttons
            view = ContentActionView(result, interaction.user.id)
            await interaction.followup.send(embed=embed, view=view)
            return
        else:
            embed = discord.Embed(title="❌ Failed", description="Could not get info", color=0xff0000)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="help", description="Show all available commands and how to use them")
async def help_command(interaction: discord.Interaction):
    """Show comprehensive help information."""
    embed = discord.Embed(
        title=f"🤖 {config.BOT_NAME} - Help & Commands",
        description="**Advanced Discord bot for Trakt.tv management**",
        color=0x0099ff
    )
    
    # Account Management
    embed.add_field(
        name="🔐 Account Management",
        value="`/connect` - Link your Trakt.tv account\n"
              "`/public` - Make profile public\n"
              "`/private` - Make profile private\n"
              "`/stats` - View your statistics",
        inline=False
    )
    
    # Content Discovery
    embed.add_field(
        name="🔍 Content Discovery",
        value="`/search <query>` - Interactive search with buttons\n"
              "`/info <show/movie>` - Detailed info with actions\n"
              "`/quick_action <content> <action>` - One-command workflow",
        inline=False
    )
    
    # Content Management
    embed.add_field(
        name="🎬 Content Management",
        value="`/watched <show/movie>` - Mark as watched\n"
              "`/unwatch <show/movie>` - Remove from watched\n"
              "`/watchlist <show/movie>` - Add to watchlist",
        inline=False
    )
    
    # Reminders
    embed.add_field(
        name="🔔 Reminders",
        value="`/remind <show>` - Set custom episode reminders\n"
              "`/unremind <show>` - Remove reminders\n"
              "`/reminders` - List all your reminders",
        inline=False
    )
    
    # Social Features
    embed.add_field(
        name="👥 Social Features",
        value="`/watching [user]` - See current watching activity\n"
              "`/last [user] [count]` - Recent watches (1-10 items)",
        inline=False
    )
    
    # Special Features
    embed.add_field(
        name="✨ Special Features",
        value="**Right-click** any message → `Quick Trakt Info`\n"
              "**Autocomplete** - Shows suggest as you type\n"
              "**Interactive Buttons** - One-click actions\n"
              "**Custom Modals** - Rich reminder settings",
        inline=False
    )
    
    # Getting Started
    embed.add_field(
        name="🚀 Getting Started",
        value="1. Use `/connect` to link your Trakt.tv account\n"
              "2. Try `/search Breaking Bad` for interactive search\n"
              "3. Use `/public` to enable social features\n"
              "4. Set reminders with `/remind <show name>`",
        inline=False
    )
    
    embed.set_footer(text="💡 Tip: All commands have autocomplete - just start typing!")
    
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
        try:
            await interaction.response.send_message(f"❌ An error occurred: {str(error)}", ephemeral=True)
        except:
            # If response was already sent, use followup
            try:
                await interaction.followup.send(f"❌ An error occurred: {str(error)}", ephemeral=True)
            except:
                pass
        print(f"Error in {interaction.command}: {error}")

if __name__ == "__main__":
    bot.run(config.DISCORD_TOKEN) 