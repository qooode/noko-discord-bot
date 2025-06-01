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

    @bot.tree.command(name="random", description="Get random content recommendations based on your preferences")
    @app_commands.describe(
        content_type="Type of content to recommend",
        genre="Filter by specific genre",
        min_rating="Minimum rating (1-10)",
        from_watchlist="Get random item from your watchlist"
    )
    @app_commands.choices(
        content_type=[
            app_commands.Choice(name="Movies & Shows", value="all"),
            app_commands.Choice(name="Movies Only", value="movie"),
            app_commands.Choice(name="Shows Only", value="show")
        ],
        genre=[
            app_commands.Choice(name="Any Genre", value="any"),
            app_commands.Choice(name="Action", value="action"),
            app_commands.Choice(name="Comedy", value="comedy"),
            app_commands.Choice(name="Drama", value="drama"),
            app_commands.Choice(name="Horror", value="horror"),
            app_commands.Choice(name="Sci-Fi", value="science-fiction"),
            app_commands.Choice(name="Thriller", value="thriller"),
            app_commands.Choice(name="Romance", value="romance"),
            app_commands.Choice(name="Fantasy", value="fantasy"),
            app_commands.Choice(name="Crime", value="crime"),
            app_commands.Choice(name="Documentary", value="documentary"),
            app_commands.Choice(name="Animation", value="animation")
        ]
    )
    async def random_recommendation(
        interaction: discord.Interaction, 
        content_type: str = "all",
        genre: str = "any", 
        min_rating: float = 6.0,
        from_watchlist: bool = False
    ):
        await interaction.response.defer()
        
        user = db.get_user(str(interaction.user.id))
        
        try:
            if from_watchlist and user:
                # Get random from user's watchlist
                watchlist = trakt_api.get_user_watchlist(user['access_token'])
                if not watchlist:
                    embed = discord.Embed(
                        title="📋 Empty Watchlist",
                        description="Your watchlist is empty! Add some shows or movies first.",
                        color=0xff6600
                    )
                    embed.add_field(
                        name="💡 How to Add Content",
                        value="• Use `/search` to find content\n• Click **Add to Watchlist** button\n• Or use `/watchlist <show/movie name>`",
                        inline=False
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                import random
                random_item = random.choice(watchlist)
                content = random_item.get('show') or random_item.get('movie')
                content_type_result = 'show' if 'show' in random_item else 'movie'
                
                embed = discord.Embed(
                    title="🎲 Random from Your Watchlist",
                    description=f"**{content['title']}** ({content.get('year', 'N/A')})",
                    color=0x9d4edd
                )
                
                # Add description
                overview = content.get('overview', '')
                if overview:
                    embed.add_field(
                        name="📖 Synopsis", 
                        value=overview[:300] + "..." if len(overview) > 300 else overview,
                        inline=False
                    )
                
                # Add details
                rating = content.get('rating', 0)
                votes = content.get('votes', 0)
                runtime = content.get('runtime', 0)
                
                details = f"⭐ **{rating}/10**"
                if votes > 0:
                    details += f" ({votes:,} votes)"
                if runtime > 0:
                    details += f" • ⏱️ **{runtime} min**"
                
                embed.add_field(name="📊 Details", value=details, inline=True)
                
                # Add genres
                genres = content.get('genres', [])
                if genres:
                    embed.add_field(name="🏷️ Genres", value=", ".join(genres[:3]), inline=True)
                
                embed.add_field(name="🎯 Source", value="From your watchlist", inline=True)
                
            else:
                # Get popular/trending content for random selection
                if content_type == "all":
                    # Get both movies and shows
                    movies = trakt_api.get_popular_movies()[:20] if hasattr(trakt_api, 'get_popular_movies') else []
                    shows = trakt_api.get_popular_shows()[:20] if hasattr(trakt_api, 'get_popular_shows') else []
                    
                    # If API methods don't exist, use search with popular terms
                    if not movies and not shows:
                        popular_terms = ["breaking bad", "inception", "the office", "stranger things", "pulp fiction", "game of thrones", "the dark knight", "friends"]
                        import random
                        search_term = random.choice(popular_terms)
                        results = trakt_api.search_content(search_term)
                        if results:
                            content_items = [results[0]]  # Take first result
                        else:
                            await interaction.followup.send("❌ Unable to get recommendations right now. Try again later.")
                            return
                    else:
                        content_items = movies + shows
                        
                elif content_type == "movie":
                    content_items = trakt_api.get_popular_movies()[:30] if hasattr(trakt_api, 'get_popular_movies') else []
                    if not content_items:
                        # Fallback to search
                        movie_terms = ["inception", "pulp fiction", "the dark knight", "forrest gump", "the matrix"]
                        import random
                        search_term = random.choice(movie_terms)
                        results = trakt_api.search_content(search_term, 'movie')
                        content_items = results[:10] if results else []
                        
                else:  # show
                    content_items = trakt_api.get_popular_shows()[:30] if hasattr(trakt_api, 'get_popular_shows') else []
                    if not content_items:
                        # Fallback to search
                        show_terms = ["breaking bad", "the office", "stranger things", "game of thrones", "friends"]
                        import random
                        search_term = random.choice(show_terms)
                        results = trakt_api.search_content(search_term, 'show')
                        content_items = results[:10] if results else []
                
                if not content_items:
                    await interaction.followup.send("❌ No recommendations available right now. Try again later.")
                    return
                
                # Filter by rating and genre
                import random
                filtered_items = []
                
                for item in content_items:
                    content = item.get('show') or item.get('movie')
                    if not content:
                        continue
                        
                    # Check rating
                    rating = content.get('rating', 0)
                    if rating < min_rating:
                        continue
                    
                    # Check genre
                    if genre != "any":
                        content_genres = [g.lower().replace('-', ' ') for g in content.get('genres', [])]
                        genre_check = genre.lower().replace('-', ' ')
                        if genre_check not in content_genres:
                            continue
                    
                    filtered_items.append(item)
                
                if not filtered_items:
                    embed = discord.Embed(
                        title="🎲 No Matches Found",
                        description=f"No content found matching your criteria:",
                        color=0xff6600
                    )
                    embed.add_field(name="🔍 Your Filters", value=f"• **Type:** {content_type.title()}\n• **Genre:** {genre.title()}\n• **Min Rating:** {min_rating}/10", inline=False)
                    embed.add_field(name="💡 Try:", value="• Lower the minimum rating\n• Choose 'Any Genre'\n• Try 'Movies & Shows'", inline=False)
                    await interaction.followup.send(embed=embed)
                    return
                
                # Pick random item
                random_item = random.choice(filtered_items)
                content = random_item.get('show') or random_item.get('movie')
                content_type_result = 'show' if 'show' in random_item else 'movie'
                
                embed = discord.Embed(
                    title="🎲 Random Recommendation",
                    description=f"**{content['title']}** ({content.get('year', 'N/A')})",
                    color=0x00ff88
                )
                
                # Add description
                overview = content.get('overview', '')
                if overview:
                    embed.add_field(
                        name="📖 Synopsis", 
                        value=overview[:300] + "..." if len(overview) > 300 else overview,
                        inline=False
                    )
                
                # Add details
                rating = content.get('rating', 0)
                votes = content.get('votes', 0)
                runtime = content.get('runtime', 0)
                
                details = f"⭐ **{rating}/10**"
                if votes > 0:
                    details += f" ({votes:,} votes)"
                if runtime > 0:
                    details += f" • ⏱️ **{runtime} min**"
                
                embed.add_field(name="📊 Details", value=details, inline=True)
                
                # Add genres
                genres = content.get('genres', [])
                if genres:
                    embed.add_field(name="🏷️ Genres", value=", ".join(genres[:3]), inline=True)
                
                # Show applied filters
                filter_text = f"**{content_type_result.title()}**"
                if genre != "any":
                    filter_text += f" • {genre.title()}"
                if min_rating > 6.0:
                    filter_text += f" • {min_rating}+ ⭐"
                    
                embed.add_field(name="🎯 Filters Applied", value=filter_text, inline=True)
            
            # Add poster
            tmdb_id = content.get('ids', {}).get('tmdb')
            if tmdb_id:
                embed.set_image(url=f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg")
            
            # Add action buttons
            view = ContentActionView(random_item, interaction.user.id)
            
            # Add "Get Another" button
            class RandomAgainView(ContentActionView):
                def __init__(self, item, user_id):
                    super().__init__(item, user_id)
                    
                @discord.ui.button(label='🎲 Another Random', style=discord.ButtonStyle.primary, emoji='🔄')
                async def another_random(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.user_id:
                        await interaction.response.send_message("This isn't your recommendation!", ephemeral=True)
                        return
                    
                    # Re-run the random command
                    await interaction.response.send_message("🎲 Getting another recommendation...", ephemeral=True)
            
            view = RandomAgainView(random_item, interaction.user.id)
            
            embed.set_footer(text="💡 Click the buttons below to take action, or use 🎲 for another recommendation!")
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Random recommendation error: {e}")
            await interaction.followup.send(
                "❌ **Recommendation Error**\n"
                "Unable to get recommendations right now. This could be due to:\n"
                "• Trakt.tv API limitations\n"
                "• Network connectivity issues\n"
                "• Try again in a moment!"
            )

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

    @bot.tree.command(name="top", description="Browse curated lists of top-rated content")
    @app_commands.describe(
        content_type="Type of content to show",
        category="What type of top list to show", 
        genre="Filter by specific genre",
        year="Filter by specific year"
    )
    @app_commands.choices(
        content_type=[
            app_commands.Choice(name="Movies & Shows", value="all"),
            app_commands.Choice(name="Movies Only", value="movie"),
            app_commands.Choice(name="Shows Only", value="show")
        ],
        category=[
            app_commands.Choice(name="Highest Rated", value="rated"),
            app_commands.Choice(name="Most Popular", value="popular"),
            app_commands.Choice(name="Trending Now", value="trending"),
            app_commands.Choice(name="Most Watched", value="watched"),
            app_commands.Choice(name="Recently Updated", value="updated")
        ],
        genre=[
            app_commands.Choice(name="Any Genre", value="any"),
            app_commands.Choice(name="Action", value="action"),
            app_commands.Choice(name="Comedy", value="comedy"),
            app_commands.Choice(name="Drama", value="drama"),
            app_commands.Choice(name="Horror", value="horror"),
            app_commands.Choice(name="Sci-Fi", value="science-fiction"),
            app_commands.Choice(name="Thriller", value="thriller"),
            app_commands.Choice(name="Romance", value="romance"),
            app_commands.Choice(name="Fantasy", value="fantasy"),
            app_commands.Choice(name="Crime", value="crime"),
            app_commands.Choice(name="Documentary", value="documentary"),
            app_commands.Choice(name="Animation", value="animation")
        ]
    )
    async def top_content(
        interaction: discord.Interaction, 
        content_type: str = "all",
        category: str = "rated",
        genre: str = "any",
        year: int = None
    ):
        await interaction.response.defer()
        
        try:
            # Create curated lists based on category
            if category == "rated":
                category_title = "🏆 Highest Rated"
                category_desc = "Top-rated content on Trakt.tv"
                category_emoji = "⭐"
            elif category == "popular":
                category_title = "🔥 Most Popular"
                category_desc = "Currently popular content"
                category_emoji = "🔥"
            elif category == "trending":
                category_title = "📈 Trending Now"
                category_desc = "What's trending right now"
                category_emoji = "📈"
            elif category == "watched":
                category_title = "👁️ Most Watched"
                category_desc = "Most watched content this week"
                category_emoji = "👁️"
            else:  # updated
                category_title = "🆕 Recently Updated"
                category_desc = "Recently updated shows and new releases"
                category_emoji = "🆕"
            
            # Get curated content - since we don't have specific API endpoints, we'll use search with popular terms and filter
            curated_content = []
            
            if content_type == "all" or content_type == "movie":
                # Get popular movies using known high-quality titles
                if category == "rated":
                    movie_terms = ["the godfather", "pulp fiction", "the dark knight", "schindler's list", "forrest gump", "inception", "goodfellas", "the matrix", "fight club", "lord of the rings"]
                elif category == "popular":
                    movie_terms = ["oppenheimer", "barbie", "avatar", "top gun maverick", "spider-man", "batman", "marvel", "star wars", "john wick", "fast and furious"]
                elif category == "trending":
                    movie_terms = ["dune", "scream", "everything everywhere", "black panther", "thor", "minions", "lightyear", "nope", "bullet train", "dragon ball"]
                else:  # watched/updated
                    movie_terms = ["the avengers", "jurassic park", "titanic", "star wars", "harry potter", "james bond", "mission impossible", "transformers", "pirates caribbean", "indiana jones"]
                
                for term in movie_terms[:8]:  # Limit to prevent API overload
                    try:
                        results = trakt_api.search_content(term, 'movie')
                        if results:
                            movie_result = results[0]
                            if 'movie' in movie_result:
                                curated_content.append(movie_result)
                    except:
                        continue
            
            if content_type == "all" or content_type == "show":
                # Get popular shows
                if category == "rated":
                    show_terms = ["breaking bad", "the sopranos", "the wire", "better call saul", "game of thrones", "stranger things", "chernobyl", "the office", "friends", "sherlock"]
                elif category == "popular":
                    show_terms = ["house of the dragon", "the bear", "wednesday", "stranger things", "euphoria", "squid game", "the crown", "ozark", "succession", "yellowstone"]
                elif category == "trending":
                    show_terms = ["the last of us", "wednesday", "house of the dragon", "rings of power", "she-hulk", "sandman", "the boys", "umbrella academy", "stranger things", "euphoria"]
                else:  # watched/updated
                    show_terms = ["friends", "the office", "grey's anatomy", "supernatural", "criminal minds", "ncis", "big bang theory", "how i met your mother", "modern family", "parks recreation"]
                
                for term in show_terms[:8]:  # Limit to prevent API overload
                    try:
                        results = trakt_api.search_content(term, 'show')
                        if results:
                            show_result = results[0]
                            if 'show' in show_result:
                                curated_content.append(show_result)
                    except:
                        continue
            
            if not curated_content:
                embed = discord.Embed(
                    title="❌ No Content Found",
                    description="Unable to load curated content right now. Please try again later.",
                    color=0xff6600
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Filter by genre if specified
            if genre != "any":
                filtered_content = []
                for item in curated_content:
                    content = item.get('show') or item.get('movie')
                    content_id = str(content['ids']['trakt'])
                    item_type = 'show' if 'show' in item else 'movie'
                    
                    # Get detailed info to check genres
                    try:
                        if item_type == 'show':
                            detailed = trakt_api.get_show_info(content_id)
                        else:
                            detailed = trakt_api.get_movie_info(content_id)
                        
                        if detailed and detailed.get('genres'):
                            content_genres = [g.lower().replace('-', ' ') for g in detailed['genres']]
                            genre_check = genre.lower().replace('-', ' ')
                            if genre_check in content_genres:
                                filtered_content.append(item)
                    except:
                        continue
                
                curated_content = filtered_content
            
            # Filter by year if specified
            if year:
                year_filtered = []
                for item in curated_content:
                    content = item.get('show') or item.get('movie')
                    if content.get('year') == year:
                        year_filtered.append(item)
                curated_content = year_filtered
            
            if not curated_content:
                filters_text = ""
                if genre != "any":
                    filters_text += f" • {genre.title()}"
                if year:
                    filters_text += f" • {year}"
                
                embed = discord.Embed(
                    title="🎯 No Matches Found",
                    description=f"No content found for **{category_title}**{filters_text}",
                    color=0xff6600
                )
                embed.add_field(
                    name="💡 Try:",
                    value="• Different genre filter\n• Remove year filter\n• Different category\n• Movies & Shows instead of specific type",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Sort content by rating for better curation
            sorted_content = []
            for item in curated_content:
                content = item.get('show') or item.get('movie')
                rating = content.get('rating', 0)
                sorted_content.append((rating, item))
            
            sorted_content.sort(key=lambda x: x[0], reverse=True)
            curated_content = [item[1] for item in sorted_content]
            
            # Create paginated view
            class TopContentView(discord.ui.View):
                def __init__(self, content_list, user_id, category_info):
                    super().__init__(timeout=300)
                    self.content_list = content_list
                    self.user_id = user_id
                    self.current_page = 0
                    self.max_page = (len(content_list) - 1) // 5  # 5 items per page
                    self.category_info = category_info
                
                def get_embed(self):
                    start_idx = self.current_page * 5
                    end_idx = min(start_idx + 5, len(self.content_list))
                    page_content = self.content_list[start_idx:end_idx]
                    
                    # Apply filters info
                    filter_text = ""
                    if genre != "any":
                        filter_text += f" • {genre.title()}"
                    if year:
                        filter_text += f" • {year}"
                    if content_type != "all":
                        filter_text += f" • {content_type.title()}s Only"
                    
                    embed = discord.Embed(
                        title=f"{self.category_info['emoji']} {self.category_info['title']}{filter_text}",
                        description=f"{self.category_info['desc']} • Page {self.current_page + 1}/{self.max_page + 1}",
                        color=0xffd700
                    )
                    
                    for i, item in enumerate(page_content, start_idx + 1):
                        content = item.get('show') or item.get('movie')
                        content_type_display = 'Show' if 'show' in item else 'Movie'
                        
                        title = content['title']
                        year_display = content.get('year', 'N/A')
                        rating = content.get('rating', 0)
                        votes = content.get('votes', 0)
                        
                        rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                        
                        field_value = f"**{title}** ({year_display}) • {content_type_display}\n"
                        field_value += f"⭐ **{rating}/10**"
                        if votes > 0:
                            field_value += f" ({votes:,} votes)"
                        
                        # Add brief overview
                        overview = content.get('overview', '')
                        if overview:
                            field_value += f"\n{overview[:100]}..."
                        
                        embed.add_field(
                            name=f"{rank_emoji} #{i}",
                            value=field_value,
                            inline=False
                        )
                    
                    # Add thumbnail from top item
                    if page_content:
                        top_content = page_content[0].get('show') or page_content[0].get('movie')
                        tmdb_id = top_content.get('ids', {}).get('tmdb')
                        if tmdb_id:
                            embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
                    
                    embed.set_footer(text=f"💡 Use buttons to navigate • {len(self.content_list)} total items")
                    return embed
                
                @discord.ui.button(label='◀️ Previous', style=discord.ButtonStyle.secondary, disabled=True)
                async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.user_id:
                        await interaction.response.send_message("This isn't your list!", ephemeral=True)
                        return
                    
                    self.current_page -= 1
                    
                    # Update button states
                    self.previous_page.disabled = self.current_page == 0
                    self.next_page.disabled = self.current_page == self.max_page
                    
                    embed = self.get_embed()
                    await interaction.response.edit_message(embed=embed, view=self)
                
                @discord.ui.button(label='▶️ Next', style=discord.ButtonStyle.secondary)
                async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.user_id:
                        await interaction.response.send_message("This isn't your list!", ephemeral=True)
                        return
                    
                    self.current_page += 1
                    
                    # Update button states
                    self.previous_page.disabled = self.current_page == 0
                    self.next_page.disabled = self.current_page == self.max_page
                    
                    embed = self.get_embed()
                    await interaction.response.edit_message(embed=embed, view=self)
                
                @discord.ui.button(label='🎲 Random from List', style=discord.ButtonStyle.primary)
                async def random_from_list(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.user_id:
                        await interaction.response.send_message("This isn't your list!", ephemeral=True)
                        return
                    
                    import random
                    random_item = random.choice(self.content_list)
                    content = random_item.get('show') or random_item.get('movie')
                    content_type_display = 'Show' if 'show' in random_item else 'Movie'
                    
                    embed = discord.Embed(
                        title="🎲 Random Pick from Top List",
                        description=f"**{content['title']}** ({content.get('year', 'N/A')}) • {content_type_display}",
                        color=0x9d4edd
                    )
                    
                    rating = content.get('rating', 0)
                    votes = content.get('votes', 0)
                    embed.add_field(
                        name="⭐ Rating",
                        value=f"**{rating}/10**" + (f" ({votes:,} votes)" if votes > 0 else ""),
                        inline=True
                    )
                    
                    overview = content.get('overview', '')
                    if overview:
                        embed.add_field(
                            name="📖 Overview",
                            value=overview[:300] + "..." if len(overview) > 300 else overview,
                            inline=False
                        )
                    
                    tmdb_id = content.get('ids', {}).get('tmdb')
                    if tmdb_id:
                        embed.set_image(url=f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg")
                    
                    action_view = ContentActionView(random_item, interaction.user.id)
                    await interaction.response.send_message(embed=embed, view=action_view, ephemeral=True)
            
            category_info = {
                'title': category_title,
                'desc': category_desc,
                'emoji': category_emoji
            }
            
            view = TopContentView(curated_content, interaction.user.id, category_info)
            embed = view.get_embed()
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Top content error: {e}")
            await interaction.followup.send(
                "❌ **Error Loading Top Content**\n"
                "Unable to load curated lists right now. This could be due to:\n"
                "• Trakt.tv API limitations\n"
                "• Network connectivity issues\n"
                "• Try again in a moment or try different filters!"
            )

    @bot.tree.command(name="unwatch", description="Remove a show or movie from your watch history")
    @app_commands.describe(query="Show or movie name to remove from history")
    @app_commands.autocomplete(query=content_autocomplete)
    async def unwatch_content(interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        user = db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
            return
        
        try:
            # Search for the content
            results = trakt_api.search_content(query)
            if not results:
                await interaction.followup.send(f"❌ No results found for '{query}'")
                return
            
            result = results[0]
            content = result.get('show') or result.get('movie')
            content_type = 'show' if 'show' in result else 'movie'
            content_id = str(content['ids']['trakt'])
            
            # Check if it's in their history first
            history = trakt_api.get_user_history_authenticated(user['access_token'], 100)
            
            # Look for this content in their history
            found_in_history = False
            history_items = []
            
            for item in history:
                item_content = item.get('show') or item.get('movie')
                if item_content and item_content['title'].lower() == content['title'].lower():
                    found_in_history = True
                    history_items.append(item)
            
            if not found_in_history:
                embed = discord.Embed(
                    title="❓ Not Found in History",
                    description=f"**{content['title']}** doesn't appear in your recent watch history.",
                    color=0xff6600
                )
                embed.add_field(
                    name="💡 Possible Reasons",
                    value="• Not marked as watched yet\n• Too old to appear in recent history\n• Different title spelling\n• Use `/search` to find the exact title",
                    inline=False
                )
                
                tmdb_id = content.get('ids', {}).get('tmdb')
                if tmdb_id:
                    embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
                
                await interaction.followup.send(embed=embed)
                return
            
            # Create confirmation embed
            embed = discord.Embed(
                title="⚠️ Confirm Removal",
                description=f"Are you sure you want to remove **{content['title']}** from your watch history?",
                color=0xff6600
            )
            
            # Show what will be removed
            if content_type == 'movie':
                embed.add_field(
                    name="🎬 Movie",
                    value=f"**{content['title']}** ({content.get('year', 'N/A')})\n"
                          f"This will remove the movie from your watched history.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="📺 TV Show",
                    value=f"**{content['title']}** ({content.get('year', 'N/A')})\n"
                          f"⚠️ This will remove **ALL episodes** from your watched history.\n"
                          f"Found **{len(history_items)}** entries in recent history.",
                    inline=False
                )
            
            embed.add_field(
                name="⚠️ Warning",
                value="• This action cannot be undone\n• Your ratings and reviews will remain\n• The item will be removed from your watched history",
                inline=False
            )
            
            tmdb_id = content.get('ids', {}).get('tmdb')
            if tmdb_id:
                embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
            
            # Create confirmation view
            class UnwatchConfirmView(discord.ui.View):
                def __init__(self, content_data, content_type, user_id, access_token):
                    super().__init__(timeout=300)
                    self.content_data = content_data
                    self.content_type = content_type
                    self.user_id = user_id
                    self.access_token = access_token
                
                @discord.ui.button(label='✅ Yes, Remove', style=discord.ButtonStyle.danger)
                async def confirm_unwatch(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.user_id:
                        await interaction.response.send_message("This isn't your confirmation!", ephemeral=True)
                        return
                    
                    await interaction.response.defer()
                    
                    # Attempt to remove from history
                    success = trakt_api.unmark_as_watched(self.access_token, self.content_type, content_id)
                    
                    if success:
                        embed = discord.Embed(
                            title="✅ Successfully Removed",
                            description=f"**{self.content_data['title']}** has been removed from your watch history!",
                            color=0x00ff00
                        )
                        
                        if self.content_type == 'show':
                            embed.add_field(
                                name="📺 Show Removed",
                                value="All episodes have been unmarked as watched.\nYou can re-watch and track them again anytime!",
                                inline=False
                            )
                        else:
                            embed.add_field(
                                name="🎬 Movie Removed", 
                                value="Movie has been unmarked as watched.\nYou can watch and track it again anytime!",
                                inline=False
                            )
                        
                        embed.add_field(
                            name="💡 Next Steps",
                            value="• Use `/search` to find and re-track content\n• Use `/watched` to mark as watched again\n• Your ratings and lists are unaffected",
                            inline=False
                        )
                        
                        tmdb_id = self.content_data.get('ids', {}).get('tmdb')
                        if tmdb_id:
                            embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
                        
                        # Disable all buttons
                        for item in self.children:
                            item.disabled = True
                        
                        await interaction.edit_original_response(embed=embed, view=self)
                    else:
                        error_embed = discord.Embed(
                            title="❌ Removal Failed",
                            description="Failed to remove content from your watch history.",
                            color=0xff0000
                        )
                        error_embed.add_field(
                            name="💡 Possible Solutions",
                            value="• Try again in a moment\n• Check your internet connection\n• Content might already be removed\n• Use `/connect` to refresh your account",
                            inline=False
                        )
                        await interaction.edit_original_response(embed=error_embed, view=self)
                
                @discord.ui.button(label='❌ Cancel', style=discord.ButtonStyle.secondary)
                async def cancel_unwatch(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.user_id:
                        await interaction.response.send_message("This isn't your confirmation!", ephemeral=True)
                        return
                    
                    embed = discord.Embed(
                        title="✅ Cancelled",
                        description=f"**{self.content_data['title']}** remains in your watch history.",
                        color=0x0099ff
                    )
                    
                    # Disable all buttons
                    for item in self.children:
                        item.disabled = True
                    
                    await interaction.response.edit_message(embed=embed, view=self)
            
            view = UnwatchConfirmView(content, content_type, interaction.user.id, user['access_token'])
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Unwatch error: {e}")
            await interaction.followup.send(
                "❌ **Error Processing Unwatch Request**\n"
                "Unable to process your request right now. This could be due to:\n"
                "• Trakt.tv API temporarily unavailable\n"
                "• Your account connection needs refreshing\n"
                "• Network connectivity issues\n\n"
                "💡 Try again in a moment or use `/connect` to refresh your connection!"
            )

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
        await interaction.response.defer()
        
        user = db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
            return
        
        reminders = db.get_user_reminders(str(interaction.user.id))
        
        if not reminders:
            embed = discord.Embed(
                title="🔔 No Active Reminders",
                description="You don't have any episode reminders set up.",
                color=0xff6600
            )
            embed.add_field(
                name="💡 How to Add Reminders",
                value="Use `/remind <show>` to get notified when new episodes air!",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🔔 Your Active Reminders",
            description=f"You have **{len(reminders)}** active reminders:",
            color=0x0099ff
        )
        
        for reminder in reminders.values():
            hours = reminder.get('hours_before', 1)
            message = reminder.get('message', '')
            
            reminder_text = f"⏰ {hours} hour{'s' if hours != 1 else ''} before new episodes"
            if message:
                reminder_text += f"\n💬 \"{message}\""
            
            embed.add_field(
                name=f"📺 {reminder['show_name']}",
                value=reminder_text,
                inline=False
            )
        
        embed.set_footer(text="💡 Use /remind to add more or manage existing reminders")
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="calendar", description="View upcoming episodes from your watched shows")
    @app_commands.describe(
        days="Number of days to look ahead (1-30)",
        view_type="How to display the calendar"
    )
    @app_commands.choices(
        view_type=[
            app_commands.Choice(name="Compact List", value="compact"),
            app_commands.Choice(name="Detailed View", value="detailed"),
            app_commands.Choice(name="Today Only", value="today"),
            app_commands.Choice(name="This Week", value="week")
        ]
    )
    async def upcoming_calendar(interaction: discord.Interaction, days: int = 7, view_type: str = "compact"):
        await interaction.response.defer()
        
        user = db.get_user(str(interaction.user.id))
        if not user:
            embed = discord.Embed(
                title="❌ Account Not Connected",
                description="Connect your Trakt.tv account to view your calendar!",
                color=0xff0000
            )
            embed.add_field(
                name="🔗 Getting Started",
                value="1. Use `/connect` to get authorization link\n2. Follow the steps to link your account\n3. Start tracking your shows!",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Validate days parameter
        if days < 1 or days > 30:
            days = 7
        
        # Adjust days based on view type
        if view_type == "today":
            days = 1
        elif view_type == "week":
            days = 7
        
        try:
            # Get calendar data
            username = user['trakt_username']
            calendar_data = trakt_api.get_calendar(username, days)
            
            if not calendar_data:
                embed = discord.Embed(
                    title="📅 No Upcoming Episodes",
                    description=f"No episodes are scheduled to air in the next **{days} day{'s' if days != 1 else ''}**.",
                    color=0xff6600
                )
                
                if days <= 7:
                    embed.add_field(
                        name="💡 Try Looking Further",
                        value="• Use `/calendar days:14` for 2 weeks\n• Use `/calendar days:30` for a month\n• Make sure you're watching some shows!",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="🎭 Start Watching",
                        value="• Use `/search` to find shows\n• Mark shows as watched to see upcoming episodes\n• Use `/continue` to see shows you can continue",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
                return
            
            # Process calendar data by date
            from collections import defaultdict
            from datetime import datetime, timedelta
            
            episodes_by_date = defaultdict(list)
            
            for item in calendar_data:
                try:
                    episode = item.get('episode', {})
                    show = item.get('show', {})
                    
                    first_aired = episode.get('first_aired')
                    if not first_aired:
                        continue
                    
                    # Parse air date
                    try:
                        air_date = datetime.fromisoformat(first_aired.replace('Z', '+00:00')).date()
                    except:
                        air_date = datetime.strptime(first_aired[:10], '%Y-%m-%d').date()
                    
                    episodes_by_date[air_date].append({
                        'show': show,
                        'episode': episode,
                        'air_date': air_date
                    })
                    
                except Exception as e:
                    print(f"Error processing calendar item: {e}")
                    continue
            
            if not episodes_by_date:
                await interaction.followup.send("📅 No episodes found in the specified time range.")
                return
            
            # Create calendar embed based on view type
            if view_type == "compact":
                embed = discord.Embed(
                    title="📅 Upcoming Episodes Calendar",
                    description=f"Next **{days} day{'s' if days != 1 else ''}** • **{len(calendar_data)} episode{'s' if len(calendar_data) != 1 else ''}**",
                    color=0x0099ff
                )
                
                # Sort dates
                sorted_dates = sorted(episodes_by_date.keys())
                today = datetime.now().date()
                
                episode_count = 0
                for air_date in sorted_dates:
                    if episode_count >= 15:  # Limit for compact view
                        remaining = sum(len(episodes_by_date[d]) for d in sorted_dates[sorted_dates.index(air_date):])
                        embed.add_field(
                            name="📋 More Episodes",
                            value=f"...and **{remaining}** more episodes\nUse `/calendar view_type:detailed` to see all",
                            inline=False
                        )
                        break
                    
                    episodes = episodes_by_date[air_date]
                    
                    # Date formatting
                    if air_date == today:
                        date_str = "🔥 **TODAY**"
                    elif air_date == today + timedelta(days=1):
                        date_str = "⭐ **TOMORROW**"
                    elif air_date <= today + timedelta(days=7):
                        date_str = f"📅 **{air_date.strftime('%A')}**"
                    else:
                        date_str = f"📅 **{air_date.strftime('%m/%d/%Y')}**"
                    
                    episode_list = ""
                    for ep in episodes[:3]:  # Max 3 per date in compact view
                        show_title = ep['show']['title']
                        episode_info = ep['episode']
                        season = episode_info.get('season', 0)
                        number = episode_info.get('number', 0)
                        ep_title = episode_info.get('title', f'Episode {number}')
                        
                        if len(ep_title) > 30:
                            ep_title = ep_title[:27] + "..."
                        
                        episode_list += f"📺 **{show_title}** S{season}E{number}\n    ↳ *{ep_title}*\n"
                        episode_count += 1
                    
                    if len(episodes) > 3:
                        episode_list += f"    *...and {len(episodes) - 3} more*\n"
                    
                    embed.add_field(name=date_str, value=episode_list, inline=False)
                
            elif view_type == "detailed":
                embed = discord.Embed(
                    title="📅 Detailed Episode Calendar",
                    description=f"Next **{days} day{'s' if days != 1 else ''}** • **{len(calendar_data)} episode{'s' if len(calendar_data) != 1 else ''}**",
                    color=0x0099ff
                )
                
                sorted_dates = sorted(episodes_by_date.keys())
                today = datetime.now().date()
                
                for air_date in sorted_dates:
                    episodes = episodes_by_date[air_date]
                    
                    # Date formatting
                    if air_date == today:
                        date_str = "🔥 TODAY"
                    elif air_date == today + timedelta(days=1):
                        date_str = "⭐ TOMORROW"
                    else:
                        date_str = air_date.strftime('%A, %B %d, %Y')
                    
                    for ep in episodes:
                        show_title = ep['show']['title']
                        episode_info = ep['episode']
                        season = episode_info.get('season', 0)
                        number = episode_info.get('number', 0)
                        ep_title = episode_info.get('title', f'Episode {number}')
                        runtime = episode_info.get('runtime', 0)
                        rating = episode_info.get('rating', 0)
                        
                        field_value = f"**S{season}E{number}**: {ep_title}\n"
                        if runtime > 0:
                            field_value += f"⏱️ {runtime} min"
                        if rating > 0:
                            field_value += f" • ⭐ {rating}/10"
                        field_value += f"\n📅 {date_str}"
                        
                        embed.add_field(
                            name=f"📺 {show_title}",
                            value=field_value,
                            inline=True
                        )
                        
                        if len(embed.fields) >= 24:  # Discord limit
                            break
                    
                    if len(embed.fields) >= 24:
                        embed.add_field(
                            name="📋 View Limit Reached",
                            value="Use compact view or reduce days to see more",
                            inline=False
                        )
                        break
                        
            elif view_type == "today":
                today = datetime.now().date()
                today_episodes = episodes_by_date.get(today, [])
                
                if not today_episodes:
                    embed = discord.Embed(
                        title="📅 Today's Episodes",
                        description="No episodes airing today! 🎉",
                        color=0xff6600
                    )
                    
                    # Check tomorrow
                    tomorrow = today + timedelta(days=1)
                    tomorrow_episodes = episodes_by_date.get(tomorrow, [])
                    if tomorrow_episodes:
                        embed.add_field(
                            name="⭐ Tomorrow",
                            value=f"**{len(tomorrow_episodes)} episode{'s' if len(tomorrow_episodes) != 1 else ''}** airing tomorrow",
                            inline=False
                        )
                else:
                    embed = discord.Embed(
                        title="🔥 Today's Episodes",
                        description=f"**{len(today_episodes)} episode{'s' if len(today_episodes) != 1 else ''}** airing today!",
                        color=0xff6600
                    )
                    
                    for ep in today_episodes:
                        show_title = ep['show']['title']
                        episode_info = ep['episode']
                        season = episode_info.get('season', 0)
                        number = episode_info.get('number', 0)
                        ep_title = episode_info.get('title', f'Episode {number}')
                        runtime = episode_info.get('runtime', 0)
                        
                        field_value = f"**S{season}E{number}**: {ep_title}\n"
                        if runtime > 0:
                            field_value += f"⏱️ {runtime} min"
                        
                        embed.add_field(
                            name=f"📺 {show_title}",
                            value=field_value,
                            inline=True
                        )
            
            # Add poster from most recent show
            if calendar_data:
                try:
                    recent_show = calendar_data[0].get('show', {})
                    tmdb_id = recent_show.get('ids', {}).get('tmdb')
                    if tmdb_id:
                        embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
                except:
                    pass
            
            # Footer with helpful tips
            footer_text = f"💡 Use /remind to get notified • {len(calendar_data)} total episodes"
            embed.set_footer(text=footer_text)
            
            # Create interactive view for calendar navigation
            class CalendarView(discord.ui.View):
                def __init__(self, user_id, current_days, current_view):
                    super().__init__(timeout=300)
                    self.user_id = user_id
                    self.current_days = current_days
                    self.current_view = current_view
                
                @discord.ui.button(label='📅 Today Only', style=discord.ButtonStyle.secondary)
                async def today_view(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.user_id:
                        await interaction.response.send_message("This isn't your calendar!", ephemeral=True)
                        return
                    
                    await interaction.response.send_message("📅 Loading today's episodes...", ephemeral=True)
                
                @discord.ui.button(label='📊 Compact', style=discord.ButtonStyle.primary)
                async def compact_view(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.user_id:
                        await interaction.response.send_message("This isn't your calendar!", ephemeral=True)
                        return
                    
                    await interaction.response.send_message("📊 Switching to compact view...", ephemeral=True)
                
                @discord.ui.button(label='📋 Detailed', style=discord.ButtonStyle.secondary)
                async def detailed_view(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.user_id:
                        await interaction.response.send_message("This isn't your calendar!", ephemeral=True)
                        return
                    
                    await interaction.response.send_message("📋 Switching to detailed view...", ephemeral=True)
            
            view = CalendarView(interaction.user.id, days, view_type)
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Calendar error: {e}")
            await interaction.followup.send(
                "❌ **Calendar Error**\n"
                "Unable to load your episode calendar. This could be due to:\n"
                "• Trakt.tv API temporarily unavailable\n"
                "• Your account needs to be reconnected\n"
                "• Network connectivity issues\n\n"
                "💡 Try again in a moment or use `/connect` to refresh your connection!"
            )

def register_help_commands():
    """Register help and documentation commands"""
    
    @bot.tree.command(name="help", description="Show all available commands and how to use them")
    async def help_command(interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"🤖 {config.BOT_NAME} - Command Guide",
            description="**Advanced Discord Trakt.tv Bot** with interactive features and rich visuals!",
            color=0x0099ff
        )
        
        # Account Management
        embed.add_field(
            name="🔐 **Account Management**",
            value="• `/connect` - Link your Trakt.tv account\n"
                  "• `/authorize <code>` - Complete authorization\n"
                  "• `/public` / `/private` - Control profile visibility\n"
                  "• `/profile [user]` - View detailed user profiles",
            inline=False
        )
        
        # Content Discovery
        embed.add_field(
            name="🔍 **Content Discovery**",
            value="• `/search <query>` - Interactive search with buttons\n"
                  "• `/random` - Smart recommendations with filters\n"
                  "• `/info <show/movie>` - Detailed content information\n"
                  "• `/calendar` - Upcoming episodes calendar\n"
                  "• `/top` - Curated lists of top-rated content",
            inline=False
        )
        
        # Content Management
        embed.add_field(
            name="🎬 **Content Management**",
            value="• `/watched <show/movie>` - Mark as watched\n"
                  "• `/unwatch <show/movie>` - Remove from watch history\n"
                  "• `/watchlist <show/movie>` - Add to watchlist\n"
                  "• `/progress <show>` - Visual progress tracking\n"
                  "• `/manage <show>` - Advanced show management\n"
                  "• `/continue` - Find shows to continue\n"
                  "• `/episode <show> <season> <episode>` - Direct episode control",
            inline=False
        )
        
        # Reminders & Notifications
        embed.add_field(
            name="🔔 **Reminders**",
            value="• `/remind <show>` - Set custom episode reminders\n"
                  "• `/reminders` - List all active reminders",
            inline=False
        )
        
        # Social Features
        embed.add_field(
            name="👥 **Social & Community**",
            value="• `/watching [user]` - Current watching activity\n"
                  "• `/last [user]` - Recent watches\n"
                  "• `/stats` - Your Trakt.tv statistics\n"
                  "• `/community` - Live community activity\n"
                  "• `/trends` - Community trends & analytics\n"
                  "• `/compare <user1> [user2]` - Compare watching habits\n"
                  "• `/leaderboard` - Most active watchers",
            inline=False
        )
        
        # Arena System
        embed.add_field(
            name="🎬 **Arena - Movie Challenges**",
            value="• `/arena` - Join the movie challenge arena\n"
                  "• `/arena-status` - Check your progress\n"
                  "• `/arena-complete` - Mark challenge complete\n"
                  "• `/arena-teams` - View team standings\n"
                  "• `/arena-leave` - Leave arena",
            inline=False
        )
        
        # Getting Started
        embed.add_field(
            name="🚀 **Getting Started**",
            value="1. **Connect:** Use `/connect` to link your Trakt.tv account\n"
                  "2. **Discover:** Try `/search` or `/random` to find content\n"
                  "3. **Track:** Use `/watched` or `/watchlist` to track content\n"
                  "4. **Social:** Use `/public` to join the community\n"
                  "5. **Explore:** Check `/calendar`, `/profile`, and more!",
            inline=False
        )
        
        embed.add_field(
            name="✨ **Interactive Features**",
            value="🔘 **Buttons & Menus** - Click buttons for quick actions\n"
                  "🔍 **Smart Autocomplete** - Commands suggest as you type\n"
                  "🖼️ **Rich Visuals** - Posters, ratings, and detailed info\n"
                  "📱 **Mobile Optimized** - Works great on phone and desktop",
            inline=False
        )
        
        embed.set_footer(text="💡 Most commands have autocomplete - just start typing! | Right-click messages for quick info")
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