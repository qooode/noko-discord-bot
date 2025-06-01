import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import re
from typing import Optional, List
import json
import requests

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
            votes = content.get('votes', 0)
            runtime = content.get('runtime', 0)
            status = content.get('status', '')
            
            # Build rich field value with more details
            field_value = f"⭐ **{rating}/10** ({votes:,} votes)\n"
            
            if runtime:
                field_value += f"⏱️ **{runtime} min** • "
            if status and content_type == 'Show':
                field_value += f"📺 **{status.title()}**\n"
            else:
                field_value += "\n"
            
            # Add genres if available
            genres = content.get('genres', [])
            if genres:
                field_value += f"🏷️ {', '.join(genres[:3])}\n"
            
            # Add overview
            overview = content.get('overview', 'No description available')
            field_value += f"{overview[:120]}..." if len(overview) > 120 else overview
            
            embed.add_field(
                name=f"{i}. {content['title']} ({year}) - {content_type}",
                value=field_value,
                inline=False
            )
        
        # Add poster image from first result if available
        if page_results:
            first_content = page_results[0].get('show') or page_results[0].get('movie')
            tmdb_id = first_content.get('ids', {}).get('tmdb')
            if tmdb_id:
                poster_url = f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg"
                embed.set_thumbnail(url=poster_url)
        
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
            
            # Enhanced fields with more data
            embed.add_field(name="Type", value=content_type.title(), inline=True)
            
            rating = detailed_info.get('rating', 0)
            votes = detailed_info.get('votes', 0)
            embed.add_field(name="Rating", value=f"⭐ {rating}/10\n({votes:,} votes)", inline=True)
            
            runtime = detailed_info.get('runtime', 0)
            embed.add_field(name="Runtime", value=f"⏱️ {runtime} min" if runtime else "N/A", inline=True)
            
            if content_type == 'show':
                status = detailed_info.get('status', 'N/A')
                network = detailed_info.get('network', 'N/A')
                embed.add_field(name="Status", value=f"📺 {status}", inline=True)
                embed.add_field(name="Network", value=f"📡 {network}", inline=True)
                
                # Add aired info for shows
                aired = detailed_info.get('first_aired', '')
                if aired:
                    aired_date = aired[:10]  # Get just the date part
                    embed.add_field(name="First Aired", value=f"📅 {aired_date}", inline=True)
            else:
                # Movie specific info
                released = detailed_info.get('released', '')
                if released:
                    embed.add_field(name="Released", value=f"📅 {released}", inline=True)
                
                # Add certification if available
                certification = detailed_info.get('certification', '')
                if certification:
                    embed.add_field(name="Rating", value=f"🎬 {certification}", inline=True)
            
            # Add genres
            genres = detailed_info.get('genres', [])
            if genres:
                embed.add_field(name="Genres", value=f"🏷️ {', '.join(genres[:5])}", inline=False)
            
            # Add languages if available
            languages = detailed_info.get('available_translations', [])
            if languages:
                embed.add_field(name="Languages", value=f"🌍 {', '.join(languages[:8])}", inline=False)
            
            # Add poster image
            tmdb_id = detailed_info.get('ids', {}).get('tmdb')
            if tmdb_id:
                poster_url = f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg"
                embed.set_image(url=poster_url)
            
            # Add trailer link if available
            trailer = detailed_info.get('trailer')
            if trailer:
                embed.add_field(name="Trailer", value=f"🎥 [Watch Trailer]({trailer})", inline=False)
            
            # Add homepage link if available
            homepage = detailed_info.get('homepage')
            if homepage:
                embed.add_field(name="Official Site", value=f"🌐 [Visit Homepage]({homepage})", inline=False)
            
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

class ShowProgressView(discord.ui.View):
    """Interactive view for managing show watching progress."""
    def __init__(self, show_result, user_id, access_token):
        super().__init__(timeout=300)
        self.show_result = show_result
        self.user_id = user_id
        self.access_token = access_token
        self.show = show_result.get('show')
        self.show_id = str(self.show['ids']['trakt'])
        
    def get_progress_embed(self, progress_data=None):
        """Create embed showing show progress."""
        embed = discord.Embed(
            title=f"📺 {self.show['title']} - Watch Progress",
            color=0x0099ff
        )
        
        if progress_data:
            # Show detailed progress
            completed = progress_data.get('completed', 0)
            total = progress_data.get('episodes', 0)
            percentage = (completed / total * 100) if total > 0 else 0
            
            embed.add_field(
                name="📊 Overall Progress",
                value=f"**{completed}/{total} episodes** ({percentage:.1f}%)\n"
                      f"{'🟩' * int(percentage // 10)}{'⬜' * (10 - int(percentage // 10))}",
                inline=False
            )
            
            # Show season progress
            seasons = progress_data.get('seasons', [])
            if seasons:
                season_text = ""
                for season in seasons[:5]:  # Show first 5 seasons
                    season_num = season['number']
                    s_completed = season.get('completed', 0)
                    s_total = season.get('episodes', 0)
                    s_percentage = (s_completed / s_total * 100) if s_total > 0 else 0
                    
                    status = "✅" if s_completed == s_total else "🔄" if s_completed > 0 else "⭕"
                    season_text += f"{status} **Season {season_num}**: {s_completed}/{s_total} ({s_percentage:.0f}%)\n"
                
                if len(seasons) > 5:
                    season_text += f"*...and {len(seasons) - 5} more seasons*"
                
                embed.add_field(
                    name="🎬 Season Progress",
                    value=season_text,
                    inline=False
                )
        else:
            embed.add_field(
                name="📊 Progress",
                value="Loading progress data...",
                inline=False
            )
        
        # Add poster
        tmdb_id = self.show.get('ids', {}).get('tmdb')
        if tmdb_id:
            poster_url = f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg"
            embed.set_thumbnail(url=poster_url)
        
        return embed
    
    @discord.ui.button(label='📊 View Progress', style=discord.ButtonStyle.primary)
    async def view_progress(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your show!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Get detailed progress
        progress = trakt_api.get_show_progress(self.access_token, self.show_id)
        embed = self.get_progress_embed(progress)
        
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
    
    @discord.ui.button(label='🎭 Manage Seasons', style=discord.ButtonStyle.secondary)
    async def manage_seasons(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your show!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Get seasons
        seasons = trakt_api.get_show_seasons(self.show_id)
        if not seasons:
            await interaction.followup.send("❌ Could not load seasons for this show.", ephemeral=True)
            return
        
        view = SeasonSelectView(self.show, seasons, self.user_id, self.access_token)
        embed = view.get_seasons_embed()
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label='✅ Mark All Watched', style=discord.ButtonStyle.success)
    async def mark_all_watched(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your show!", ephemeral=True)
            return
        
        success = trakt_api.mark_as_watched(self.access_token, 'show', self.show_id)
        
        if success:
            embed = discord.Embed(
                title="✅ Show Marked as Watched",
                description=f"All episodes of **{self.show['title']}** have been marked as watched!",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Failed",
                description="Could not mark show as watched.",
                color=0xff0000
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label='❌ Unmark All', style=discord.ButtonStyle.danger)
    async def unmark_all_watched(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your show!", ephemeral=True)
            return
        
        success = trakt_api.unmark_as_watched(self.access_token, 'show', self.show_id)
        
        if success:
            embed = discord.Embed(
                title="❌ Show Unmarked",
                description=f"**{self.show['title']}** has been removed from your watched history!",
                color=0xff6600
            )
        else:
            embed = discord.Embed(
                title="❌ Failed",
                description="Could not unmark show.",
                color=0xff0000
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SeasonSelectView(discord.ui.View):
    """View for selecting and managing specific seasons."""
    def __init__(self, show, seasons, user_id, access_token):
        super().__init__(timeout=300)
        self.show = show
        self.seasons = seasons
        self.user_id = user_id
        self.access_token = access_token
        self.show_id = str(show['ids']['trakt'])
        
        # Add season dropdown
        options = []
        for season in seasons:
            if season['number'] == 0:  # Skip specials for now
                continue
            
            episode_count = len(season.get('episodes', []))
            options.append(discord.SelectOption(
                label=f"Season {season['number']}",
                description=f"{episode_count} episodes",
                value=str(season['number'])
            ))
        
        if options:
            select = discord.ui.Select(
                placeholder="Choose a season to manage...",
                options=options[:25]  # Discord limit
            )
            select.callback = self.season_callback
            self.add_item(select)
    
    def get_seasons_embed(self):
        """Create embed showing all seasons."""
        embed = discord.Embed(
            title=f"🎭 {self.show['title']} - Season Management",
            description="Select a season to manage episodes or mark entire seasons as watched/unwatched.",
            color=0x9d4edd
        )
        
        season_text = ""
        for season in self.seasons:
            if season['number'] == 0:  # Skip specials
                continue
            
            episode_count = len(season.get('episodes', []))
            season_text += f"**Season {season['number']}**: {episode_count} episodes\n"
        
        embed.add_field(
            name="📺 Available Seasons",
            value=season_text,
            inline=False
        )
        
        return embed
    
    async def season_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your show!", ephemeral=True)
            return
        
        season_number = int(interaction.data['values'][0])
        
        # Find the selected season
        selected_season = None
        for season in self.seasons:
            if season['number'] == season_number:
                selected_season = season
                break
        
        if not selected_season:
            await interaction.response.send_message("❌ Season not found.", ephemeral=True)
            return
        
        # Get detailed episode info
        episodes = trakt_api.get_season_episodes(self.show_id, season_number)
        
        view = EpisodeManageView(self.show, selected_season, episodes, self.user_id, self.access_token)
        embed = view.get_episode_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class EpisodeManageView(discord.ui.View):
    """View for managing individual episodes in a season."""
    def __init__(self, show, season, episodes, user_id, access_token):
        super().__init__(timeout=300)
        self.show = show
        self.season = season
        self.episodes = episodes
        self.user_id = user_id
        self.access_token = access_token
        self.show_id = str(show['ids']['trakt'])
        self.season_number = season['number']
        
        # Add episode dropdown for individual episode management
        if episodes:
            options = []
            for episode in episodes[:25]:  # Discord limit
                episode_title = episode.get('title', f'Episode {episode["number"]}')
                if len(episode_title) > 45:
                    episode_title = episode_title[:42] + "..."
                
                options.append(discord.SelectOption(
                    label=f"E{episode['number']}: {episode_title}",
                    description=f"Runtime: {episode.get('runtime', 'N/A')} min",
                    value=str(episode['number'])
                ))
            
            if options:
                select = discord.ui.Select(
                    placeholder="Choose an episode to mark/unmark...",
                    options=options
                )
                select.callback = self.episode_callback
                self.add_item(select)
    
    def get_episode_embed(self):
        """Create embed showing season episodes."""
        embed = discord.Embed(
            title=f"📺 {self.show['title']} - Season {self.season_number}",
            description=f"Manage individual episodes or mark the entire season.",
            color=0x0099ff
        )
        
        # Show episode list (first 10)
        episode_text = ""
        for i, episode in enumerate(self.episodes[:10]):
            title = episode.get('title', f'Episode {episode["number"]}')
            runtime = episode.get('runtime', 'N/A')
            episode_text += f"**E{episode['number']}**: {title} ({runtime} min)\n"
        
        if len(self.episodes) > 10:
            episode_text += f"*...and {len(self.episodes) - 10} more episodes*"
        
        embed.add_field(
            name=f"📋 Episodes ({len(self.episodes)} total)",
            value=episode_text,
            inline=False
        )
        
        return embed
    
    async def episode_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your episode selection!", ephemeral=True)
            return
        
        episode_number = int(interaction.data['values'][0])
        
        # Find the episode
        selected_episode = None
        for episode in self.episodes:
            if episode['number'] == episode_number:
                selected_episode = episode
                break
        
        if not selected_episode:
            await interaction.response.send_message("❌ Episode not found.", ephemeral=True)
            return
        
        # Create action view for the specific episode
        view = EpisodeActionView(self.show, self.season_number, selected_episode, self.user_id, self.access_token)
        
        embed = discord.Embed(
            title=f"📺 {self.show['title']} S{self.season_number}E{episode_number}",
            description=f"**{selected_episode.get('title', 'Episode')}**\n\n"
                       f"{selected_episode.get('overview', 'No description available')}",
            color=0x0099ff
        )
        
        embed.add_field(name="Runtime", value=f"⏱️ {selected_episode.get('runtime', 'N/A')} min", inline=True)
        embed.add_field(name="Rating", value=f"⭐ {selected_episode.get('rating', 0)}/10", inline=True)
        
        if selected_episode.get('first_aired'):
            aired = selected_episode['first_aired'][:10]
            embed.add_field(name="Aired", value=f"📅 {aired}", inline=True)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label='✅ Mark Season Watched', style=discord.ButtonStyle.success)
    async def mark_season_watched(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your season!", ephemeral=True)
            return
        
        success = trakt_api.mark_season_watched(self.access_token, self.show_id, self.season_number)
        
        if success:
            embed = discord.Embed(
                title="✅ Season Marked as Watched",
                description=f"Season {self.season_number} of **{self.show['title']}** has been marked as watched!",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Failed",
                description="Could not mark season as watched.",
                color=0xff0000
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label='❌ Unmark Season', style=discord.ButtonStyle.danger)
    async def unmark_season_watched(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your season!", ephemeral=True)
            return
        
        success = trakt_api.unmark_season_watched(self.access_token, self.show_id, self.season_number)
        
        if success:
            embed = discord.Embed(
                title="❌ Season Unmarked",
                description=f"Season {self.season_number} of **{self.show['title']}** has been removed from watched!",
                color=0xff6600
            )
        else:
            embed = discord.Embed(
                title="❌ Failed",
                description="Could not unmark season.",
                color=0xff0000
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class EpisodeActionView(discord.ui.View):
    """Action buttons for individual episode management."""
    def __init__(self, show, season_number, episode, user_id, access_token):
        super().__init__(timeout=300)
        self.show = show
        self.season_number = season_number
        self.episode = episode
        self.user_id = user_id
        self.access_token = access_token
        self.show_id = str(show['ids']['trakt'])
        self.episode_number = episode['number']
    
    @discord.ui.button(label='✅ Mark Watched', style=discord.ButtonStyle.success)
    async def mark_episode_watched(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your episode!", ephemeral=True)
            return
        
        success = trakt_api.mark_episode_watched(
            self.access_token, 
            self.show_id, 
            self.season_number, 
            self.episode_number
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Episode Marked as Watched",
                description=f"**{self.show['title']}** S{self.season_number}E{self.episode_number} has been marked as watched!",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Failed",
                description="Could not mark episode as watched.",
                color=0xff0000
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label='❌ Unmark Episode', style=discord.ButtonStyle.danger)
    async def unmark_episode_watched(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your episode!", ephemeral=True)
            return
        
        success = trakt_api.unmark_episode_watched(
            self.access_token, 
            self.show_id, 
            self.season_number, 
            self.episode_number
        )
        
        if success:
            embed = discord.Embed(
                title="❌ Episode Unmarked",
                description=f"**{self.show['title']}** S{self.season_number}E{self.episode_number} has been removed from watched!",
                color=0xff6600
            )
        else:
            embed = discord.Embed(
                title="❌ Failed",
                description="Could not unmark episode.",
                color=0xff0000
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
                description=content_obj.get('overview', 'No description available')[:300] + "..." if len(content_obj.get('overview', '')) > 300 else content_obj.get('overview', 'No description available'),
                color=0x0099ff
            )
            
            # Enhanced quick info
            year = content_obj.get('year', 'N/A')
            rating = content_obj.get('rating', 0)
            votes = content_obj.get('votes', 0)
            runtime = content_obj.get('runtime', 0)
            
            embed.add_field(name="Year", value=f"📅 {year}", inline=True)
            embed.add_field(name="Rating", value=f"⭐ {rating}/10\n({votes:,} votes)" if votes > 0 else f"⭐ {rating}/10", inline=True)
            
            if runtime:
                embed.add_field(name="Runtime", value=f"⏱️ {runtime} min", inline=True)
            
            # Add genres if available
            genres = content_obj.get('genres', [])
            if genres:
                embed.add_field(name="Genres", value=f"🏷️ {', '.join(genres[:3])}", inline=False)
            
            # Add poster thumbnail
            tmdb_id = content_obj.get('ids', {}).get('tmdb')
            if tmdb_id:
                poster_url = f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg"
                embed.set_thumbnail(url=poster_url)
            
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
    
    # Enhanced fields with richer data
    embed.add_field(name="Type", value=content_type.title(), inline=True)
    
    rating = detailed_info.get('rating', 0)
    votes = detailed_info.get('votes', 0)
    embed.add_field(name="Rating", value=f"⭐ {rating}/10\n({votes:,} votes)", inline=True)
    
    runtime = detailed_info.get('runtime', 0)
    embed.add_field(name="Runtime", value=f"⏱️ {runtime} min" if runtime else "N/A", inline=True)
    
    if content_type == 'show':
        status = detailed_info.get('status', 'N/A')
        network = detailed_info.get('network', 'N/A')
        embed.add_field(name="Status", value=f"📺 {status}", inline=True)
        embed.add_field(name="Network", value=f"📡 {network}", inline=True)
        
        # Add aired info
        aired = detailed_info.get('first_aired', '')
        if aired:
            aired_date = aired[:10]
            embed.add_field(name="First Aired", value=f"📅 {aired_date}", inline=True)
    else:
        # Movie specific info
        released = detailed_info.get('released', '')
        if released:
            embed.add_field(name="Released", value=f"📅 {released}", inline=True)
        
        certification = detailed_info.get('certification', '')
        if certification:
            embed.add_field(name="Certification", value=f"🎬 {certification}", inline=True)
    
    # Add genres
    genres = detailed_info.get('genres', [])
    if genres:
        embed.add_field(name="Genres", value=f"🏷️ {', '.join(genres[:5])}", inline=False)
    
    # Add languages
    languages = detailed_info.get('available_translations', [])
    if languages:
        embed.add_field(name="Languages", value=f"🌍 {', '.join(languages[:8])}", inline=False)
    
    # Add poster image
    tmdb_id = detailed_info.get('ids', {}).get('tmdb')
    if tmdb_id:
        poster_url = f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg"
        embed.set_image(url=poster_url)
    
    # Add links if available
    trailer = detailed_info.get('trailer')
    if trailer:
        embed.add_field(name="Trailer", value=f"🎥 [Watch Trailer]({trailer})", inline=False)
    
    homepage = detailed_info.get('homepage')
    if homepage:
        embed.add_field(name="Official Site", value=f"🌐 [Visit Homepage]({homepage})", inline=False)
    
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
    
    if content_type == 'show':
        # For shows, use the advanced progress management
        embed = discord.Embed(
            title=f"📺 {content['title']} - Show Management",
            description="For TV shows, use the advanced management options below to mark specific seasons/episodes or the entire show.",
            color=0x0099ff
        )
        
        # Add poster
        tmdb_id = content.get('ids', {}).get('tmdb')
        if tmdb_id:
            poster_url = f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg"
            embed.set_thumbnail(url=poster_url)
        
        view = ShowProgressView(result, interaction.user.id, user['access_token'])
        await interaction.followup.send(embed=embed, view=view)
    else:
        # For movies, keep the simple functionality
        success = trakt_api.mark_as_watched(user['access_token'], content_type, content_id)
        
        if success:
            embed = discord.Embed(
                title="✅ Movie Marked as Watched",
                description=f"**{content['title']}** has been marked as watched!",
                color=0x00ff00
            )
            
            # Add poster
            tmdb_id = content.get('ids', {}).get('tmdb')
            if tmdb_id:
                poster_url = f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg"
                embed.set_thumbnail(url=poster_url)
            
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
            value=f"**S{episode['season']}E{episode['number']}**: {episode.get('title', 'Episode')}\n"
                  f"⭐ {content.get('rating', 0)}/10 • ⏱️ {content.get('runtime', 'N/A')} min",
            inline=False
        )
    else:
        embed.add_field(
            name=f"{content['title']} ({content_type})",
            value=f"{content.get('overview', 'No description available')[:200]}...\n"
                  f"⭐ {content.get('rating', 0)}/10 • ⏱️ {content.get('runtime', 'N/A')} min",
            inline=False
        )
    
    # Add poster image if available
    tmdb_id = content.get('ids', {}).get('tmdb')
    if tmdb_id:
        poster_url = f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg"
        embed.set_thumbnail(url=poster_url)
    
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
    
    for i, item in enumerate(history):
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
        
        # Enhanced field with more details
        field_value = f"📅 **{watched_at.strftime('%m/%d/%Y at %I:%M %p')}**\n"
        
        rating = content.get('rating', 0)
        if rating > 0:
            field_value += f"⭐ {rating}/10"
        
        runtime = content.get('runtime', 0)
        if runtime > 0:
            field_value += f" • ⏱️ {runtime} min"
        
        # Add a brief overview for first few items
        if i < 3:  # Only for first 3 items to avoid too much text
            overview = content.get('overview', '')
            if overview:
                field_value += f"\n{overview[:100]}..." if len(overview) > 100 else f"\n{overview}"
        
        embed.add_field(
            name=title,
            value=field_value,
            inline=False
        )
    
    # Add poster from most recent item
    if history:
        recent_content = history[0].get('show') or history[0].get('movie')
        tmdb_id = recent_content.get('ids', {}).get('tmdb')
        if tmdb_id:
            poster_url = f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg"
            embed.set_thumbnail(url=poster_url)
    
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
            
            # Enhanced info display
            embed.add_field(name="Type", value=content_type.title(), inline=True)
            
            rating = detailed_info.get('rating', 0)
            votes = detailed_info.get('votes', 0)
            embed.add_field(name="Rating", value=f"⭐ {rating}/10\n({votes:,} votes)", inline=True)
            
            runtime = detailed_info.get('runtime', 0)
            embed.add_field(name="Runtime", value=f"⏱️ {runtime} min" if runtime else "N/A", inline=True)
            
            # Add poster image
            tmdb_id = detailed_info.get('ids', {}).get('tmdb')
            if tmdb_id:
                poster_url = f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg"
                embed.set_image(url=poster_url)
            
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
              "`/watchlist <show/movie>` - Add to watchlist\n"
              "`/progress <show>` - **View & manage show progress** 📊\n"
              "`/manage <show>` - **Advanced show management** 🎭\n"
              "`/continue` - **Shows you can continue watching** ▶️\n"
              "`/episode <show> <season> <ep>` - **Mark specific episode**",
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
              "`/last [user] [count]` - Recent watches (1-10 items)\n"
              "`/community` - **Live community activity** 🔴\n"
              "`/trends [days]` - **Community trends & stats** 📈",
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

@bot.tree.command(name="community", description="See what the community is watching right now")
async def community_watching(interaction: discord.Interaction):
    """See what the community is watching right now."""
    await interaction.response.defer()
    
    # Get all public users
    public_users = db.get_public_users()
    user_stats = db.get_user_count()
    
    if not public_users:
        embed = discord.Embed(
            title="👥 Community Watch",
            description="No public profiles available. Encourage users to use `/public` to join the community!",
            color=0xff6600
        )
        await interaction.followup.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="🌍 Community Watch - Live Activity",
        description=f"Real-time activity from {len(public_users)} public members",
        color=0x00ff88
    )
    
    # Track what everyone is watching
    currently_watching = []
    trending_shows = {}
    trending_movies = {}
    active_users = []
    
    for user in public_users:
        try:
            watching = trakt_api.get_watching_now(user['trakt_username'])
            if watching:
                currently_watching.append({
                    'user': user,
                    'watching': watching
                })
                
                # Track trending content
                content = watching.get('show') or watching.get('movie')
                if content:
                    content_title = content['title']
                    content_type = 'show' if 'show' in watching else 'movie'
                    
                    if content_type == 'show':
                        trending_shows[content_title] = trending_shows.get(content_title, 0) + 1
                    else:
                        trending_movies[content_title] = trending_movies.get(content_title, 0) + 1
                    
                    active_users.append(user['trakt_username'])
        except:
            continue  # Skip users with API issues
    
    # Community stats
    embed.add_field(
        name="📊 Community Stats",
        value=f"👥 **{user_stats['total']} total** • **{user_stats['public']} public** • **{len(active_users)} active now**",
        inline=False
    )
    
    # Show trending content
    if trending_shows or trending_movies:
        trending_text = ""
        
        # Top trending shows
        if trending_shows:
            top_shows = sorted(trending_shows.items(), key=lambda x: x[1], reverse=True)[:3]
            trending_text += "📺 **Trending Shows:**\n"
            for show, count in top_shows:
                trending_text += f"• **{show}** ({count} watching)\n"
        
        # Top trending movies  
        if trending_movies:
            top_movies = sorted(trending_movies.items(), key=lambda x: x[1], reverse=True)[:3]
            trending_text += "\n🎬 **Trending Movies:**\n"
            for movie, count in top_movies:
                trending_text += f"• **{movie}** ({count} watching)\n"
        
        embed.add_field(
            name="🔥 What's Hot Right Now",
            value=trending_text,
            inline=False
        )
    
    # Show live activity (up to 5 users)
    if currently_watching:
        activity_text = ""
        for i, activity in enumerate(currently_watching[:5]):
            user = activity['user']
            watching = activity['watching']
            content = watching.get('show') or watching.get('movie')
            
            if 'episode' in watching:
                episode = watching['episode']
                activity_text += f"📺 **{user['trakt_username']}** watching **{content['title']}**\n"
                activity_text += f"   S{episode['season']}E{episode['number']}: {episode.get('title', 'Episode')}\n"
            else:
                activity_text += f"🎬 **{user['trakt_username']}** watching **{content['title']}**\n"
            
            # Add rating if available
            rating = content.get('rating', 0)
            if rating > 0:
                activity_text += f"   ⭐ {rating}/10\n"
            
            activity_text += "\n"
        
        if len(currently_watching) > 5:
            activity_text += f"*...and {len(currently_watching) - 5} more users are watching*"
        
        embed.add_field(
            name=f"🔴 Live Activity ({len(currently_watching)} active)",
            value=activity_text,
            inline=False
        )
    else:
        embed.add_field(
            name="😴 Community Status",
            value="No one is currently watching anything. Time to start a watch party!",
            inline=False
        )
    
    # Add community poster from most popular content
    if trending_shows:
        top_show = max(trending_shows.items(), key=lambda x: x[1])[0]
        # Try to get poster for the top trending show
        search_results = trakt_api.search_content(top_show, 'show')
        if search_results:
            content = search_results[0].get('show')
            tmdb_id = content.get('ids', {}).get('tmdb')
            if tmdb_id:
                poster_url = f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg"
                embed.set_thumbnail(url=poster_url)
    elif trending_movies:
        top_movie = max(trending_movies.items(), key=lambda x: x[1])[0]
        search_results = trakt_api.search_content(top_movie, 'movie')
        if search_results:
            content = search_results[0].get('movie')
            tmdb_id = content.get('ids', {}).get('tmdb')
            if tmdb_id:
                poster_url = f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg"
                embed.set_thumbnail(url=poster_url)
    
    # Add footer with refresh info
    embed.set_footer(text="🔄 Live data • Use /public to join the community watch!")
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="trends", description="See what the community has been watching this week")
@app_commands.describe(days="Number of days to look back (1-14)")
async def community_trends(interaction: discord.Interaction, days: int = 7):
    """See what the community has been watching over the past week."""
    await interaction.response.defer()
    
    if days < 1 or days > 14:
        days = 7
    
    # Get all public users
    public_users = db.get_public_users()
    
    if not public_users:
        embed = discord.Embed(
            title="📈 Community Trends",
            description="No public profiles available. Encourage users to use `/public` to join the community!",
            color=0xff6600
        )
        await interaction.followup.send(embed=embed)
        return
    
    embed = discord.Embed(
        title=f"📈 Community Trends - Past {days} Days",
        description=f"Aggregated activity from {len(public_users)} public members",
        color=0x9d4edd
    )
    
    # Collect all watch history
    all_shows = {}
    all_movies = {}
    total_episodes = 0
    total_movies = 0
    most_active_users = {}
    
    for user in public_users:
        try:
            # Get more history entries to cover the time period
            history = trakt_api.get_user_history(user['trakt_username'], 50)
            
            user_activity = 0
            for item in history:
                watched_date = datetime.fromisoformat(item['watched_at'].replace('Z', '+00:00'))
                days_ago = (datetime.now().replace(tzinfo=watched_date.tzinfo) - watched_date).days
                
                if days_ago <= days:
                    content = item.get('show') or item.get('movie')
                    content_title = content['title']
                    
                    if 'show' in item:
                        all_shows[content_title] = all_shows.get(content_title, 0) + 1
                        total_episodes += 1
                    else:
                        all_movies[content_title] = all_movies.get(content_title, 0) + 1
                        total_movies += 1
                    
                    user_activity += 1
            
            if user_activity > 0:
                most_active_users[user['trakt_username']] = user_activity
                
        except:
            continue
    
    # Community overview stats
    embed.add_field(
        name="📊 Community Activity Overview",
        value=f"📺 **{total_episodes} episodes** watched\n"
              f"🎬 **{total_movies} movies** watched\n"
              f"👥 **{len(most_active_users)} active** members\n"
              f"🏆 **{len(all_shows) + len(all_movies)} unique** titles",
        inline=False
    )
    
    # Top trending shows
    if all_shows:
        top_shows = sorted(all_shows.items(), key=lambda x: x[1], reverse=True)[:5]
        shows_text = ""
        for i, (show, count) in enumerate(top_shows, 1):
            shows_text += f"{i}. **{show}** • {count} episodes\n"
        
        embed.add_field(
            name="📺 Trending Shows",
            value=shows_text,
            inline=True
        )
    
    # Top trending movies
    if all_movies:
        top_movies = sorted(all_movies.items(), key=lambda x: x[1], reverse=True)[:5]
        movies_text = ""
        for i, (movie, count) in enumerate(top_movies, 1):
            movies_text += f"{i}. **{movie}** • {count} watches\n"
        
        embed.add_field(
            name="🎬 Trending Movies", 
            value=movies_text,
            inline=True
        )
    
    # Most active users
    if most_active_users:
        top_users = sorted(most_active_users.items(), key=lambda x: x[1], reverse=True)[:5]
        users_text = ""
        for i, (username, activity) in enumerate(top_users, 1):
            users_text += f"{i}. **{username}** • {activity} watches\n"
        
        embed.add_field(
            name="🔥 Most Active Members",
            value=users_text,
            inline=True
        )
    
    # Add poster from top trending content
    top_content = None
    if all_shows:
        top_show = max(all_shows.items(), key=lambda x: x[1])[0]
        search_results = trakt_api.search_content(top_show, 'show')
        if search_results:
            top_content = search_results[0].get('show')
    
    if not top_content and all_movies:
        top_movie = max(all_movies.items(), key=lambda x: x[1])[0] 
        search_results = trakt_api.search_content(top_movie, 'movie')
        if search_results:
            top_content = search_results[0].get('movie')
    
    if top_content:
        tmdb_id = top_content.get('ids', {}).get('tmdb')
        if tmdb_id:
            poster_url = f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg"
            embed.set_thumbnail(url=poster_url)
    
    # Fun stats
    if total_episodes > 0 or total_movies > 0:
        avg_per_user = (total_episodes + total_movies) / max(len(most_active_users), 1)
        total_runtime_estimate = (total_episodes * 45) + (total_movies * 120)  # Rough estimates
        hours = total_runtime_estimate // 60
        
        embed.add_field(
            name="🎯 Fun Stats",
            value=f"📊 **{avg_per_user:.1f}** avg watches per active user\n"
                  f"⏱️ **~{hours:,} hours** of content consumed\n"
                  f"🗓️ **{days} days** of community activity",
            inline=False
        )
    
    embed.set_footer(text=f"📈 Trends based on {days} days of activity • Use /community for live activity")
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="progress", description="View and manage your watching progress for a show")
@app_commands.describe(show_name="Name of the show to check progress for")
@app_commands.autocomplete(show_name=show_autocomplete)
async def show_progress(interaction: discord.Interaction, show_name: str):
    """View and manage your watching progress for a show."""
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
    show_result = results[0]
    
    # Create the progress management view
    view = ShowProgressView(show_result, interaction.user.id, user['access_token'])
    embed = view.get_progress_embed()
    
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="manage", description="Advanced management for shows - seasons, episodes, progress")
@app_commands.describe(show_name="Name of the show to manage")
@app_commands.autocomplete(show_name=show_autocomplete)
async def manage_show(interaction: discord.Interaction, show_name: str):
    """Advanced management for shows including seasons and episodes."""
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
    show_result = results[0]
    show = show_result.get('show')
    
    # Create initial embed with show info
    embed = discord.Embed(
        title=f"🎭 Manage: {show['title']} ({show.get('year', 'N/A')})",
        description=show.get('overview', 'No description available'),
        color=0x9d4edd
    )
    
    embed.add_field(name="Type", value="📺 TV Show", inline=True)
    
    rating = show.get('rating', 0)
    votes = show.get('votes', 0)
    embed.add_field(name="Rating", value=f"⭐ {rating}/10\n({votes:,} votes)" if votes > 0 else f"⭐ {rating}/10", inline=True)
    
    status = show.get('status', 'N/A')
    embed.add_field(name="Status", value=f"📺 {status}", inline=True)
    
    # Add poster
    tmdb_id = show.get('ids', {}).get('tmdb')
    if tmdb_id:
        poster_url = f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg"
        embed.set_image(url=poster_url)
    
    # Create the management view
    view = ShowProgressView(show_result, interaction.user.id, user['access_token'])
    
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="continue", description="See what shows you can continue watching")
async def continue_watching(interaction: discord.Interaction):
    """See what shows you can continue watching based on your progress."""
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    # Get user's watching progress for all shows
    try:
        response = requests.get(
            f"{trakt_api.base_url}/users/me/watched/shows?extended=full",
            headers=trakt_api.get_headers(user['access_token'])
        )
        
        if response.status_code != 200:
            await interaction.followup.send("❌ Could not fetch your watching progress.")
            return
        
        watched_shows = response.json()
        
        # Find shows that are in progress (not fully watched)
        continue_options = []
        
        for watched_show in watched_shows[:10]:  # Limit to avoid too much data
            show = watched_show['show']
            show_id = str(show['ids']['trakt'])
            
            # Get detailed progress
            progress = trakt_api.get_show_progress(user['access_token'], show_id)
            if progress:
                completed = progress.get('completed', 0)
                total = progress.get('episodes', 0)
                
                # Only include shows that are partially watched
                if 0 < completed < total:
                    continue_options.append({
                        'show': show,
                        'progress': progress,
                        'completed': completed,
                        'total': total,
                        'percentage': (completed / total * 100) if total > 0 else 0
                    })
        
        if not continue_options:
            embed = discord.Embed(
                title="📺 Continue Watching",
                description="No shows in progress found. Start watching some shows or use `/progress <show>` to check specific shows!",
                color=0xff6600
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Sort by percentage to show most progressed first
        continue_options.sort(key=lambda x: x['percentage'], reverse=True)
        
        embed = discord.Embed(
            title="📺 Continue Watching",
            description=f"You have {len(continue_options)} shows in progress:",
            color=0x00ff88
        )
        
        for i, option in enumerate(continue_options[:5], 1):  # Show top 5
            show = option['show']
            completed = option['completed']
            total = option['total']
            percentage = option['percentage']
            
            progress_bar = '🟩' * int(percentage // 10) + '⬜' * (10 - int(percentage // 10))
            
            embed.add_field(
                name=f"{i}. {show['title']} ({show.get('year', 'N/A')})",
                value=f"**{completed}/{total} episodes** ({percentage:.1f}%)\n{progress_bar}",
                inline=False
            )
        
        if len(continue_options) > 5:
            embed.set_footer(text=f"...and {len(continue_options) - 5} more shows. Use /progress <show> for detailed management.")
        
        # Add poster from most progressed show
        if continue_options:
            top_show = continue_options[0]['show']
            tmdb_id = top_show.get('ids', {}).get('tmdb')
            if tmdb_id:
                poster_url = f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg"
                embed.set_thumbnail(url=poster_url)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Error in continue_watching: {e}")
        await interaction.followup.send("❌ Error fetching your watching progress. Please try again.")

@bot.tree.command(name="episode", description="Mark or unmark a specific episode as watched")
@app_commands.describe(
    show_name="Name of the show",
    season="Season number",
    episode="Episode number"
)
@app_commands.autocomplete(show_name=show_autocomplete)
async def manage_episode(interaction: discord.Interaction, show_name: str, season: int, episode: int):
    """Quick command to mark/unmark a specific episode."""
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    if season < 1 or episode < 1:
        await interaction.followup.send("❌ Season and episode numbers must be positive.")
        return
    
    # Search for the show
    results = trakt_api.search_content(show_name, 'show')
    if not results:
        await interaction.followup.send(f"❌ No shows found for '{show_name}'")
        return
    
    show_result = results[0]
    show = show_result.get('show')
    show_id = str(show['ids']['trakt'])
    
    # Get episode details
    episodes = trakt_api.get_season_episodes(show_id, season)
    if not episodes:
        await interaction.followup.send(f"❌ Could not find season {season} for this show.")
        return
    
    # Find the specific episode
    target_episode = None
    for ep in episodes:
        if ep['number'] == episode:
            target_episode = ep
            break
    
    if not target_episode:
        await interaction.followup.send(f"❌ Episode {episode} not found in season {season}.")
        return
    
    # Create episode action view
    view = EpisodeActionView(show, season, target_episode, interaction.user.id, user['access_token'])
    
    embed = discord.Embed(
        title=f"📺 {show['title']} S{season}E{episode}",
        description=f"**{target_episode.get('title', 'Episode')}**\n\n"
                   f"{target_episode.get('overview', 'No description available')}",
        color=0x0099ff
    )
    
    embed.add_field(name="Runtime", value=f"⏱️ {target_episode.get('runtime', 'N/A')} min", inline=True)
    embed.add_field(name="Rating", value=f"⭐ {target_episode.get('rating', 0)}/10", inline=True)
    
    if target_episode.get('first_aired'):
        aired = target_episode['first_aired'][:10]
        embed.add_field(name="Aired", value=f"📅 {aired}", inline=True)
    
    await interaction.followup.send(embed=embed, view=view)

if __name__ == "__main__":
    bot.run(config.DISCORD_TOKEN) 