import discord
from discord import app_commands
from typing import Optional
from datetime import datetime

# Initialize these as None and set them later
bot = None
trakt_api = None
db = None

def init_social(discord_bot, api, database):
    """Initialize the social module with shared objects"""
    global bot, trakt_api, db
    bot = discord_bot
    trakt_api = api
    db = database
    
    # Register all social commands
    register_social_commands()

def register_social_commands():
    """Register social and community commands"""
    
    @bot.tree.command(name="watching", description="See what you or another user is currently watching")
    @app_commands.describe(user="User to check (leave empty for yourself)")
    async def get_watching(interaction: discord.Interaction, user: Optional[discord.Member] = None):
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
        
        # Add poster
        tmdb_id = content.get('ids', {}).get('tmdb')
        if tmdb_id:
            embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
        
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="last", description="See what you or another user watched recently")
    @app_commands.describe(
        user="User to check (leave empty for yourself)",
        count="Number of recent items to show (1-10)"
    )
    async def get_last_watched(interaction: discord.Interaction, user: Optional[discord.Member] = None, count: int = 5):
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
            
            field_value = f"📅 **{watched_at.strftime('%m/%d/%Y at %I:%M %p')}**\n"
            
            rating = content.get('rating', 0)
            if rating > 0:
                field_value += f"⭐ {rating}/10"
            
            runtime = content.get('runtime', 0)
            if runtime > 0:
                field_value += f" • ⏱️ {runtime} min"
            
            # Add brief overview for first few items
            if i < 3:
                overview = content.get('overview', '')
                if overview:
                    field_value += f"\n{overview[:100]}..." if len(overview) > 100 else f"\n{overview}"
            
            embed.add_field(name=title, value=field_value, inline=False)
        
        # Add poster from most recent item
        if history:
            recent_content = history[0].get('show') or history[0].get('movie')
            tmdb_id = recent_content.get('ids', {}).get('tmdb')
            if tmdb_id:
                embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
        
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="stats", description="View your Trakt.tv statistics")
    async def view_stats(interaction: discord.Interaction):
        await interaction.response.defer()
        
        user = db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
            return
        
        profile = trakt_api.get_user_profile(user['access_token'])
        if not profile:
            await interaction.followup.send("❌ Failed to get your profile information.")
            return
        
        history = trakt_api.get_user_history(user['trakt_username'], 50)
        reminders = db.get_user_reminders(str(interaction.user.id))
        
        embed = discord.Embed(
            title=f"📊 Stats for {profile['username']}",
            color=0x0099ff
        )
        
        embed.add_field(name="👤 Username", value=profile['username'], inline=True)
        embed.add_field(name="📅 Member Since", value=profile.get('joined_at', 'N/A')[:10], inline=True)
        embed.add_field(name="🔔 Active Reminders", value=str(len(reminders)), inline=True)
        
        if history:
            recent_shows = len([h for h in history if 'show' in h])
            recent_movies = len([h for h in history if 'movie' in h])
            embed.add_field(name="📺 Recent Shows Watched", value=str(recent_shows), inline=True)
            embed.add_field(name="🎬 Recent Movies Watched", value=str(recent_movies), inline=True)
            
            last_watched = history[0] if history else None
            if last_watched:
                content = last_watched.get('show') or last_watched.get('movie')
                last_date = datetime.fromisoformat(last_watched['watched_at'].replace('Z', '+00:00'))
                embed.add_field(
                    name="🕐 Last Watched", 
                    value=f"{content['title']}\n{last_date.strftime('%m/%d/%Y')}", 
                    inline=True
                )
        
        embed.set_footer(text="Stats based on recent activity")
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="profile", description="View detailed profile for yourself or another user")
    @app_commands.describe(user="User to view profile for (leave empty for yourself)")
    async def view_profile(interaction: discord.Interaction, user: Optional[discord.Member] = None):
        await interaction.response.defer()
        
        if user:
            # Viewing another user's profile
            target_user = db.get_user(str(user.id))
            if not target_user:
                embed = discord.Embed(
                    title="❌ Account Not Connected", 
                    description=f"**{user.display_name}** hasn't connected their Trakt.tv account yet.",
                    color=0xff0000
                )
                embed.add_field(
                    name="💡 How to Connect",
                    value="Use `/connect` to link your Trakt.tv account and join the community!",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
                
            if not target_user.get('is_public', False):
                embed = discord.Embed(
                    title="🔒 Private Profile",
                    description=f"**{user.display_name}**'s profile is set to private.",
                    color=0xff6600
                )
                embed.add_field(
                    name="👀 Want to share?", 
                    value="Use `/public` to make your profile visible to others!",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
                
            username = target_user['trakt_username']
            discord_user = user
            profile_type = "Public Profile"
        else:
            # Viewing own profile
            current_user = db.get_user(str(interaction.user.id))
            if not current_user:
                embed = discord.Embed(
                    title="❌ Account Not Connected",
                    description="Connect your Trakt.tv account to view your profile!",
                    color=0xff0000
                )
                embed.add_field(
                    name="🔗 Getting Started",
                    value="1. Use `/connect` to get authorization link\n2. Follow the steps to link your account\n3. Start tracking your watches!",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
                
            username = current_user['trakt_username']
            discord_user = interaction.user
            privacy_status = "🔒 Private" if not current_user.get('is_public', False) else "👁️ Public"
            profile_type = f"Your Profile ({privacy_status})"

        # Get comprehensive profile data
        try:
            # Get profile info
            profile = trakt_api.get_user_profile(username if user else current_user['access_token'])
            if not profile:
                await interaction.followup.send("❌ Failed to load profile data. Please try again.")
                return

            # Get recent activity
            history = trakt_api.get_user_history(username, 10)
            
            # Get current watching
            watching = trakt_api.get_watching_now(username)
            
            # Get reminders (only for own profile)
            reminders = []
            if not user:
                reminders = db.get_user_reminders(str(interaction.user.id))

            # Create rich profile embed
            embed = discord.Embed(
                title=f"👤 {profile['username']}",
                description=f"**{profile_type}**",
                color=0x0099ff
            )

            # Set Discord user avatar as thumbnail
            if discord_user.avatar:
                embed.set_thumbnail(url=discord_user.avatar.url)

            # Basic info section
            joined_date = profile.get('joined_at', '')[:10] if profile.get('joined_at') else 'Unknown'
            embed.add_field(
                name="📋 Basic Info",
                value=f"**Trakt Username:** {profile['username']}\n"
                      f"**Discord:** {discord_user.mention}\n"  
                      f"**Member Since:** {joined_date}",
                inline=False
            )

            # Activity stats
            if history:
                shows_count = len([h for h in history if 'show' in h])
                movies_count = len([h for h in history if 'movie' in h])
                
                # Calculate watch streak
                watch_dates = []
                for item in history:
                    try:
                        watch_date = datetime.fromisoformat(item['watched_at'].replace('Z', '+00:00')).date()
                        if watch_date not in watch_dates:
                            watch_dates.append(watch_date)
                    except:
                        continue
                
                watch_dates.sort(reverse=True)
                current_streak = 0
                if watch_dates:
                    current_date = datetime.now().date()
                    for i, date in enumerate(watch_dates):
                        if (current_date - date).days == i:
                            current_streak += 1
                        else:
                            break

                embed.add_field(
                    name="📊 Recent Activity (Last 10)",
                    value=f"📺 **{shows_count}** episodes\n"
                          f"🎬 **{movies_count}** movies\n"
                          f"🔥 **{current_streak}** day streak",
                    inline=True
                )

            # Current status
            status_text = ""
            if watching:
                content = watching.get('show') or watching.get('movie')
                if 'episode' in watching:
                    episode = watching['episode']
                    status_text = f"📺 Watching **{content['title']}**\nS{episode['season']}E{episode['number']}"
                else:
                    status_text = f"🎬 Watching **{content['title']}**"
            else:
                status_text = "💤 Not currently watching"

            # Add reminders info for own profile
            if not user and reminders:
                status_text += f"\n🔔 **{len(reminders)}** active reminders"

            embed.add_field(name="🎯 Current Status", value=status_text, inline=True)

            # Recent watches (last 3)
            if history:
                recent_text = ""
                for item in history[:3]:
                    content = item.get('show') or item.get('movie')
                    watch_date = datetime.fromisoformat(item['watched_at'].replace('Z', '+00:00'))
                    
                    if 'episode' in item:
                        episode = item['episode']
                        recent_text += f"📺 **{content['title']}** S{episode['season']}E{episode['number']}\n"
                    else:
                        recent_text += f"🎬 **{content['title']}**\n"
                    
                    recent_text += f"    ↳ {watch_date.strftime('%m/%d/%Y at %I:%M %p')}\n"

                embed.add_field(name="🕒 Recent Watches", value=recent_text, inline=False)

            # Footer with helpful info
            if not user:
                footer_text = f"Use /public or /private to change visibility • {len(history)} recent items shown"
            else:
                footer_text = f"Showing {username}'s public profile • {len(history)} recent items"
            
            embed.set_footer(text=footer_text)

            # Add poster from most recent watch
            if history:
                recent_content = history[0].get('show') or history[0].get('movie')
                tmdb_id = recent_content.get('ids', {}).get('tmdb')
                if tmdb_id:
                    embed.set_image(url=f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Profile error: {e}")
            await interaction.followup.send("❌ **Error Loading Profile**\nThere was an issue fetching profile data. Please try again in a moment.")

    @bot.tree.command(name="community", description="See what the community is watching right now")
    async def community_watching(interaction: discord.Interaction):
        await interaction.response.defer()
        
        public_users = db.get_public_users()
        user_stats = db.get_user_count()
        
        if not public_users:
            embed = discord.Embed(
                title="👥 Community Watch",
                description="No public profiles available. Use `/public` to join the community!",
                color=0xff6600
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🌍 Community Watch - Live Activity",
            description=f"Real-time activity from {len(public_users)} public members",
            color=0x00ff88
        )
        
        currently_watching = []
        trending_shows = {}
        trending_movies = {}
        active_users = []
        
        for user in public_users:
            try:
                watching = trakt_api.get_watching_now(user['trakt_username'])
                if watching:
                    currently_watching.append({'user': user, 'watching': watching})
                    
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
                continue
        
        embed.add_field(
            name="📊 Community Stats",
            value=f"👥 **{user_stats['total']} total** • **{user_stats['public']} public** • **{len(active_users)} active now**",
            inline=False
        )
        
        # Show trending content
        if trending_shows or trending_movies:
            trending_text = ""
            
            if trending_shows:
                top_shows = sorted(trending_shows.items(), key=lambda x: x[1], reverse=True)[:3]
                trending_text += "📺 **Trending Shows:**\n"
                for show, count in top_shows:
                    trending_text += f"• **{show}** ({count} watching)\n"
            
            if trending_movies:
                top_movies = sorted(trending_movies.items(), key=lambda x: x[1], reverse=True)[:3]
                trending_text += "\n🎬 **Trending Movies:**\n"
                for movie, count in top_movies:
                    trending_text += f"• **{movie}** ({count} watching)\n"
            
            embed.add_field(name="🔥 What's Hot Right Now", value=trending_text, inline=False)
        
        # Show live activity
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
        
        # Add poster from most popular content
        if trending_shows:
            top_show = max(trending_shows.items(), key=lambda x: x[1])[0]
            search_results = trakt_api.search_content(top_show, 'show')
            if search_results:
                content = search_results[0].get('show')
                tmdb_id = content.get('ids', {}).get('tmdb')
                if tmdb_id:
                    embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
        elif trending_movies:
            top_movie = max(trending_movies.items(), key=lambda x: x[1])[0]
            search_results = trakt_api.search_content(top_movie, 'movie')
            if search_results:
                content = search_results[0].get('movie')
                tmdb_id = content.get('ids', {}).get('tmdb')
                if tmdb_id:
                    embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
        
        embed.set_footer(text="🔄 Live data • Use /public to join the community watch!")
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="trends", description="See what the community has been watching this week")
    @app_commands.describe(days="Number of days to look back (1-14)")
    async def community_trends(interaction: discord.Interaction, days: int = 7):
        await interaction.response.defer()
        
        if days < 1 or days > 14:
            days = 7
        
        public_users = db.get_public_users()
        
        if not public_users:
            embed = discord.Embed(
                title="📈 Community Trends",
                description="No public profiles available. Use `/public` to join the community!",
                color=0xff6600
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"📈 Community Trends - Past {days} Days",
            description=f"Aggregated activity from {len(public_users)} public members",
            color=0x9d4edd
        )
        
        all_shows = {}
        all_movies = {}
        total_episodes = 0
        total_movies = 0
        most_active_users = {}
        
        for user in public_users:
            try:
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
            
            embed.add_field(name="📺 Trending Shows", value=shows_text, inline=True)
        
        # Top trending movies
        if all_movies:
            top_movies = sorted(all_movies.items(), key=lambda x: x[1], reverse=True)[:5]
            movies_text = ""
            for i, (movie, count) in enumerate(top_movies, 1):
                movies_text += f"{i}. **{movie}** • {count} watches\n"
            
            embed.add_field(name="🎬 Trending Movies", value=movies_text, inline=True)
        
        # Most active users
        if most_active_users:
            top_users = sorted(most_active_users.items(), key=lambda x: x[1], reverse=True)[:5]
            users_text = ""
            for i, (username, activity) in enumerate(top_users, 1):
                users_text += f"{i}. **{username}** • {activity} watches\n"
            
            embed.add_field(name="🔥 Most Active Members", value=users_text, inline=True)
        
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
                embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
        
        # Fun stats
        if total_episodes > 0 or total_movies > 0:
            avg_per_user = (total_episodes + total_movies) / max(len(most_active_users), 1)
            total_runtime_estimate = (total_episodes * 45) + (total_movies * 120)
            hours = total_runtime_estimate // 60
            
            embed.add_field(
                name="🎯 Fun Stats",
                value=f"📊 **{avg_per_user:.1f}** avg watches per active user\n"
                      f"⏱️ **~{hours:,} hours** of content consumed\n"
                      f"🗓️ **{days} days** of community activity",
                inline=False
            )
        
        embed.set_footer(text=f"📈 Trends based on {days} days of activity")
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="leaderboard", description="See the most active community watchers")
    @app_commands.describe(
        timeframe="Time period for leaderboard (week/month/all)",
        category="What to rank by (total/episodes/movies)"
    )
    @app_commands.choices(
        timeframe=[
            app_commands.Choice(name="This Week", value="week"),
            app_commands.Choice(name="This Month", value="month"), 
            app_commands.Choice(name="All Time", value="all")
        ],
        category=[
            app_commands.Choice(name="Total Watches", value="total"),
            app_commands.Choice(name="Episodes Only", value="episodes"),
            app_commands.Choice(name="Movies Only", value="movies")
        ]
    )
    async def community_leaderboard(interaction: discord.Interaction, timeframe: str = "week", category: str = "total"):
        await interaction.response.defer()
        
        public_users = db.get_public_users()
        
        if not public_users:
            embed = discord.Embed(
                title="🏆 Community Leaderboard",
                description="No public profiles available. Use `/public` to join the community!",
                color=0xff6600
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Set timeframe parameters
        if timeframe == "week":
            days_back = 7
            timeframe_title = "This Week"
            emoji = "📅"
        elif timeframe == "month":
            days_back = 30
            timeframe_title = "This Month"
            emoji = "🗓️"
        else:  # all time
            days_back = 365 * 10  # 10 years should cover "all time"
            timeframe_title = "All Time"
            emoji = "🏆"
        
        # Category settings
        if category == "episodes":
            category_title = "Episodes Watched"
            category_emoji = "📺"
        elif category == "movies":
            category_title = "Movies Watched"
            category_emoji = "🎬"
        else:  # total
            category_title = "Total Watches"
            category_emoji = "🎯"
        
        embed = discord.Embed(
            title=f"🏆 {category_title} Leaderboard - {timeframe_title}",
            description=f"Top community watchers from {len(public_users)} public members",
            color=0xffd700
        )
        
        user_stats = {}
        total_community_episodes = 0
        total_community_movies = 0
        
        for user in public_users:
            try:
                history = trakt_api.get_user_history(user['trakt_username'], 100)
                
                episodes_count = 0
                movies_count = 0
                
                for item in history:
                    watched_date = datetime.fromisoformat(item['watched_at'].replace('Z', '+00:00'))
                    days_ago = (datetime.now().replace(tzinfo=watched_date.tzinfo) - watched_date).days
                    
                    if days_ago <= days_back:
                        if 'show' in item:
                            episodes_count += 1
                            total_community_episodes += 1
                        elif 'movie' in item:
                            movies_count += 1
                            total_community_movies += 1
                
                # Calculate the score based on category
                if category == "episodes":
                    score = episodes_count
                elif category == "movies":
                    score = movies_count
                else:  # total
                    score = episodes_count + movies_count
                
                if score > 0:
                    user_stats[user['trakt_username']] = {
                        'score': score,
                        'episodes': episodes_count,
                        'movies': movies_count,
                        'total': episodes_count + movies_count
                    }
                    
            except:
                continue
        
        if not user_stats:
            embed.add_field(
                name="😴 No Activity",
                value=f"No community activity found for {timeframe_title.lower()}.",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Sort users by score
        top_users = sorted(user_stats.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
        
        # Create leaderboard text
        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (username, stats) in enumerate(top_users, 1):
            if i <= 3:
                rank_emoji = medals[i-1]
            elif i <= 5:
                rank_emoji = "🏅"
            else:
                rank_emoji = f"{i}."
            
            score = stats['score']
            episodes = stats['episodes'] 
            movies = stats['movies']
            
            if category == "total":
                detail = f"({episodes}📺 + {movies}🎬)"
            elif category == "episodes":
                detail = f"episodes"
            else:  # movies
                detail = f"movies"
            
            leaderboard_text += f"{rank_emoji} **{username}** • {score} {detail}\n"
        
        embed.add_field(
            name=f"{category_emoji} Top {len(top_users)} Watchers",
            value=leaderboard_text,
            inline=False
        )
        
        # Community overview stats
        total_active = len(user_stats)
        total_watches = total_community_episodes + total_community_movies
        avg_watches = total_watches / max(total_active, 1)
        
        stats_text = f"👥 **{total_active}** active members\n"
        stats_text += f"📺 **{total_community_episodes}** episodes watched\n"
        stats_text += f"🎬 **{total_community_movies}** movies watched\n"
        stats_text += f"📊 **{avg_watches:.1f}** avg per active user"
        
        embed.add_field(
            name=f"📈 Community Stats ({timeframe_title})",
            value=stats_text,
            inline=False
        )
        
        # Add achievement highlights for top performer
        if top_users:
            top_performer = top_users[0]
            top_username = top_performer[0]
            top_stats = top_performer[1]
            
            # Calculate some fun stats
            if timeframe == "week":
                daily_avg = top_stats['total'] / 7
                achievement_text = f"🔥 **{top_username}** is dominating with {daily_avg:.1f} watches per day!"
            elif timeframe == "month": 
                daily_avg = top_stats['total'] / 30
                achievement_text = f"🔥 **{top_username}** is on fire with {daily_avg:.1f} watches per day!"
            else:  # all time
                achievement_text = f"🔥 **{top_username}** is the ultimate community champion!"
            
            embed.add_field(
                name="🏆 Top Performer",
                value=achievement_text,
                inline=False
            )
        
        # Add thumbnail from a popular show/movie if available
        if timeframe != "all":
            # Try to get recent popular content for thumbnail
            try:
                sample_user = public_users[0]
                recent_history = trakt_api.get_user_history(sample_user['trakt_username'], 5)
                if recent_history:
                    recent_item = recent_history[0]
                    content = recent_item.get('show') or recent_item.get('movie')
                    if content:
                        tmdb_id = content.get('ids', {}).get('tmdb')
                        if tmdb_id:
                            embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
            except:
                pass
        
        embed.set_footer(text=f"🏆 {emoji} {timeframe_title} leaderboard • Use /public to compete!")
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="compare", description="Compare watching habits between two users")
    @app_commands.describe(
        user1="First user to compare",
        user2="Second user to compare (leave empty to compare with yourself)"
    )
    async def compare_users(interaction: discord.Interaction, user1: discord.Member, user2: Optional[discord.Member] = None):
        await interaction.response.defer()
        
        # If user2 is not specified, compare user1 with the command author
        if user2 is None:
            current_user = db.get_user(str(interaction.user.id))
            if not current_user:
                await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
                return
            user2 = interaction.user
            user2_data = current_user
        else:
            user2_data = db.get_user(str(user2.id))
            if not user2_data:
                await interaction.followup.send(f"❌ {user2.display_name} hasn't connected their Trakt.tv account.")
                return
        
        # Get first user data
        user1_data = db.get_user(str(user1.id))
        if not user1_data:
            await interaction.followup.send(f"❌ {user1.display_name} hasn't connected their Trakt.tv account.")
            return
        
        # Check privacy settings
        if not user1_data.get('is_public', False):
            await interaction.followup.send(f"❌ {user1.display_name}'s profile is private.")
            return
        
        if not user2_data.get('is_public', False) and user2.id != interaction.user.id:
            await interaction.followup.send(f"❌ {user2.display_name}'s profile is private.")
            return
        
        # Prevent comparing same user
        if user1.id == user2.id:
            await interaction.followup.send("❌ Can't compare a user with themselves! Try comparing with someone else.")
            return
        
        user1_username = user1_data['trakt_username']
        user2_username = user2_data['trakt_username']
        
        try:
            # Get user histories
            user1_history = trakt_api.get_user_history(user1_username, 100)
            user2_history = trakt_api.get_user_history(user2_username, 100)
            
            if not user1_history or not user2_history:
                await interaction.followup.send("❌ Not enough data to compare users.")
                return
            
            embed = discord.Embed(
                title=f"🆚 {user1_username} vs {user2_username}",
                description="Detailed taste and compatibility comparison",
                color=0xe74c3c
            )
            
            # Calculate basic stats
            user1_shows = [h for h in user1_history if 'show' in h]
            user1_movies = [h for h in user1_history if 'movie' in h]
            user2_shows = [h for h in user2_history if 'show' in h]
            user2_movies = [h for h in user2_history if 'movie' in h]
            
            # Basic stats comparison
            stats_text = f"**{user1_username}:**\n"
            stats_text += f"📺 {len(user1_shows)} episodes • 🎬 {len(user1_movies)} movies\n\n"
            stats_text += f"**{user2_username}:**\n"
            stats_text += f"📺 {len(user2_shows)} episodes • 🎬 {len(user2_movies)} movies"
            
            embed.add_field(
                name="📊 Recent Activity Comparison",
                value=stats_text,
                inline=False
            )
            
            # Find shared content
            user1_content = set()
            user2_content = set()
            
            for item in user1_history:
                content = item.get('show') or item.get('movie')
                user1_content.add(content['title'])
            
            for item in user2_history:
                content = item.get('show') or item.get('movie')
                user2_content.add(content['title'])
            
            shared_content = user1_content.intersection(user2_content)
            total_unique = len(user1_content.union(user2_content))
            
            # Calculate compatibility score
            if total_unique > 0:
                compatibility_score = (len(shared_content) / total_unique) * 100
            else:
                compatibility_score = 0
            
            # Compatibility visualization
            compatibility_bars = "█" * int(compatibility_score / 10) + "░" * (10 - int(compatibility_score / 10))
            compatibility_text = f"**{compatibility_score:.1f}%** {compatibility_bars}\n"
            
            if compatibility_score >= 80:
                compatibility_text += "🔥 **Perfect Match!** They have very similar tastes!"
            elif compatibility_score >= 60:
                compatibility_text += "💫 **Great Compatibility!** They'd enjoy each other's recommendations!"
            elif compatibility_score >= 40:
                compatibility_text += "✨ **Good Match!** Some overlapping interests!"
            elif compatibility_score >= 20:
                compatibility_text += "🤔 **Different Tastes** but could discover new content!"
            else:
                compatibility_text += "🌍 **Opposite Tastes** - perfect for expanding horizons!"
            
            embed.add_field(
                name="💝 Compatibility Score",
                value=compatibility_text,
                inline=False
            )
            
            # Show shared favorites
            if shared_content:
                shared_list = list(shared_content)[:8]
                shared_text = ""
                for i, title in enumerate(shared_list, 1):
                    shared_text += f"{i}. **{title}**\n"
                
                if len(shared_content) > 8:
                    shared_text += f"*...and {len(shared_content) - 8} more*"
                
                embed.add_field(
                    name=f"🤝 Shared Favorites ({len(shared_content)} total)",
                    value=shared_text,
                    inline=False
                )
            
            # Recommendations (what one watched that other hasn't)
            user1_only = user1_content - user2_content
            user2_only = user2_content - user1_content
            
            recommendations_text = ""
            if user2_only:
                rec_list = list(user2_only)[:5]
                recommendations_text += f"**For {user1_username}** (from {user2_username}):\n"
                for title in rec_list:
                    recommendations_text += f"• {title}\n"
            
            if user1_only and user2_only:
                recommendations_text += "\n"
            
            if user1_only:
                rec_list = list(user1_only)[:5]
                recommendations_text += f"**For {user2_username}** (from {user1_username}):\n"
                for title in rec_list:
                    recommendations_text += f"• {title}\n"
            
            if recommendations_text:
                embed.add_field(
                    name="💡 Personalized Recommendations",
                    value=recommendations_text,
                    inline=False
                )
            
            # Genre analysis
            user1_genres = {}
            user2_genres = {}
            
            # Get detailed info for genre analysis (sample recent items)
            for item in user1_history[:20]:
                content = item.get('show') or item.get('movie')
                content_type = 'show' if 'show' in item else 'movie'
                try:
                    if content_type == 'show':
                        detailed = trakt_api.get_show_info(str(content['ids']['trakt']))
                    else:
                        detailed = trakt_api.get_movie_info(str(content['ids']['trakt']))
                    
                    if detailed and detailed.get('genres'):
                        for genre in detailed['genres']:
                            user1_genres[genre] = user1_genres.get(genre, 0) + 1
                except:
                    continue
            
            for item in user2_history[:20]:
                content = item.get('show') or item.get('movie')
                content_type = 'show' if 'show' in item else 'movie'
                try:
                    if content_type == 'show':
                        detailed = trakt_api.get_show_info(str(content['ids']['trakt']))
                    else:
                        detailed = trakt_api.get_movie_info(str(content['ids']['trakt']))
                    
                    if detailed and detailed.get('genres'):
                        for genre in detailed['genres']:
                            user2_genres[genre] = user2_genres.get(genre, 0) + 1
                except:
                    continue
            
            # Show top genres
            if user1_genres and user2_genres:
                user1_top = sorted(user1_genres.items(), key=lambda x: x[1], reverse=True)[:3]
                user2_top = sorted(user2_genres.items(), key=lambda x: x[1], reverse=True)[:3]
                
                genre_text = f"**{user1_username}:** "
                genre_text += " • ".join([g[0] for g in user1_top])
                genre_text += f"\n**{user2_username}:** "
                genre_text += " • ".join([g[0] for g in user2_top])
                
                embed.add_field(
                    name="🎭 Favorite Genres",
                    value=genre_text,
                    inline=False
                )
            
            # Activity patterns
            user1_activity_score = len(user1_history)
            user2_activity_score = len(user2_history)
            
            if user1_activity_score > user2_activity_score:
                more_active = user1_username
                activity_diff = user1_activity_score - user2_activity_score
            else:
                more_active = user2_username
                activity_diff = user2_activity_score - user1_activity_score
            
            if activity_diff == 0:
                activity_text = "🤝 **Equal Activity** - perfectly matched watching pace!"
            elif activity_diff <= 5:
                activity_text = f"⚖️ **Similar Activity** - {more_active} is slightly more active"
            elif activity_diff <= 15:
                activity_text = f"📈 **{more_active}** is noticeably more active (+{activity_diff} items)"
            else:
                activity_text = f"🚀 **{more_active}** is much more active (+{activity_diff} items)"
            
            embed.add_field(
                name="⚡ Activity Comparison",
                value=activity_text,
                inline=False
            )
            
            # Fun fact
            fun_facts = [
                f"🎯 They've discovered **{len(shared_content)}** titles in common!",
                f"🔍 **{len(user1_content.union(user2_content))}** unique titles between them both!",
                f"📚 **{len(user1_only) + len(user2_only)}** potential recommendations available!",
                f"🎪 Their combined watching power: **{len(user1_history) + len(user2_history)}** recent items!"
            ]
            
            import random
            embed.add_field(
                name="🎉 Fun Fact",
                value=random.choice(fun_facts),
                inline=False
            )
            
            # Add thumbnail from a shared favorite
            if shared_content:
                try:
                    shared_title = list(shared_content)[0]
                    search_results = trakt_api.search_content(shared_title)
                    if search_results:
                        content = search_results[0].get('show') or search_results[0].get('movie')
                        tmdb_id = content.get('ids', {}).get('tmdb')
                        if tmdb_id:
                            embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg")
                except:
                    pass
            
            # Add note about who requested the comparison
            comparison_type = "yourself" if user2.id == interaction.user.id else f"{user2.display_name}"
            embed.set_footer(text=f"🆚 Comparison requested by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error comparing users: {str(e)}")
            print(f"Compare error: {e}")

    @bot.tree.command(name="arena", description="🎬 Join the movie challenge Arena! Daily movie challenges & team competitions")
    async def arena_command(interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Check if user is connected
        user = db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`")
            return
        
        # Get arena status
        arena_data = db.get_arena_status()
        
        embed = discord.Embed(
            title="🎬🏟️ ARENA - Movie Challenge Hub",
            description="**Daily movie challenges • Team competitions • Epic rewards**",
            color=0xff4500
        )
        
        # Show current challenge
        if arena_data and arena_data.get('current_challenge'):
            challenge = arena_data['current_challenge']
            embed.add_field(
                name=f"🎯 Today's Challenge: {challenge['name']}",
                value=f"**{challenge['description']}**\n"
                      f"⏰ Ends: <t:{challenge['end_time']}:R>\n"
                      f"🏆 Reward: **{challenge['points']} points**",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 No Active Challenge",
                value="Waiting for challengers to join...",
                inline=False
            )
        
        # Show arena stats
        participants = db.get_arena_participants()
        teams = db.get_arena_teams()
        
        if participants:
            embed.add_field(
                name="🏟️ Arena Status",
                value=f"👥 **{len(participants)} players** ready\n"
                      f"👥 **{len(teams)} teams** formed\n"
                      f"🔥 **{len([p for p in participants if p.get('active_today', False)])} active** today",
                inline=True
            )
        
        # Show leaderboard preview
        if participants:
            top_players = sorted(participants, key=lambda x: x.get('points', 0), reverse=True)[:3]
            leaderboard_text = ""
            medals = ["🥇", "🥈", "🥉"]
            for i, player in enumerate(top_players):
                username = player['username']
                points = player.get('points', 0)
                leaderboard_text += f"{medals[i]} **{username}** • {points} pts\n"
            
            embed.add_field(
                name="🏆 Top Players",
                value=leaderboard_text,
                inline=True
            )
        
        # Action buttons
        view = ArenaView(interaction.user.id)
        
        embed.set_footer(text="🎬 Arena resets weekly • Only movie watchers survive!")
        await interaction.followup.send(embed=embed, view=view)

    @bot.tree.command(name="arena-complete", description="🏆 Complete arena challenge (auto-validates from Trakt)")
    async def arena_complete(interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Check if user is in arena
        if not db.is_in_arena(str(interaction.user.id)):
            await interaction.followup.send("❌ You're not in the Arena! Use `/arena` to join.", ephemeral=True)
            return
        
        # Get user data for Trakt access
        user = db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send("❌ You need to connect your Trakt.tv account first. Use `/connect`", ephemeral=True)
            return
        
        if not user.get('is_public', False):
            await interaction.followup.send("❌ You need a public Trakt profile to participate in Arena! Use `/public`", ephemeral=True)
            return
        
        # Check if there's an active challenge
        challenge = db.get_arena_challenge()
        if not challenge:
            await interaction.followup.send("❌ No active challenge right now!", ephemeral=True)
            return
        
        # Check if challenge expired
        import time
        if time.time() > challenge.get('end_time', 0):
            await interaction.followup.send("❌ Challenge has expired! Wait for the next one.", ephemeral=True)
            return
        
        # Basic validation - challenge must be at least 30 minutes old
        challenge_start = challenge.get('end_time', 0) - (24 * 60 * 60)  # 24h ago
        time_since_start = time.time() - challenge_start
        
        if time_since_start < 30 * 60:  # 30 minutes minimum
            minutes_left = int((30 * 60 - time_since_start) / 60)
            await interaction.followup.send(
                f"⏰ Challenge just started! Wait {minutes_left} more minutes before completing.\n"
                f"*This prevents instant completions and gives everyone fair time.*", 
                ephemeral=True
            )
            return
        
        # Check if already completed this challenge
        if db.has_completed_arena_challenge(str(interaction.user.id), challenge.get('name')):
            await interaction.followup.send("❌ You've already completed this challenge!", ephemeral=True)
            return
        
        # Validate against Trakt data
        await interaction.followup.send("🔍 Checking your Trakt watch history...", ephemeral=True)
        
        # Try to refresh token if needed
        validation_result = None
        access_token = user['access_token']
        
        try:
            validation_result = trakt_api.validate_arena_challenge(
                access_token, 
                challenge, 
                challenge_start
            )
        except Exception as e:
            print(f"First validation attempt failed: {e}")
            
            # Try refreshing the token
            try:
                token_response = trakt_api.refresh_token(user['refresh_token'])
                if token_response:
                    new_access_token = token_response['access_token']
                    new_refresh_token = token_response['refresh_token']
                    
                    # Update tokens in database
                    db.update_user_tokens(str(interaction.user.id), new_access_token, new_refresh_token)
                    
                    # Retry validation with new token
                    validation_result = trakt_api.validate_arena_challenge(
                        new_access_token, 
                        challenge, 
                        challenge_start
                    )
                else:
                    validation_result = {'valid': False, 'reason': 'Failed to refresh authentication token'}
            except Exception as refresh_error:
                print(f"Token refresh failed: {refresh_error}")
                validation_result = {'valid': False, 'reason': 'Authentication error. Please reconnect your Trakt account.'}
        
        if not validation_result or not validation_result['valid']:
            reason = validation_result.get('reason', 'Unknown validation error') if validation_result else 'Validation system error'
            
            # Provide helpful error messages based on reason
            if 'authentication' in reason.lower() or 'token' in reason.lower():
                error_message = (
                    f"❌ **Authentication Issue**\n\n"
                    f"Your Trakt connection needs to be refreshed.\n"
                    f"Please use `/connect` to reconnect your account."
                )
            elif 'no movies watched' in reason.lower():
                error_message = (
                    f"❌ **No Movies Found**\n\n"
                    f"We didn't find any movies in your recent Trakt history since this challenge started.\n\n"
                    f"**Current Challenge:** {challenge['name']}\n"
                    f"**Requirements:** {challenge['description']}\n\n"
                    f"💡 **Make sure to:**\n"
                    f"• Watch a movie that matches the challenge\n"
                    f"• Mark it as watched on Trakt.tv\n" 
                    f"• Wait a few minutes for sync, then try again"
                )
            elif 'no movies found that match' in reason.lower():
                error_message = (
                    f"❌ **No Matching Movies**\n\n"
                    f"We found movies in your recent history, but none match the challenge criteria.\n\n"
                    f"**Current Challenge:** {challenge['name']}\n"
                    f"**Requirements:** {challenge['description']}\n\n"
                    f"💡 **Double-check that your recent movie:**\n"
                    f"• Meets all the challenge requirements\n"
                    f"• Was watched AFTER the challenge started\n"
                    f"• Is properly marked as watched on Trakt"
                )
            else:
                error_message = (
                    f"❌ **Validation Error**\n\n"
                    f"**Reason:** {reason}\n\n"
                    f"**Current Challenge:** {challenge['name']}\n"
                    f"**Requirements:** {challenge['description']}\n\n"
                    f"💡 **Try these steps:**\n"
                    f"• Ensure your movie is marked as watched on Trakt\n"
                    f"• Wait a few minutes for sync\n"
                    f"• Check that the movie meets all requirements\n"
                    f"• If issues persist, try `/connect` to refresh your connection"
                )
            
            await interaction.edit_original_response(content=error_message)
            return
        
        # Complete challenge
        success = db.complete_arena_challenge(str(interaction.user.id))
        
        if success:
            validated_movie = validation_result.get('movie', {})
            participant = None
            for p in db.get_arena_participants():
                if p['discord_id'] == str(interaction.user.id):
                    participant = p
                    break
            
            embed = discord.Embed(
                title="🏆 Challenge Completed!",
                description=f"**{user['trakt_username']}** completed: **{challenge['name']}**",
                color=0x00ff00
            )
            
            embed.add_field(
                name="🎯 Challenge",
                value=challenge['description'],
                inline=False
            )
            
            if validated_movie:
                movie_year = validated_movie.get('year', 'Unknown')
                movie_rating = validated_movie.get('rating', 'Not rated')
                embed.add_field(
                    name="🎬 Validated Movie",
                    value=f"**{validated_movie.get('title', 'Unknown')}** ({movie_year})\n"
                          f"⭐ {movie_rating}/10 on Trakt",
                    inline=False
                )
            
            embed.add_field(
                name="📊 Rewards",
                value=f"🎬 **+{challenge['points']} points**\n"
                      f"🏆 Total: **{participant['points']} points**\n"
                      f"🥇 Wins: **{participant['challenges_won']}**",
                inline=True
            )
            
            embed.add_field(
                name="👥 Team",
                value=f"**{participant.get('team', 'No Team')}**",
                inline=True
            )
            
            embed.set_footer(text="✅ Validated against Trakt.tv data!")
            await interaction.edit_original_response(content=None, embed=embed)
        else:
            await interaction.edit_original_response(content="❌ Failed to record completion! Try again.")

    @bot.tree.command(name="arena-reset", description="🔄 Reset the entire Arena (Admin only)")
    async def arena_reset(interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Simple admin check - you can make this more sophisticated
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("❌ Admin only command!", ephemeral=True)
            return
        
        success = db.reset_arena()
        
        if success:
            embed = discord.Embed(
                title="🔄 Arena Reset!",
                description="The Arena has been completely reset!",
                color=0xff6600
            )
            embed.add_field(
                name="🎯 What was reset",
                value="• All participants removed\n"
                      "• Teams disbanded\n"
                      "• Challenges cleared\n"
                      "• Points reset to zero",
                inline=False
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Failed to reset arena!", ephemeral=True)

    @bot.tree.command(name="arena-status", description="📊 Check your Arena status and current challenge")
    async def arena_status(interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Check if user is in arena
        if not db.is_in_arena(str(interaction.user.id)):
            await interaction.followup.send("❌ You're not in the Arena! Use `/arena` to join.", ephemeral=True)
            return
        
        user = db.get_user(str(interaction.user.id))
        participant = None
        for p in db.get_arena_participants():
            if p['discord_id'] == str(interaction.user.id):
                participant = p
                break
        
        if not participant:
            await interaction.followup.send("❌ Arena data not found!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🏟️ {participant['username']}'s Arena Status",
            color=0x0099ff
        )
        
        # Personal stats
        embed.add_field(
            name="📊 Your Stats",
            value=f"🏆 **{participant['points']} points**\n"
                  f"🥇 **{participant['challenges_won']} challenges won**\n"
                  f"👥 **{participant.get('team', 'No Team')}**",
            inline=True
        )
        
        # Current challenge
        challenge = db.get_arena_challenge()
        if challenge:
            import time
            time_left = challenge.get('end_time', 0) - time.time()
            hours_left = max(0, int(time_left / 3600))
            
            embed.add_field(
                name="🎯 Current Challenge",
                value=f"**{challenge['name']}**\n"
                      f"{challenge['description']}\n"
                      f"⏰ **{hours_left}h remaining**\n"
                      f"🏆 **{challenge['points']} points**",
                inline=True
            )
        else:
            embed.add_field(
                name="🎯 Current Challenge",
                value="No active challenge",
                inline=True
            )
        
        # Team stats
        teams = db.get_arena_teams()
        user_team = participant.get('team')
        
        if teams and user_team:
            team_info = next((t for t in teams if t['name'] == user_team), None)
            if team_info:
                # Calculate team points
                team_points = 0
                team_wins = 0
                participants = db.get_arena_participants()
                
                for member_username in team_info['members']:
                    for p in participants:
                        if p['username'] == member_username:
                            team_points += p.get('points', 0)
                            team_wins += p.get('challenges_won', 0)
                
                embed.add_field(
                    name=f"👥 {user_team} Stats",
                    value=f"👥 **{len(team_info['members'])} members**\n"
                          f"🏆 **{team_points} total points**\n"
                          f"🥇 **{team_wins} total wins**",
                    inline=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="arena-new-challenge", description="🎲 Start a new random challenge (Admin only)")
    async def arena_new_challenge(interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Simple admin check
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("❌ Admin only command!", ephemeral=True)
            return
        
        # Check if arena has participants
        participants = db.get_arena_participants()
        if not participants:
            await interaction.followup.send("❌ No participants in Arena!", ephemeral=True)
            return
        
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
                "name": "Deep Cut",
                "description": "Watch a movie with **<1000 votes** on Trakt",
                "points": 25,
                "type": "obscure",
                "target": 1000
            },
            {
                "name": "Classic Quest",
                "description": "Watch a movie from **before 1980**",
                "points": 18,
                "type": "classic",
                "target": 1980
            },
            {
                "name": "Foreign Film",
                "description": "Watch a **non-English** movie",
                "points": 22,
                "type": "language",
                "target": "non-english"
            },
            {
                "name": "Action Pack",
                "description": "Watch any **Action** movie",
                "points": 12,
                "type": "genre",
                "target": "action"
            }
        ]
        
        import random
        challenge = random.choice(challenges)
        
        # Set 24 hour timer
        import time
        end_time = int(time.time()) + (24 * 60 * 60)
        challenge['end_time'] = end_time
        
        db.set_arena_challenge(challenge)
        
        # Notify about new challenge
        embed = discord.Embed(
            title=f"🎯 NEW Arena Challenge: {challenge['name']}",
            description=f"**{challenge['description']}**\n\n"
                       f"⏰ **24 hours** to complete\n"
                       f"🏆 **{challenge['points']} points** for completion\n"
                       f"🥇 **+5 bonus points** for first team to complete!\n"
                       f"🚪 **Arena stays open** for late joiners!",
            color=0xff4500
        )
        
        embed.add_field(
            name="📋 How to Complete",
            value="• Watch a movie that matches the challenge\n"
                  "• Mark it as watched on Trakt\n"
                  "• Bot will auto-detect and award points\n"
                  "• First team completion gets bonus!",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="arena-leave", description="🚪 Leave the Arena permanently")
    async def arena_leave(interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Check if user is in arena
        if not db.is_in_arena(str(interaction.user.id)):
            await interaction.followup.send("❌ You're not in the Arena!", ephemeral=True)
            return
        
        user = db.get_user(str(interaction.user.id))
        success = db.leave_arena(str(interaction.user.id))
        
        if success:
            embed = discord.Embed(
                title="🚪 Left Arena",
                description=f"**{user['trakt_username']}** has left the Arena!",
                color=0xff6600
            )
            embed.add_field(
                name="⚠️ What happens now",
                value="• Removed from all teams\n"
                      "• Points and progress lost\n"
                      "• Teams will be auto-rebalanced\n"
                      "• Can rejoin anytime with `/arena`",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            
            # Auto-rebalance remaining teams
            teams = db.get_arena_teams()
            if teams:
                db.rebalance_all_arena_teams()
        else:
            await interaction.followup.send("❌ Failed to leave arena!", ephemeral=True)

    @bot.tree.command(name="arena-teams", description="👥 View all Arena teams, scores, and current standings")
    async def arena_teams_overview(interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Get arena data
        participants = db.get_arena_participants()
        teams = db.get_arena_teams()
        current_challenge = db.get_arena_challenge()
        
        if not participants:
            await interaction.followup.send("❌ No participants in Arena yet! Use `/arena` to join.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="👥 Arena Teams Overview",
            description=f"**{len(participants)} players** across **{len(teams)} teams**",
            color=0x9d4edd
        )
        
        # Show current challenge
        if current_challenge:
            import time
            time_left = current_challenge.get('end_time', 0) - time.time()
            hours_left = max(0, int(time_left / 3600))
            
            embed.add_field(
                name="🎯 Current Challenge",
                value=f"**{current_challenge['name']}**\n"
                      f"{current_challenge['description']}\n"
                      f"⏰ **{hours_left}h remaining** • 🏆 **{current_challenge['points']} points**",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 Current Challenge",
                value="No active challenge",
                inline=False
            )
        
        if teams:
            # Calculate team stats
            team_stats = []
            for team in teams:
                team_points = 0
                team_wins = 0
                team_members_detail = []
                
                for member_username in team['members']:
                    # Find participant data
                    for participant in participants:
                        if participant['username'] == member_username:
                            points = participant.get('points', 0)
                            wins = participant.get('challenges_won', 0)
                            team_points += points
                            team_wins += wins
                            team_members_detail.append({
                                'username': member_username,
                                'points': points,
                                'wins': wins
                            })
                            break
                
                team_stats.append({
                    'name': team['name'],
                    'total_points': team_points,
                    'total_wins': team_wins,
                    'member_count': len(team['members']),
                    'members': team_members_detail,
                    'avg_points': team_points / max(len(team['members']), 1)
                })
            
            # Sort teams by total points
            team_stats.sort(key=lambda x: x['total_points'], reverse=True)
            
            # Team rankings
            team_rankings = ""
            medals = ["🥇", "🥈", "🥉"]
            
            for i, team in enumerate(team_stats):
                if i < 3:
                    rank_emoji = medals[i]
                else:
                    rank_emoji = f"{i+1}."
                
                team_rankings += f"{rank_emoji} **{team['name']}** • {team['total_points']} pts ({team['total_wins']} wins)\n"
                team_rankings += f"   👥 {team['member_count']} members • 📊 {team['avg_points']:.1f} avg\n"
            
            embed.add_field(
                name="🏆 Team Rankings",
                value=team_rankings,
                inline=False
            )
            
            # Detailed team breakdown
            for i, team in enumerate(team_stats[:3]):  # Show top 3 teams in detail
                members_text = ""
                # Sort team members by points
                sorted_members = sorted(team['members'], key=lambda x: x['points'], reverse=True)
                
                for j, member in enumerate(sorted_members):
                    if j == 0:
                        members_text += f"👑 **{member['username']}** • {member['points']} pts • {member['wins']} wins\n"
                    else:
                        members_text += f"🎯 **{member['username']}** • {member['points']} pts • {member['wins']} wins\n"
                
                embed.add_field(
                    name=f"{medals[i] if i < 3 else ''} {team['name']} Details",
                    value=members_text,
                    inline=True
                )
            
            # Competition stats
            total_arena_points = sum(p.get('points', 0) for p in participants)
            total_arena_wins = sum(p.get('challenges_won', 0) for p in participants)
            most_active_team = max(team_stats, key=lambda x: x['total_wins'])
            
            embed.add_field(
                name="📊 Arena Statistics",
                value=f"🎬 **{total_arena_points}** total points earned\n"
                      f"🏆 **{total_arena_wins}** challenges completed\n"
                      f"🔥 **{most_active_team['name']}** most active ({most_active_team['total_wins']} wins)\n"
                      f"📈 **{total_arena_wins / max(len(participants), 1):.1f}** avg challenges per player",
                inline=False
            )
            
            # Show current challenge completion status
            if current_challenge:
                completions = db.get_challenge_completions()
                if completions:
                    completion_text = ""
                    completed_teams = {}
                    
                    for completion in completions:
                        team_name = completion['team']
                        if team_name not in completed_teams:
                            completed_teams[team_name] = []
                        completed_teams[team_name].append(completion['username'])
                    
                    # Sort teams by number of completions
                    sorted_teams = sorted(completed_teams.items(), key=lambda x: len(x[1]), reverse=True)
                    
                    for team_name, completed_members in sorted_teams[:5]:  # Show top 5 teams
                        completion_text += f"👥 **{team_name}**: {', '.join(completed_members)}\n"
                    
                    if not completion_text:
                        completion_text = "No completions yet for current challenge"
                    
                    embed.add_field(
                        name="✅ Current Challenge Progress",
                        value=completion_text,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="✅ Current Challenge Progress", 
                        value="No completions yet - race is on! 🏁",
                        inline=False
                    )
        
        else:
            # No teams formed yet
            embed.add_field(
                name="👥 Participants (No Teams Yet)",
                value=f"**{len(participants)} players** waiting for team formation",
                inline=False
            )
            
            # Show individual participants
            participant_list = ""
            sorted_participants = sorted(participants, key=lambda x: x.get('points', 0), reverse=True)
            
            for i, participant in enumerate(sorted_participants[:10]):
                username = participant['username']
                points = participant.get('points', 0)
                wins = participant.get('challenges_won', 0)
                participant_list += f"{i+1}. **{username}** • {points} pts • {wins} wins\n"
            
            if participant_list:
                embed.add_field(
                    name="🎯 Individual Standings",
                    value=participant_list,
                    inline=False
                )
        
        # Add timestamp
        embed.set_footer(text="📊 Live arena data • Refreshes with each completion")
        await interaction.followup.send(embed=embed)

class ArenaView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)  # Never timeout - critical fix!
        self.user_id = user_id
    
    @discord.ui.button(label="🏟️ Join Arena", style=discord.ButtonStyle.danger, emoji="🎬")
    async def join_arena(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        user = db.get_user(str(interaction.user.id))
        if not user or not user.get('is_public', False):
            await interaction.followup.send("❌ You need a public Trakt profile to join Arena! Use `/public`", ephemeral=True)
            return
        
        # Check if already in arena
        if db.is_in_arena(str(interaction.user.id)):
            await interaction.followup.send("❌ You're already in the Arena!", ephemeral=True)
            return
        
        # Add user to arena
        success = db.add_arena_participant(str(interaction.user.id), user['trakt_username'])
        
        if success:
            participants = db.get_arena_participants()
            teams = db.get_arena_teams()
            
            # If arena already has teams, auto-balance the new joiner
            if teams:
                balanced_team = db.balance_arena_teams(str(interaction.user.id), user['trakt_username'])
                
                embed = discord.Embed(
                    title="🏟️ Joined Mid-Competition!",
                    description=f"**{user['trakt_username']}** joined the ongoing Arena!",
                    color=0x00ff00
                )
                embed.add_field(
                    name="👥 Auto-Balanced",
                    value=f"Added to **{balanced_team}** to keep teams fair!",
                    inline=False
                )
                embed.add_field(
                    name="🎯 Current Challenge",
                    value="Check current challenge and start competing immediately!",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
                
            else:
                # No teams yet, normal join flow
                embed = discord.Embed(
                    title="🏟️ Welcome to Arena!",
                    description=f"**{user['trakt_username']}** has entered the movie competition!",
                    color=0x00ff00
                )
                
                if len(participants) >= 4:
                    embed.add_field(
                        name="👥 Ready to Form Teams!",
                        value="Click **Team Setup** to vote on team sizes and start competing!",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="🎯 What's Next?",
                        value=f"• Wait for {4 - len(participants)} more players to join\n"
                              "• Vote on team sizes when we hit 4+ members\n" 
                              "• Compete in daily movie challenges\n"
                              "• Climb the leaderboard!",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Failed to join Arena! Try again.", ephemeral=True)
    
    @discord.ui.button(label="👥 Team Setup", style=discord.ButtonStyle.primary, emoji="👥")
    async def team_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        participants = db.get_arena_participants()
        if len(participants) < 4:
            await interaction.followup.send(f"❌ Need at least 4 players! Currently have {len(participants)}.", ephemeral=True)
            return
        
        # Check if teams already exist
        teams = db.get_arena_teams()
        if teams:
            embed = discord.Embed(
                title="👥 Teams Already Formed",
                description="Arena is running! New joiners are auto-balanced.",
                color=0x0099ff
            )
            
            team_text = ""
            for i, team in enumerate(teams, 1):
                team_text += f"**Team {i}** ({len(team['members'])} members): {', '.join(team['members'])}\n"
            
            embed.add_field(name="👥 Current Teams", value=team_text, inline=False)
            
            # Add rebalance option
            view = ArenaManagementView()
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            return
        
        # Start team size voting
        embed = discord.Embed(
            title="👥 Team Formation Vote",
            description=f"**{len(participants)} players** ready! How should we form teams?",
            color=0x0099ff
        )
        
        embed.add_field(
            name="⚖️ Voting Rules",
            value="• Majority vote decides team size\n"
                  "• After teams form, vote to start challenges\n"
                  "• Arena stays open for late joiners!",
            inline=False
        )
        
        view = TeamVoteView()
        await interaction.followup.send(embed=embed, view=view)
    
    @discord.ui.button(label="🏆 Leaderboard", style=discord.ButtonStyle.secondary, emoji="📊")
    async def show_leaderboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        participants = db.get_arena_participants()
        if not participants:
            await interaction.followup.send("❌ No players in Arena yet!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 Arena Leaderboard",
            description="**Hall of Movie Champions**",
            color=0xffd700
        )
        
        # Sort by points
        ranked_players = sorted(participants, key=lambda x: x.get('points', 0), reverse=True)
        
        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for i, player in enumerate(ranked_players[:10], 1):
            username = player['username']
            points = player.get('points', 0)
            wins = player.get('challenges_won', 0)
            team = player.get('team', 'No Team')
            
            if i <= 3:
                rank_emoji = medals[i-1]
            else:
                rank_emoji = f"{i}."
            
            leaderboard_text += f"{rank_emoji} **{username}** ({team}) • {points} pts • {wins} wins\n"
        
        embed.add_field(
            name="🎬 Movie Champions",
            value=leaderboard_text,
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="👥 Teams Overview", style=discord.ButtonStyle.secondary, emoji="👥")
    async def show_teams_overview(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Get arena data
        participants = db.get_arena_participants()
        teams = db.get_arena_teams()
        current_challenge = db.get_arena_challenge()
        
        if not participants:
            await interaction.followup.send("❌ No participants in Arena yet!", ephemeral=True)
            return
        
        if not teams:
            await interaction.followup.send("❌ No teams formed yet! Use **Team Setup** to create teams.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="👥 Teams Overview",
            description=f"**{len(participants)} players** across **{len(teams)} teams**",
            color=0x9d4edd
        )
        
        # Calculate team stats
        team_stats = []
        for team in teams:
            team_points = 0
            team_wins = 0
            
            for member_username in team['members']:
                # Find participant data
                for participant in participants:
                    if participant['username'] == member_username:
                        team_points += participant.get('points', 0)
                        team_wins += participant.get('challenges_won', 0)
                        break
            
            team_stats.append({
                'name': team['name'],
                'total_points': team_points,
                'total_wins': team_wins,
                'member_count': len(team['members']),
                'avg_points': team_points / max(len(team['members']), 1)
            })
        
        # Sort teams by total points
        team_stats.sort(key=lambda x: x['total_points'], reverse=True)
        
        # Team rankings
        team_rankings = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for i, team in enumerate(team_stats):
            if i < 3:
                rank_emoji = medals[i]
            else:
                rank_emoji = f"{i+1}."
            
            team_rankings += f"{rank_emoji} **{team['name']}** • {team['total_points']} pts\n"
            team_rankings += f"   👥 {team['member_count']} members • {team['total_wins']} wins • {team['avg_points']:.1f} avg\n\n"
        
        embed.add_field(
            name="🏆 Team Rankings",
            value=team_rankings,
            inline=False
        )
        
        # Current challenge
        if current_challenge:
            import time
            time_left = current_challenge.get('end_time', 0) - time.time()
            hours_left = max(0, int(time_left / 3600))
            
            embed.add_field(
                name="🎯 Current Challenge",
                value=f"**{current_challenge['name']}**\n"
                      f"⏰ **{hours_left}h remaining** • 🏆 **{current_challenge['points']} points**",
                inline=False
            )
        
        embed.set_footer(text="💡 Use /arena-teams for detailed team breakdown")
        await interaction.followup.send(embed=embed, ephemeral=True)

class ArenaManagementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Never timeout - critical fix!
    
    @discord.ui.button(label="⚖️ Rebalance Teams", style=discord.ButtonStyle.secondary)
    async def rebalance_teams(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Rebalance all teams
        teams = db.rebalance_all_arena_teams()
        
        embed = discord.Embed(
            title="⚖️ Teams Rebalanced!",
            description="All teams have been fairly redistributed!",
            color=0x00ff00
        )
        
        team_text = ""
        for i, team in enumerate(teams, 1):
            team_text += f"**Team {i}** ({len(team['members'])} members): {', '.join(team['members'])}\n"
        
        embed.add_field(name="🛡️ New Team Distribution", value=team_text, inline=False)
        
        await interaction.followup.send(embed=embed)

class TeamVoteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Never timeout - critical fix!
        # Load persistent voting state from database
        self.votes = db.get_arena_vote_state().get('size_votes', {})
        self.start_votes = set(db.get_arena_vote_state().get('start_votes', []))
    
    @discord.ui.button(label="👥 Teams of 2", style=discord.ButtonStyle.primary)
    async def vote_pairs(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes[str(interaction.user.id)] = 2
        db.save_arena_vote_state({'size_votes': self.votes, 'start_votes': list(self.start_votes)})
        await interaction.response.send_message("✅ Voted for teams of 2!", ephemeral=True)
        await self.check_vote_completion(interaction)
    
    @discord.ui.button(label="👥 Teams of 3", style=discord.ButtonStyle.primary) 
    async def vote_trios(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes[str(interaction.user.id)] = 3
        db.save_arena_vote_state({'size_votes': self.votes, 'start_votes': list(self.start_votes)})
        await interaction.response.send_message("✅ Voted for teams of 3!", ephemeral=True)
        await self.check_vote_completion(interaction)
    
    @discord.ui.button(label="👥 Teams of 4+", style=discord.ButtonStyle.primary)
    async def vote_squads(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes[str(interaction.user.id)] = 4
        db.save_arena_vote_state({'size_votes': self.votes, 'start_votes': list(self.start_votes)})
        await interaction.response.send_message("✅ Voted for larger teams!", ephemeral=True)
        await self.check_vote_completion(interaction)
    
    @discord.ui.button(label="🚀 START ARENA", style=discord.ButtonStyle.success, emoji="⚡")
    async def start_arena(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if teams are formed first
        teams = db.get_arena_teams()
        if not teams:
            await interaction.response.send_message("❌ Form teams first before starting!", ephemeral=True)
            return
        
        self.start_votes.add(str(interaction.user.id))
        db.save_arena_vote_state({'size_votes': self.votes, 'start_votes': list(self.start_votes)})
        
        participants = db.get_arena_participants()
        needed_votes = max(2, len(participants) // 2)  # At least 2 votes needed
        
        if len(self.start_votes) >= needed_votes:
            await interaction.response.defer()
            # Clear voting state after successful start
            db.clear_arena_vote_state()
            await self.start_daily_challenge(interaction)
        else:
            await interaction.response.send_message(
                f"✅ Voted to start! ({len(self.start_votes)}/{needed_votes} votes needed)", 
                ephemeral=True
            )
    
    async def check_vote_completion(self, interaction):
        participants = db.get_arena_participants()
        
        # If majority voted, form teams
        if len(self.votes) >= len(participants) // 2 + 1:
            # Count votes
            vote_counts = {}
            for vote in self.votes.values():
                vote_counts[vote] = vote_counts.get(vote, 0) + 1
            
            # Handle ties by picking random winner
            max_votes = max(vote_counts.values())
            tied_options = [size for size, count in vote_counts.items() if count == max_votes]
            
            import random
            winning_size = random.choice(tied_options) if len(tied_options) > 1 else tied_options[0]
            
            # Form teams
            teams = db.create_arena_teams(winning_size)
            
            if teams:
                embed = discord.Embed(
                    title="👥 Teams Formed!",
                    description=f"Teams of {winning_size} won the vote!",
                    color=0x00ff00
                )
                
                team_text = ""
                for i, team in enumerate(teams, 1):
                    team_text += f"**Team {i}**: {', '.join(team['members'])}\n"
                
                embed.add_field(name="👥 Competition Teams", value=team_text, inline=False)
            
            embed.add_field(
                name="🚀 Ready to Start?", 
                value="Vote **START ARENA** to begin daily challenges!\n"
                      "⚠️ Arena stays open for late joiners (auto-balanced)",
                inline=False
            )
            
            # Enable start button by updating the view
            self.start_arena.disabled = False
            await interaction.edit_original_response(embed=embed, view=self)
    
    async def start_daily_challenge(self, interaction):
        """Start the first daily challenge"""
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
                "name": "Deep Cut",
                "description": "Watch a movie with **<1000 votes** on Trakt",
                "points": 25,
                "type": "obscure",
                "target": 1000
            },
            {
                "name": "Classic Quest",
                "description": "Watch a movie from **before 1980**",
                "points": 18,
                "type": "classic",
                "target": 1980
            },
            {
                "name": "Foreign Film",
                "description": "Watch a **non-English** movie",
                "points": 22,
                "type": "language",
                "target": "non-english"
            },
            {
                "name": "Action Pack",
                "description": "Watch any **Action** movie",
                "points": 12,
                "type": "genre",
                "target": "action"
            }
        ]
        
        import random
        challenge = random.choice(challenges)
        
        # Set 24 hour timer
        import time
        end_time = int(time.time()) + (24 * 60 * 60)
        challenge['end_time'] = end_time
        
        db.set_arena_challenge(challenge)
        db.set_arena_active(True)
        
        # Notify participants
        challenge_embed = discord.Embed(
            title=f"🎯 Arena Challenge: {challenge['name']}",
            description=f"**{challenge['description']}**\n\n"
                       f"⏰ **24 hours** to complete\n"
                       f"🏆 **{challenge['points']} points** for completion\n"
                       f"🥇 **+5 bonus points** for first team to complete!\n"
                       f"🚪 **Arena stays open** for late joiners!",
            color=0xff4500
        )
        
        challenge_embed.add_field(
            name="📋 How to Complete",
            value="• Watch a movie that matches the challenge\n"
                  "• Mark it as watched on Trakt\n"
                  "• Bot will auto-detect and award points\n"
                  "• First team completion gets bonus!",
            inline=False
        )
        
        await interaction.followup.send(embed=challenge_embed)
        
        # Disable all voting buttons since arena started
        for item in self.children:
            if item.label != "🚀 START ARENA":
                item.disabled = True
        self.start_arena.label = "✅ ARENA STARTED"
        self.start_arena.disabled = True
        
        await interaction.edit_original_response(view=self) 