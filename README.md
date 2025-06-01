# Noko - Advanced Discord Trakt.tv Bot

A **powerful and interactive** Discord bot for managing your Trakt.tv account with modern Discord features and **rich visual content**!

## ✨ Advanced Features

### 🎮 **Interactive UI with Rich Visuals**
- **Button Navigation** - Browse search results with Previous/Next buttons
- **Dropdown Menus** - Select content from interactive dropdowns  
- **Action Buttons** - Mark watched, add to watchlist, set reminders with one click
- **Modal Forms** - Custom reminder settings with rich input forms
- **Pagination** - Navigate through multiple pages of results seamlessly
- **🖼️ Poster Images** - Beautiful movie/show posters in all displays
- **📊 Rich Data** - Ratings with vote counts, runtime, genres, release dates
- **🌟 Enhanced Visuals** - Thumbnails, full images, and styled embeds

### 🔍 **Smart Search & Autocomplete**
- **Real-time Autocomplete** - Shows/movies suggest as you type
- **Interactive Search Results** - Browse with buttons, get info with dropdowns
- **🎬 Visual Search** - Poster thumbnails and rich details in results
- **Quick Actions** - One command to search, mark watched, or add to watchlist
- **Context Menu** - Right-click any message to extract show/movie info

### 🎬 **Enhanced Content Management**
- **Advanced Episode Management** - Season/episode tracking with interactive UI
- **Progress Tracking** - Visual progress bars and completion stats
- **Continue Watching** - Smart detection of partially watched shows
- **One-click Actions** - Interactive buttons for all operations
- **Smart Reminders** - Custom timing and messages for episode notifications
- **Rich Statistics** - Comprehensive stats with recent activity tracking
- **🖼️ Visual Feedback** - Poster images and detailed info in all responses
- **📈 Enhanced Data** - Vote counts, genres, release dates, runtime info

### 👥 **Advanced Social Features**  
- **Public/Private Profiles** - Control who sees your activity
- **User Stats Comparison** - View detailed statistics for any user
- **Activity Tracking** - See what friends are watching in real-time
- **🎭 Visual Activity** - Profile images and content posters in social features
- **🌍 Live Community Feed** - Real-time activity from all public users
- **📈 Community Trends** - Aggregated stats and trending content
- **🔥 Social Discovery** - Find what's hot in your community

### 🎬 **ARENA - Movie Challenge System**
- **Daily Movie Challenges** - Compete in rotating movie-based challenges
- **Team Battles** - Form teams and compete together for points
- **Democratic Team Formation** - Vote on team sizes and participate democratically
- **Challenge Variety** - Genre Master, Decade Dive, Rating Rush, Speed Run, and more
- **Auto-Balancing** - Late joiners are automatically balanced into teams
- **Point System** - Earn points and climb leaderboards through movie watching
- **Honor System** - Complete challenges through self-reporting with basic validation
- **Weekly Resets** - Fresh competition cycles keep the arena exciting
- **Persistent State** - Arena survives bot restarts and maintains ongoing battles
- **Admin Controls** - Moderators can reset arena and manually start challenges

## 🏗️ Architecture

### **Modular Design**
The bot features a clean, modular architecture for easy maintenance and development:

```
📁 Project Structure
├── main.py          # Bot initialization, Discord setup, entry point
├── commands.py      # Basic commands, account management, content operations
├── management.py    # Advanced show/episode management, progress tracking
├── social.py        # Community features, trends, social interactions
├── views.py         # Discord UI components (buttons, modals, dropdowns)
├── trakt_api.py     # Trakt.tv API wrapper and methods
├── database.py      # User data and reminder management
├── config.py        # Configuration and environment variables
└── requirements.txt # Python dependencies
```

### **Clean Separation of Concerns**
- **main.py** - Core bot setup, event handling, background tasks
- **commands.py** - User-facing slash commands and basic operations
- **management.py** - Complex show management and episode tracking
- **social.py** - Community features, social interactions, and Arena system
- **views.py** - All Discord UI components and interactive elements
- **trakt_api.py** - Trakt.tv API integration and data handling
- **database.py** - Persistent data storage, user management, and Arena data

## Quick Setup

1. **Clone and Install**
   ```bash
   git clone https://github.com/qooode/trakt-discord-bot.git
   cd trakt-discord-bot
   pip install -r requirements.txt
   ```

2. **Discord Bot Setup**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application and bot
   - Copy the bot token
   - **IMPORTANT**: Go to the "Bot" section and enable these privileged intents:
     - ✅ **Message Content Intent** (required)
     - ✅ **Server Members Intent** (recommended)
   - Save changes

3. **Trakt.tv API Setup**
   - Go to [Trakt.tv API](https://trakt.tv/oauth/applications)
   - Create a new application
   - Copy Client ID and Client Secret
   - Set Redirect URI to: `urn:ietf:wg:oauth:2.0:oob`

4. **Configuration**
   - Create `.env` file with your settings:
   ```bash
   # Discord Bot Settings
   DISCORD_TOKEN=your_discord_bot_token_here
   COMMAND_PREFIX=!

   # Trakt.tv API Settings
   TRAKT_CLIENT_ID=your_trakt_client_id_here
   TRAKT_CLIENT_SECRET=your_trakt_client_secret_here
   TRAKT_REDIRECT_URI=urn:ietf:wg:oauth:2.0:oob

   # Bot Settings
   BOT_NAME=Noko
   ```

5. **Run the Bot**
   ```bash
   python main.py
   ```

## Server Deployment

For production deployment on a server:

```bash
# Kill any existing bot processes
pkill -f "python.*main.py"

# Clean up and clone fresh
mkdir trakt-bot
cd ..
rm -rf trakt-bot
git clone https://github.com/qooode/trakt-discord-bot.git trakt-bot

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
cd trakt-bot

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
nano .env

# Run bot in background with logging
nohup python main.py > bot.log 2>&1 &
```

**Managing the bot:**
```bash
# Check if bot is running
ps aux | grep main.py

# Stop the bot (replace PID with actual process ID)
kill [PID]

# View logs
tail -f bot.log
```

## 🚀 Comprehensive Command Reference

### **🔐 Account Management**
- `/connect` - Link your Trakt.tv account with guided setup
- `/authorize <code>` - Complete authorization with Trakt.tv code
- `/public` / `/private` - Control profile visibility
- `/stats` - View comprehensive account statistics

### **🔍 Smart Content Discovery** 
- `/search <query>` - **Interactive search** with pagination and action buttons
  - Browse results with ◀️ ▶️ buttons
  - Select items from dropdown for detailed info
  - One-click mark watched, add to watchlist, set reminders
- `/info <show/movie>` - Detailed info **with action buttons**

### **🎬 Content Management**
- `/watched <show/movie>` - Mark as watched (with autocomplete)
- `/watchlist <show/movie>` - Add to watchlist (with autocomplete)

### **📺 Advanced Show Management**
- `/progress <show>` - **Visual progress tracking** with interactive management
  - View completion percentages per season
  - Interactive season/episode management
  - Progress bars and statistics
- `/manage <show>` - **Complete show management** interface
  - Season selection with episode counts
  - Individual episode tracking
  - Mark/unmark episodes and seasons
- `/continue` - **Smart continue watching** - Find shows you can continue
- `/episode <show> <season> <episode>` - **Direct episode management**

### **🔔 Enhanced Reminders**
- `/remind <show>` - **Custom reminder setup** with modal form
  - Set hours before episode airs
  - Add custom reminder messages
  - Interactive setup with buttons
- `/reminders` - List all active reminders

### **👥 Social & Community Features**
- `/watching [user]` - See current watching activity
- `/last [user] [count]` - Recent watches (1-10 items)
- `/community` - **Live community activity feed** 🔴
  - Real-time watching activity
  - Trending shows and movies
  - Active user counts and stats
- `/trends [days]` - **Community trends & analytics** (1-14 days)
  - Popular content over time
  - Most active community members
  - Aggregated watching statistics

### **🎬 ARENA - Movie Challenge Commands**
- `/arena` - **Join the movie challenge Arena** 🎬
  - Enter daily movie competitions
  - View current challenges and leaderboards
  - Interactive team formation system
- `/arena-status` - **Check your Arena progress** 📊
  - View personal stats and team information
  - See current challenge details and time remaining
  - Track points and wins
- `/arena-complete` - **Mark current challenge as completed** 🏆
  - Self-report challenge completion
  - Earn points and increase win count
  - Honor system with basic validation
- `/arena-leave` - **Leave Arena permanently** 🚪
  - Exit arena and lose all progress
  - Teams automatically rebalanced
  - Can rejoin anytime
- `/arena-reset` - **Reset entire Arena** (Admin only) 🔄
  - Clear all participants and teams
  - Reset points and challenges
  - Fresh start for community
- `/arena-new-challenge` - **Start new challenge** (Admin only) 🎲
  - Manually trigger new random challenge
  - Override automatic rotation
  - Control arena flow

### **💡 Help & Discovery**
- `/help` - **Complete command guide** with examples and getting started tips

### **🖱️ Context Menu Commands** (Right-click)
- **"Quick Trakt Info"** - Right-click any message to extract show/movie info

## 🎮 Interactive Features

### **Enhanced Search Interface with Visuals**
```
🔍 Search Results for 'Breaking Bad'    Page 1/3
┌─────────────────────────────────────────────┐
│ 🖼️ [Poster]  1. Breaking Bad (2008) - Show │
│ ⭐ 9.3/10 (45,678 votes)                   │
│ ⏱️ 47 min • 📺 Ended                       │
│ 🏷️ Drama, Crime, Thriller                  │
│ A high school chemistry teacher...          │
└─────────────────────────────────────────────┘
[◀️ Previous] [▶️ Next] [📺 More Info]
```

### **Rich Content Information**
```
🎬 Breaking Bad (2008)
🖼️ [Full Poster Image]

📊 Details:
⭐ 9.3/10 (45,678 votes)
⏱️ 47 min episodes
📺 Ended • 📡 AMC
📅 First Aired: 2008-01-20
🏷️ Drama, Crime, Thriller, Dark Comedy
🌍 Available in: English, Spanish, German...
🎥 Watch Trailer | 🌐 Official Site
```

### **Action Buttons with Visual Feedback**
After getting show/movie info:
```
[✅ Mark Watched] [📋 Add to Watchlist] [🔔 Set Reminder]
```

### **Visual Social Features**
```
📺 Currently Watching
👤 username is watching:

🖼️ [Poster] Better Call Saul
S6E13: Waterworks
⭐ 9.0/10 • ⏱️ 63 min
```

### **Custom Reminder Modal**
```
┌─ Reminder Settings for Breaking Bad ────────┐
│ Reminder Time: [2] hours before episode     │
│ Custom Message: [Don't miss new episode!]   │
│                                              │
│                    [Submit]                  │
└──────────────────────────────────────────────┘
```

### **Smart Autocomplete with Rich Previews**
As you type `/search bre...`:
```
🔍 🎬 Breaking Bad (2008) - ⭐ 9.3/10
🔍 🎭 Breaking (2008) - ⭐ 7.2/10
🔍 🎪 Breakfast Club (1985) - ⭐ 7.8/10
```

### **Live Community Activity**
```
🌍 Community Watch - Live Activity
Real-time activity from 12 public members

📊 Community Stats
👥 45 total • 12 public • 5 active now

🔥 What's Hot Right Now
📺 Trending Shows:
• Breaking Bad (3 watching)
• The Office (2 watching)

🎬 Trending Movies:
• Oppenheimer (2 watching)

🔴 Live Activity (5 active)
📺 alice_tv watching Breaking Bad
   S5E14: Ozymandias
   ⭐ 9.9/10

🎬 bob_movies watching Oppenheimer
   ⭐ 8.3/10
```

### **Community Trends & Analytics**
```
📈 Community Trends - Past 7 Days
Aggregated activity from 12 public members

📊 Community Activity Overview
📺 156 episodes watched
🎬 23 movies watched  
👥 8 active members
🏆 47 unique titles

📺 Trending Shows    🎬 Trending Movies    🔥 Most Active
1. The Office • 23   1. Oppenheimer • 5    1. alice_tv • 34
2. Breaking Bad • 19 2. Barbie • 4         2. movie_bob • 28
3. Stranger Things  3. GOTG Vol 3 • 3     3. bingewatcher • 22

🎯 Fun Stats
📊 19.9 avg watches per active user
⏱️ ~7,650 hours of content consumed
🗓️ 7 days of community activity
```

### **Arena Movie Challenge Interface**
```
🎬⚔️ ARENA - Movie Challenge Hub
Daily movie duels • Team battles • Epic challenges

🎯 Today's Challenge: Genre Master
Watch any Horror movie you haven't seen
⏰ Ends in 18 hours
🏆 Reward: 10 points

⚔️ Arena Status
👥 12 gladiators ready
🛡️ 3 teams formed  
🔥 8 active today

🏆 Top Gladiators
🥇 movie_master • 85 pts
🥈 film_buff • 72 pts  
🥉 cinema_queen • 68 pts

[⚔️ Join Arena] [🛡️ Team Setup] [🏆 Leaderboard]
```

### **Arena Team Formation**
```
🛡️ Team Formation Vote
12 gladiators ready! How should we form teams?

⚖️ Voting Rules
• Majority vote decides team size
• After teams form, vote to start challenges  
• Arena stays open for late joiners!

[👥 Teams of 2] [🛡️ Teams of 3] [⚔️ Teams of 4+]

🛡️ Teams Formed!
Teams of 3 won the vote!

⚔️ Battle Teams
Team 1: alice_movies, bob_cinema, charlie_films
Team 2: diana_watch, eve_binge, frank_movie  
Team 3: grace_film, henry_show, iris_tv
Team 4: jack_watch, kelly_cinema

[🚀 START ARENA]
```

### **Challenge Completion**
```
🏆 Challenge Completed!
movie_master completed: Genre Master

🎯 Challenge  
Watch any Horror movie you haven't seen

📊 Rewards
🎬 +10 points
🏆 Total: 85 points
🥇 Wins: 8

🛡️ Team: Team 1

Honor system - thanks for playing fairly! ��
```

## 🖼️ Visual Content Features

### **Poster Integration**
- **Search Results** - Thumbnail posters for visual browsing
- **Detailed Info** - Full-size poster images with content details
- **Social Features** - Profile images in watching activity
- **Quick Info** - Instant poster thumbnails in context menus

### **Rich Data Display**
- **Enhanced Ratings** - Star ratings with vote counts (⭐ 9.3/10 (45,678 votes))
- **Runtime Info** - Formatted time displays (⏱️ 47 min)
- **Status Indicators** - Show status with icons (📺 Ended, 📡 AMC)
- **Genre Tags** - Visual genre categorization (🏷️ Drama, Crime)
- **Release Dates** - Formatted air dates (📅 2008-01-20)
- **Language Support** - Available translations (🌍 English, Spanish...)

### **Visual Enhancement Details**
- **TMDB Integration** - High-quality poster images from The Movie Database
- **Smart Thumbnails** - Appropriately sized images for different contexts
- **Fallback Handling** - Graceful degradation when images aren't available
- **Rich Embeds** - Beautiful Discord embeds with proper formatting
- **Icon Usage** - Consistent iconography throughout the interface

## Privacy & Social

### **Profile Control**
- `/public` - Make profile public for social features
- `/private` - Make profile private (default)

### **Social Features** (Public profiles only)
- See what friends are watching
- View recent watch history  
- Compare statistics

## 🛠️ Technical Features

### **Modern Discord Integration**
- **Slash Commands** - Native Discord command system
- **Button Components** - Interactive UI elements  
- **Select Menus** - Dropdown selection interfaces
- **Modal Forms** - Rich input dialogs
- **Context Menus** - Right-click commands
- **Autocomplete** - Real-time suggestions
- **Deferred Responses** - No timeout issues
- **Ephemeral Messages** - Private error messages

### **Enhanced User Experience**
- **Pagination** - Navigate large result sets
- **One-click Actions** - Reduce command complexity
- **Smart Error Handling** - Graceful failure recovery
- **Rich Embeds** - Beautiful, informative displays
- **Real-time Feedback** - Instant status updates

## Troubleshooting

### ❌ `PrivilegedIntentsRequired` Error
If you get this error when starting the bot:
```
discord.errors.PrivilegedIntentsRequired: Shard ID None is requesting privileged intents...
```

**Solution:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Go to the "Bot" section
4. Scroll down to "Privileged Gateway Intents"
5. Enable **Message Content Intent**
6. Click "Save Changes"
7. Restart your bot

### 🔑 Invalid Token Error
- Make sure your `DISCORD_TOKEN` in `.env` is correct
- Regenerate the token in Discord Developer Portal if needed

### 🔗 Trakt.tv API Issues
- Verify your `TRAKT_CLIENT_ID` and `TRAKT_CLIENT_SECRET` are correct
- Make sure the redirect URI is set to: `urn:ietf:wg:oauth:2.0:oob`

### 📝 Bot Not Responding
- Check the bot has proper permissions in your Discord server
- Slash commands may take a few minutes to sync when first starting
- Check `bot.log` for error messages
- Ensure all required files are present:
  - `main.py` - Entry point
  - `commands.py` - Command definitions
  - `management.py` - Show management
  - `social.py` - Community features
  - `views.py` - UI components
  - `trakt_api.py` - API integration
  - `database.py` - Data management
  - `config.py` - Configuration

### 🎮 Interactive Features Not Working
- Ensure your Discord client is up to date
- Some features require newer Discord versions
- Mobile Discord may have limited interactive support

### 🐛 Development & Debugging
- Use `python main.py` to run in development mode
- Check console output for detailed error messages
- Enable debug logging by setting environment variable: `DISCORD_DEBUG=True`
- Each module can be tested independently for troubleshooting

### 📁 File Structure Issues
If you're missing files or having import errors:
```bash
# Verify all required files are present
ls -la
# Should show: main.py commands.py management.py social.py views.py trakt_api.py database.py config.py

# Check Python path issues
python -c "import commands, management, social, views, trakt_api, database, config"
```

## 🚀 Contributing

The modular structure makes it easy to contribute:

- **commands.py** - Add new slash commands
- **management.py** - Enhance show/episode management
- **social.py** - Add community features
- **views.py** - Create new UI components
- **trakt_api.py** - Extend API functionality

Each module is focused and independent, making development and testing straightforward! 