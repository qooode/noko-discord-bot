import discord
from discord import app_commands
from typing import Optional, List
import requests
from views import SearchView, ContentActionView, ReminderModal
import config

# Initialize these as None and set them later
bot = None
trakt_api = None
db = None

def init_commands(discord_bot, api, database):
    """Initialize the commands module with shared objects"""
    global bot, trakt_api, db
    bot = discord_bot
    trakt_api = api
    db = database
    
    # Register all commands here
    register_account_commands()
    register_content_commands()
    register_help_commands()
    register_context_menus()

# Autocomplete functions
async def show_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    if len(current) < 2:
        return []
    try:
        results = trakt_api.search_content(current, 'show')
        choices = []
        for result in results[:10]:
            show = result['show']
            title = show['title']
            year = show.get('year', '')
            choice_name = f"{title} ({year})" if year else title
            choices.append(app_commands.Choice(name=choice_name[:100], value=title))
        return choices
    except:
        return []

async def content_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
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

def register_account_commands():
    """Register account management commands"""
    
    @bot.tree.command(name="connect", description="Connect your Trakt.tv account to the bot")
    async def connect_trakt(interaction: discord.Interaction):
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
        await interaction.response.defer()
        
        try:
            token_data = trakt_api.exchange_code_for_token(code)
            if not token_data:
                await interaction.followup.send("❌ Invalid authorization code. Please try again.")
                return
            
            user_profile = trakt_api.get_user_profile(token_data['access_token'])
            if not user_profile:
                await interaction.followup.send("❌ Failed to get user profile. Please try again.")
                return
            
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
        user = db.get_user(str(interaction.user.id))
        if not user:
            await interaction.response.send_message("❌ You need to connect your Trakt.tv account first. Use `/connect`")
            return
        
        if db.set_user_privacy(str(interaction.user.id), False):
            await interaction.response.send_message("✅ Your profile is now **private**.")
        else:
            await interaction.response.send_message("❌ Failed to update your privacy settings.")

def register_content_commands():
    """Register content management commands"""
    
    @bot.tree.command(name="search", description="Search for shows or movies with interactive results")
    @app_commands.describe(query="What to search for (show or movie name)")
    @app_commands.autocomplete(query=content_autocomplete)
    async def search_content(interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        results = trakt_api.search_content(query)
        if not results:
            await interaction.followup.send(f"❌ No results found for '{query}'")
            return
        
        view = SearchView(results, query, interaction.user.id)
        embed = view.get_embed()
        await interaction.followup.send(embed=embed, view=view)

    @bot.tree.command(name="info", description="Get detailed information about a show or movie")
    @app_commands.describe(query="Show or movie name to get info about")
    @app_commands.autocomplete(query=content_autocomplete)
    async def get_info(interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        results = trakt_api.search_content(query)
        if not results:
            await interaction.followup.send(f"❌ No results found for '{query}'")
            return
        
        result = results[0]
        content = result.get('show') or result.get('movie')
        content_type = 'show' if 'show' in result else 'movie'
        content_id = content['ids']['trakt']
        
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
        
        rating = detailed_info.get('rating', 0)
        votes = detailed_info.get('votes', 0)
        embed.add_field(name="Rating", value=f"⭐ {rating}/10\n({votes:,} votes)", inline=True)
        
        runtime = detailed_info.get('runtime', 0)
        embed.add_field(name="Runtime", value=f"⏱️ {runtime} min" if runtime else "N/A", inline=True)
        
        # Add poster
        tmdb_id = detailed_info.get('ids', {}).get('tmdb')
        if tmdb_id:
            embed.set_image(url=f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg")
        
        view = ContentActionView(result, interaction.user.id)
        await interaction.followup.send(embed=embed, view=view)

    @bot.tree.command(name="watched", description="Mark a show or movie as watched")
    @app_commands.describe(query="Show or movie name to mark as watched")
    @app_commands.autocomplete(query=content_autocomplete)
    async def mark_watched(interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        user = db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
            return
        
        results = trakt_api.search_content(query)
        if not results:
            await interaction.followup.send(f"❌ No results found for '{query}'")
            return
        
        result = results[0]
        content = result.get('show') or result.get('movie')
        content_type = 'show' if 'show' in result else 'movie'
        content_id = str(content['ids']['trakt'])
        
        if content_type == 'show':
            # For shows, redirect to management
            from management import ShowProgressView
            embed = discord.Embed(
                title=f"📺 {content['title']} - Show Management",
                description="For TV shows, use the advanced management options below.",
                color=0x0099ff
            )
            
            tmdb_id = content.get('ids', {}).get('tmdb')
            if tmdb_id:
                embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
            
            view = ShowProgressView(result, interaction.user.id, user['access_token'])
            await interaction.followup.send(embed=embed, view=view)
        else:
            # For movies, simple mark
            success = trakt_api.mark_as_watched(user['access_token'], content_type, content_id)
            
            if success:
                embed = discord.Embed(
                    title="✅ Movie Marked as Watched",
                    description=f"**{content['title']}** has been marked as watched!",
                    color=0x00ff00
                )
                tmdb_id = content.get('ids', {}).get('tmdb')
                if tmdb_id:
                    embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ Failed to mark as watched. Please try again.")

    @bot.tree.command(name="watchlist", description="Add a show or movie to your watchlist")
    @app_commands.describe(query="Show or movie name to add to watchlist")
    @app_commands.autocomplete(query=content_autocomplete)
    async def add_to_watchlist(interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        user = db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
            return
        
        results = trakt_api.search_content(query)
        if not results:
            await interaction.followup.send(f"❌ No results found for '{query}'")
            return
        
        result = results[0]
        content = result.get('show') or result.get('movie')
        content_type = 'show' if 'show' in result else 'movie'
        content_id = str(content['ids']['trakt'])
        
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

    @bot.tree.command(name="remind", description="Set up reminders for new episodes of a show")
    @app_commands.describe(show_name="Name of the show to get reminders for")
    @app_commands.autocomplete(show_name=show_autocomplete)
    async def add_reminder(interaction: discord.Interaction, show_name: str):
        await interaction.response.defer()
        
        user = db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
            return
        
        results = trakt_api.search_content(show_name, 'show')
        if not results:
            await interaction.followup.send(f"❌ No shows found for '{show_name}'")
            return
        
        show = results[0]['show']
        show_id = str(show['ids']['trakt'])
        
        modal = ReminderModal(show_id, show['title'])
        await interaction.response.send_modal(modal)

    @bot.tree.command(name="reminders", description="List all your active reminders")
    async def list_reminders(interaction: discord.Interaction):
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
        
        from datetime import datetime
        for show_id, reminder_data in reminders.items():
            show_name = reminder_data['show_name']
            added_at = datetime.fromisoformat(reminder_data['added_at'])
            embed.add_field(
                name=show_name,
                value=f"Added on {added_at.strftime('%m/%d/%Y')}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

def register_help_commands():
    """Register help commands"""
    
    @bot.tree.command(name="help", description="Show all available commands and how to use them")
    async def help_command(interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"🤖 {config.BOT_NAME} - Help & Commands",
            description="**Advanced Discord bot for Trakt.tv management**",
            color=0x0099ff
        )
        
        # Account Management
        embed.add_field(
            name="🔐 Account",
            value="`/connect` - Link your Trakt.tv account\n"
                  "`/public` - Make profile public\n"
                  "`/private` - Make profile private",
            inline=False
        )
        
        # Content
        embed.add_field(
            name="🔍 Content",
            value="`/search <query>` - Interactive search\n"
                  "`/info <show/movie>` - Detailed info\n"
                  "`/watched <show/movie>` - Mark as watched\n"
                  "`/watchlist <show/movie>` - Add to watchlist",
            inline=False
        )
        
        # Management
        embed.add_field(
            name="🎬 Management",
            value="`/progress <show>` - View & manage progress\n"
                  "`/manage <show>` - Advanced show management\n"
                  "`/continue` - Shows you can continue\n"
                  "`/episode <show> <season> <ep>` - Mark episode",
            inline=False
        )
        
        # Social & Reminders
        embed.add_field(
            name="👥 Social & More",
            value="`/community` - Live community activity\n"
                  "`/trends [days]` - Community trends\n"
                  "`/watching [user]` - Current watching\n"
                  "`/remind <show>` - Set reminders",
            inline=False
        )
        
        embed.set_footer(text="💡 All commands have autocomplete - just start typing!")
        await interaction.response.send_message(embed=embed)

def register_context_menus():
    """Register context menu commands"""
    
    @bot.tree.context_menu(name="Quick Trakt Info")
    async def quick_trakt_info(interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        
        content = message.content
        if len(content) < 3:
            await interaction.followup.send("❌ No content to search for.", ephemeral=True)
            return
        
        # Take first 50 chars as search query
        query = content[:50].strip()
        
        results = trakt_api.search_content(query)
        if results:
            result = results[0]
            content_obj = result.get('show') or result.get('movie')
            content_type = 'Show' if 'show' in result else 'Movie'
            
            embed = discord.Embed(
                title=f"📺 {content_obj['title']} ({content_type})",
                description=content_obj.get('overview', 'No description available')[:300],
                color=0x0099ff
            )
            
            year = content_obj.get('year', 'N/A')
            rating = content_obj.get('rating', 0)
            
            embed.add_field(name="Year", value=f"📅 {year}", inline=True)
            embed.add_field(name="Rating", value=f"⭐ {rating}/10", inline=True)
            
            tmdb_id = content_obj.get('ids', {}).get('tmdb')
            if tmdb_id:
                embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
            
            view = ContentActionView(result, interaction.user.id)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send("❌ No Trakt results found for content in this message.")

# Error handler
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    try:
        await interaction.response.send_message(f"❌ An error occurred: {str(error)}", ephemeral=True)
    except:
        try:
            await interaction.followup.send(f"❌ An error occurred: {str(error)}", ephemeral=True)
        except:
            pass
    print(f"Error in {interaction.command}: {error}")

# Register error handler when bot is available
def register_error_handler():
    bot.tree.error(on_app_command_error) 