import discord
from discord import app_commands
from datetime import datetime

# Initialize these as None and set them later
trakt_api = None
db = None

def init_views(api, database):
    """Initialize the views module with shared objects"""
    global trakt_api, db
    trakt_api = api
    db = database

class SearchView(discord.ui.View):
    def __init__(self, results, query, user_id):
        super().__init__(timeout=300)
        self.results = results
        self.query = query
        self.user_id = user_id
        self.current_page = 0
        self.items_per_page = 3
        
    def get_embed(self):
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
            runtime = content.get('runtime', 0)
            
            field_value = f"⭐ **{rating}/10**"
            if runtime:
                field_value += f" • ⏱️ **{runtime} min**"
            
            overview = content.get('overview', 'No description available')
            field_value += f"\n{overview[:120]}..." if len(overview) > 120 else f"\n{overview}"
            
            embed.add_field(
                name=f"{i}. {content['title']} ({year}) - {content_type}",
                value=field_value,
                inline=False
            )
        
        # Add poster from first result
        if page_results:
            first_content = page_results[0].get('show') or page_results[0].get('movie')
            tmdb_id = first_content.get('ids', {}).get('tmdb')
            if tmdb_id:
                embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
        
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
                value=str(i-1)
            ))
        
        if options:
            view = InfoSelectView(self.results, options, start, self.user_id)
            await interaction.response.send_message("Select an item to get more info:", view=view, ephemeral=True)

class InfoSelectView(discord.ui.View):
    def __init__(self, results, options, start_index, user_id):
        super().__init__(timeout=60)
        self.results = results
        self.start_index = start_index
        self.user_id = user_id
        
        select = discord.ui.Select(placeholder="Choose an item to get detailed info...", options=options)
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
            rating = detailed_info.get('rating', 0)
            votes = detailed_info.get('votes', 0)
            embed.add_field(name="Rating", value=f"⭐ {rating}/10\n({votes:,} votes)", inline=True)
            
            runtime = detailed_info.get('runtime', 0)
            embed.add_field(name="Runtime", value=f"⏱️ {runtime} min" if runtime else "N/A", inline=True)
            
            # Add poster
            tmdb_id = detailed_info.get('ids', {}).get('tmdb')
            if tmdb_id:
                embed.set_image(url=f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg")
            
            view = ContentActionView(result, self.user_id)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message("Failed to get detailed information.", ephemeral=True)

class ContentActionView(discord.ui.View):
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
        else:
            embed = discord.Embed(title="❌ Failed", description="Could not mark as watched", color=0xff0000)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
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
        else:
            embed = discord.Embed(title="❌ Failed", description="Could not add to watchlist", color=0xff0000)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ReminderModal(discord.ui.Modal):
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
        
        # Store reminder with enhanced data
        success = db.add_reminder(
            str(interaction.user.id), 
            self.show_id, 
            self.show_title,
            hours_before=hours,
            custom_message=self.custom_message.value
        )
        
        if success:
            embed = discord.Embed(
                title="🔔 Enhanced Reminder Set",
                description=f"**{self.show_title}**\n"
                           f"⏰ You'll be notified **{hours} hour{'s' if hours != 1 else ''}** before new episodes\n"
                           f"💬 Custom message: {self.custom_message.value or 'None'}",
                color=0x00ff00
            )
            embed.add_field(
                name="📅 How It Works",
                value="• I'll check for new episodes every 6 hours\n"
                      "• You'll get a DM when episodes are about to air\n"
                      "• Use `/reminders` to manage your notifications",
                inline=False
            )
        else:
            embed = discord.Embed(title="❌ Failed", description="Could not set reminder", color=0xff0000)
        
        await interaction.response.send_message(embed=embed, ephemeral=True) 