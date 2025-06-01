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