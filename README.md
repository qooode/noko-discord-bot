# Noko - Advanced Discord Trakt.tv Bot

A **powerful and interactive** Discord bot for managing your Trakt.tv account with modern Discord features!

## ✨ Advanced Features

### 🎮 **Interactive UI**
- **Button Navigation** - Browse search results with Previous/Next buttons
- **Dropdown Menus** - Select content from interactive dropdowns  
- **Action Buttons** - Mark watched, add to watchlist, set reminders with one click
- **Modal Forms** - Custom reminder settings with rich input forms
- **Pagination** - Navigate through multiple pages of results seamlessly

### 🔍 **Smart Search & Autocomplete**
- **Real-time Autocomplete** - Shows/movies suggest as you type
- **Interactive Search Results** - Browse with buttons, get info with dropdowns
- **Quick Actions** - One command to search, mark watched, or add to watchlist
- **Context Menu** - Right-click any message to extract show/movie info

### 🎬 **Enhanced Content Management**
- **One-click Actions** - Interactive buttons for all operations
- **Smart Reminders** - Custom timing and messages for episode notifications
- **Rich Statistics** - Comprehensive stats with recent activity tracking
- **Instant Feedback** - Embeds with status updates and confirmation

### 👥 **Advanced Social Features**  
- **Public/Private Profiles** - Control who sees your activity
- **User Stats Comparison** - View detailed statistics for any user
- **Activity Tracking** - See what friends are watching in real-time

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

### **Context Menu Commands** (Right-click)
- **"Quick Trakt Info"** - Right-click any message to extract show/movie info

## 🎮 Interactive Features

### **Search Interface**
```
🔍 Search Results for 'Breaking Bad'    Page 1/3
┌─────────────────────────────────────────────┐
│ 1. Breaking Bad (2008) - Show              │
│ ⭐ 9.3/10                                  │
│ A high school chemistry teacher...          │
└─────────────────────────────────────────────┘
[◀️ Previous] [▶️ Next] [📺 More Info]
```

### **Action Buttons**
After getting show/movie info:
```
[✅ Mark Watched] [📋 Add to Watchlist] [🔔 Set Reminder]
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

### **Smart Autocomplete**
As you type `/search bre...`:
```
🔍 Breaking Bad (2008)
🔍 Breaking (2008) 
🔍 Breakfast Club (1985)
```

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