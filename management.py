import discord
from discord import app_commands
from typing import Optional
import requests
from datetime import datetime

# Initialize these as None and set them later
bot = None
trakt_api = None
db = None

def init_management(discord_bot, api, database):
    """Initialize the management module with shared objects"""
    global bot, trakt_api, db
    bot = discord_bot
    trakt_api = api
    db = database

class ShowProgressView(discord.ui.View):
    def __init__(self, show_result, user_id, access_token):
        super().__init__(timeout=300)
        self.show_result = show_result
        self.user_id = user_id
        self.access_token = access_token
        self.show = show_result.get('show')
        self.show_id = str(self.show['ids']['trakt'])
        
    def get_progress_embed(self, progress_data=None):
        embed = discord.Embed(
            title=f"📺 {self.show['title']} - Progress",
            color=0x0099ff
        )
        
        if progress_data:
            try:
                completed = progress_data.get('completed', 0)
                total = progress_data.get('episodes', 0)
                percentage = (completed / total * 100) if total > 0 else 0
                
                embed.add_field(
                    name="📊 Overall Progress",
                    value=f"**{completed}/{total} episodes** ({percentage:.1f}%)\n"
                          f"{'🟩' * int(percentage // 10)}{'⬜' * (10 - int(percentage // 10))}",
                    inline=False
                )
                
                seasons = progress_data.get('seasons', [])
                if seasons:
                    season_text = ""
                    for season in seasons[:5]:
                        try:
                            season_num = season.get('number', 0)
                            s_completed = season.get('completed', 0)
                            s_episodes = season.get('episodes', [])
                            s_total = len(s_episodes) if isinstance(s_episodes, list) else (s_episodes if isinstance(s_episodes, int) else 0)
                            s_percentage = (s_completed / s_total * 100) if s_total > 0 else 0
                            
                            status = "✅" if s_completed == s_total else "🔄" if s_completed > 0 else "⭕"
                            season_text += f"{status} **Season {season_num}**: {s_completed}/{s_total} ({s_percentage:.0f}%)\n"
                        except:
                            continue
                    
                    if season_text:
                        embed.add_field(name="🎬 Season Progress", value=season_text, inline=False)
            except Exception as e:
                print(f"Error processing progress: {e}")
                embed.add_field(name="📊 Progress", value="❌ Error loading progress", inline=False)
        else:
            embed.add_field(name="📊 Progress", value="Loading...", inline=False)
        
        # Add poster
        try:
            tmdb_id = self.show.get('ids', {}).get('tmdb')
            if tmdb_id:
                embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
        except:
            pass
        
        return embed
    
    @discord.ui.button(label='📊 View Progress', style=discord.ButtonStyle.primary)
    async def view_progress(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your show!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            progress = trakt_api.get_show_progress(self.access_token, self.show_id)
            embed = self.get_progress_embed(progress)
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
        except Exception as e:
            await interaction.followup.send("❌ Could not load progress data.", ephemeral=True)
    
    @discord.ui.button(label='🎭 Manage Seasons', style=discord.ButtonStyle.secondary)
    async def manage_seasons(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your show!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        seasons = trakt_api.get_show_seasons(self.show_id)
        if not seasons:
            await interaction.followup.send("❌ Could not load seasons.", ephemeral=True)
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
                description=f"All episodes of **{self.show['title']}** marked as watched!",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(title="❌ Failed", description="Could not mark show", color=0xff0000)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SeasonSelectView(discord.ui.View):
    def __init__(self, show, seasons, user_id, access_token):
        super().__init__(timeout=300)
        self.show = show
        self.seasons = seasons
        self.user_id = user_id
        self.access_token = access_token
        self.show_id = str(show['ids']['trakt'])
        
        options = []
        for season in seasons:
            if season['number'] == 0:
                continue
            
            episodes = season.get('episodes', [])
            episode_count = len(episodes) if isinstance(episodes, list) else episodes
            options.append(discord.SelectOption(
                label=f"Season {season['number']}",
                description=f"{episode_count} episodes",
                value=str(season['number'])
            ))
        
        if options:
            select = discord.ui.Select(placeholder="Choose a season...", options=options[:25])
            select.callback = self.season_callback
            self.add_item(select)
    
    def get_seasons_embed(self):
        embed = discord.Embed(
            title=f"🎭 {self.show['title']} - Seasons",
            description="Select a season to manage episodes.",
            color=0x9d4edd
        )
        
        season_text = ""
        for season in self.seasons:
            if season['number'] == 0:
                continue
            
            episodes = season.get('episodes', [])
            episode_count = len(episodes) if isinstance(episodes, list) else episodes
            season_text += f"**Season {season['number']}**: {episode_count} episodes\n"
        
        embed.add_field(name="📺 Available Seasons", value=season_text, inline=False)
        return embed
    
    async def season_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your show!", ephemeral=True)
            return
        
        season_number = int(interaction.data['values'][0])
        
        selected_season = None
        for season in self.seasons:
            if season['number'] == season_number:
                selected_season = season
                break
        
        if not selected_season:
            await interaction.response.send_message("❌ Season not found.", ephemeral=True)
            return
        
        episodes = trakt_api.get_season_episodes(self.show_id, season_number)
        view = EpisodeManageView(self.show, selected_season, episodes, self.user_id, self.access_token)
        embed = view.get_episode_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class EpisodeManageView(discord.ui.View):
    def __init__(self, show, season, episodes, user_id, access_token):
        super().__init__(timeout=300)
        self.show = show
        self.season = season
        self.episodes = episodes
        self.user_id = user_id
        self.access_token = access_token
        self.show_id = str(show['ids']['trakt'])
        self.season_number = season['number']
        
        if episodes:
            options = []
            for episode in episodes[:25]:
                episode_title = episode.get('title', f'Episode {episode["number"]}')
                if len(episode_title) > 45:
                    episode_title = episode_title[:42] + "..."
                
                options.append(discord.SelectOption(
                    label=f"E{episode['number']}: {episode_title}",
                    description=f"Runtime: {episode.get('runtime', 'N/A')} min",
                    value=str(episode['number'])
                ))
            
            if options:
                select = discord.ui.Select(placeholder="Choose an episode...", options=options)
                select.callback = self.episode_callback
                self.add_item(select)
    
    def get_episode_embed(self):
        embed = discord.Embed(
            title=f"📺 {self.show['title']} - Season {self.season_number}",
            description=f"Manage episodes or mark the entire season.",
            color=0x0099ff
        )
        
        episode_text = ""
        for i, episode in enumerate(self.episodes[:10]):
            title = episode.get('title', f'Episode {episode["number"]}')
            runtime = episode.get('runtime', 'N/A')
            episode_text += f"**E{episode['number']}**: {title} ({runtime} min)\n"
        
        if len(self.episodes) > 10:
            episode_text += f"*...and {len(self.episodes) - 10} more episodes*"
        
        embed.add_field(name=f"📋 Episodes ({len(self.episodes)} total)", value=episode_text, inline=False)
        return embed
    
    async def episode_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your episode!", ephemeral=True)
            return
        
        episode_number = int(interaction.data['values'][0])
        
        selected_episode = None
        for episode in self.episodes:
            if episode['number'] == episode_number:
                selected_episode = episode
                break
        
        if not selected_episode:
            await interaction.response.send_message("❌ Episode not found.", ephemeral=True)
            return
        
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
                description=f"Season {self.season_number} of **{self.show['title']}** marked as watched!",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(title="❌ Failed", description="Could not mark season", color=0xff0000)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class EpisodeActionView(discord.ui.View):
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
                description=f"**{self.show['title']}** S{self.season_number}E{self.episode_number} marked as watched!",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(title="❌ Failed", description="Could not mark episode", color=0xff0000)
        
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
                description=f"**{self.show['title']}** S{self.season_number}E{self.episode_number} removed from watched!",
                color=0xff6600
            )
        else:
            embed = discord.Embed(title="❌ Failed", description="Could not unmark episode", color=0xff0000)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Management Commands
async def show_autocomplete_local(interaction: discord.Interaction, current: str):
    """Local autocomplete function to avoid circular imports"""
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

@bot.tree.command(name="progress", description="View and manage your watching progress for a show")
@app_commands.describe(show_name="Name of the show to check progress for")
@app_commands.autocomplete(show_name=show_autocomplete_local)
async def show_progress(interaction: discord.Interaction, show_name: str):
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    results = trakt_api.search_content(show_name, 'show')
    if not results:
        await interaction.followup.send(f"❌ No shows found for '{show_name}'")
        return
    
    show_result = results[0]
    show = show_result.get('show')
    show_id = str(show['ids']['trakt'])
    
    try:
        progress = trakt_api.get_show_progress(user['access_token'], show_id)
        view = ShowProgressView(show_result, interaction.user.id, user['access_token'])
        embed = view.get_progress_embed(progress)
        await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        print(f"Error getting progress: {e}")
        embed = discord.Embed(
            title="❌ Error Loading Progress",
            description=f"Could not load progress for **{show['title']}**.\n\n"
                       f"This might be because you haven't watched any episodes yet.",
            color=0xff0000
        )
        
        tmdb_id = show.get('ids', {}).get('tmdb')
        if tmdb_id:
            embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
        
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="manage", description="Advanced management for shows - seasons, episodes, progress")
@app_commands.describe(show_name="Name of the show to manage")
@app_commands.autocomplete(show_name=show_autocomplete_local)
async def manage_show(interaction: discord.Interaction, show_name: str):
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    results = trakt_api.search_content(show_name, 'show')
    if not results:
        await interaction.followup.send(f"❌ No shows found for '{show_name}'")
        return
    
    show_result = results[0]
    show = show_result.get('show')
    
    embed = discord.Embed(
        title=f"🎭 Manage: {show['title']} ({show.get('year', 'N/A')})",
        description=show.get('overview', 'No description available'),
        color=0x9d4edd
    )
    
    embed.add_field(name="Type", value="📺 TV Show", inline=True)
    
    rating = show.get('rating', 0)
    embed.add_field(name="Rating", value=f"⭐ {rating}/10", inline=True)
    
    status = show.get('status', 'N/A')
    embed.add_field(name="Status", value=f"📺 {status}", inline=True)
    
    tmdb_id = show.get('ids', {}).get('tmdb')
    if tmdb_id:
        embed.set_image(url=f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg")
    
    view = ShowProgressView(show_result, interaction.user.id, user['access_token'])
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="continue", description="See what shows you can continue watching")
async def continue_watching(interaction: discord.Interaction):
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    try:
        continue_options = []
        
        # Check multiple sources for shows
        collection_response = requests.get(
            f"{trakt_api.base_url}/users/me/collection/shows?extended=full",
            headers=trakt_api.get_headers(user['access_token'])
        )
        
        watched_response = requests.get(
            f"{trakt_api.base_url}/users/me/watched/shows?extended=full",
            headers=trakt_api.get_headers(user['access_token'])
        )
        
        history_response = requests.get(
            f"{trakt_api.base_url}/users/me/history/shows?limit=50",
            headers=trakt_api.get_headers(user['access_token'])
        )
        
        all_shows = set()
        
        # Collect shows from all sources
        for response in [collection_response, watched_response, history_response]:
            if response.status_code == 200:
                items = response.json()
                for item in items:
                    show = item.get('show', {})
                    if show.get('ids', {}).get('trakt'):
                        all_shows.add(str(show['ids']['trakt']))
        
        print(f"Found {len(all_shows)} unique shows to check")
        
        # Check progress for each show
        for show_id in list(all_shows)[:20]:  # Limit to avoid rate limits
            try:
                show_info = trakt_api.get_show_info(show_id)
                if not show_info:
                    continue
                
                progress = trakt_api.get_show_progress(user['access_token'], show_id)
                if progress:
                    completed = progress.get('completed', 0)
                    total_episodes = progress.get('episodes', 0)
                    
                    # Include partially watched shows
                    if completed > 0 and completed < total_episodes:
                        continue_options.append({
                            'show': show_info,
                            'completed': completed,
                            'total': total_episodes,
                            'percentage': (completed / total_episodes * 100) if total_episodes > 0 else 0
                        })
                        
            except Exception as e:
                print(f"Error checking progress for show {show_id}: {e}")
                continue
        
        if not continue_options:
            embed = discord.Embed(
                title="📺 Continue Watching",
                description=f"No shows in progress found from {len(all_shows)} shows checked.\n\n"
                           f"Try using `/progress <show>` to check specific shows.",
                color=0xff6600
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Sort by percentage
        continue_options.sort(key=lambda x: x['percentage'], reverse=True)
        
        embed = discord.Embed(
            title="📺 Continue Watching",
            description=f"Found {len(continue_options)} shows you can continue:",
            color=0x00ff88
        )
        
        for i, option in enumerate(continue_options[:8], 1):
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
        
        if len(continue_options) > 8:
            embed.set_footer(text=f"...and {len(continue_options) - 8} more shows. Use /progress <show> for management.")
        
        # Add poster from most progressed show
        if continue_options:
            top_show = continue_options[0]['show']
            tmdb_id = top_show.get('ids', {}).get('tmdb')
            if tmdb_id:
                embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Error in continue_watching: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"Error fetching your watching progress. Try again in a moment.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="episode", description="Mark or unmark a specific episode as watched")
@app_commands.describe(
    show_name="Name of the show",
    season="Season number",
    episode="Episode number"
)
@app_commands.autocomplete(show_name=show_autocomplete_local)
async def manage_episode(interaction: discord.Interaction, show_name: str, season: int, episode: int):
    await interaction.response.defer()
    
    user = db.get_user(str(interaction.user.id))
    if not user:
        await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
        return
    
    if season < 1 or episode < 1:
        await interaction.followup.send("❌ Season and episode numbers must be positive.")
        return
    
    results = trakt_api.search_content(show_name, 'show')
    if not results:
        await interaction.followup.send(f"❌ No shows found for '{show_name}'")
        return
    
    show_result = results[0]
    show = show_result.get('show')
    show_id = str(show['ids']['trakt'])
    
    episodes = trakt_api.get_season_episodes(show_id, season)
    if not episodes:
        await interaction.followup.send(f"❌ Could not find season {season} for this show.")
        return
    
    target_episode = None
    for ep in episodes:
        if ep['number'] == episode:
            target_episode = ep
            break
    
    if not target_episode:
        await interaction.followup.send(f"❌ Episode {episode} not found in season {season}.")
        return
    
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