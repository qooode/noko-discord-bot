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

## Quick Setup

1. **Clone and Install**
   ```bash
   git clone https://github.com/qooode/noko-discord-bot.git
   cd noko-discord-bot
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
   python noko.py
   ```

## Server Deployment

For production deployment on a server:

```bash
# Kill any existing bot processes
pkill -f "python.*noko.py"

# Clean up and clone fresh
mkdir noko
cd ..
rm -rf noko
git clone https://github.com/qooode/noko-discord-bot.git noko

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
cd noko

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
nano .env

# Run bot in background with logging
nohup python noko.py > bot.log 2>&1 &
```

**Managing the bot:**
```bash
# Check if bot is running
ps aux | grep noko.py

# Stop the bot (replace PID with actual process ID)
kill [PID]

# View logs
tail -f bot.log
```

## 🚀 Advanced Slash Commands

### **Account Management**
- `/connect` - Link your Trakt.tv account with guided setup
- `/public` / `/private` - Control profile visibility
- `/stats` - View comprehensive account statistics

### **Smart Content Discovery** 
- `/search <query>` - **Interactive search** with pagination and action buttons
  - Browse results with ◀️ ▶️ buttons
  - Select items from dropdown for detailed info
  - One-click mark watched, add to watchlist, set reminders
- `/quick_action <content> <action>` - **One-command workflow**
  - Autocomplete content names as you type
  - Choose: Mark Watched, Watchlist, Set Reminder, Get Info
- `/info <show/movie>` - Detailed info **with action buttons**

### **Advanced Content Management**
- `/watched <show/movie>` - Mark as watched (with autocomplete)
- `/unwatch <show/movie>` - Remove from watched (with autocomplete)  
- `/watchlist <show/movie>` - Add to watchlist (with autocomplete)

### **Enhanced Reminders**
- `/remind <show>` - **Custom reminder setup** with modal form
  - Set hours before episode airs
  - Add custom reminder messages
  - Interactive setup with buttons
- `/unremind <show>` - Remove reminders (with autocomplete)
- `/reminders` - List all active reminders

### **Social Features**
- `/watching [user]` - See current watching activity
- `/last [user] [count]` - Recent watches (1-10 items)
- `/community` - **Live community activity feed** 🔴
- `/trends [days]` - **Community trends & analytics** (1-14 days)

### **Context Menu Commands** (Right-click)
- **"Quick Trakt Info"** - Right-click any message to extract show/movie info

### **Help & Discovery**
- `/help` - **Complete command guide** with examples and getting started tips

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

### 🎮 Interactive Features Not Working
- Ensure your Discord client is up to date
- Some features require newer Discord versions
- Mobile Discord may have limited interactive support 