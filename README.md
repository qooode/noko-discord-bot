# Noko - Discord Trakt.tv Bot

A powerful Discord bot for managing your Trakt.tv account and tracking shows/movies with friends!

## Features

- 🎬 **Account Management**: Mark shows as watched, unmark, add to watchlist
- 👥 **Social Watching**: See what friends are watching (public profiles only)
- ⏰ **Episode Reminders**: Get notified when new episodes air
- 📺 **Progress Tracking**: Check watching progress and next episodes
- 🔍 **Show Discovery**: Search and get info about shows/movies

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

## Commands

### Account Management
- `!connect` - Link your Trakt.tv account
- `!watched <show/movie>` - Mark as watched
- `!unwatch <show/movie>` - Unmark as watched
- `!watchlist <show/movie>` - Add to watchlist
- `!progress` - Show your watching progress

### Social Features
- `!watching @user` - See what someone is watching
- `!last @user` - See last watched content
- `!next @user` - See upcoming episodes
- `!profile @user` - View user's profile

### Reminders
- `!remind <show>` - Get reminded for new episodes
- `!unremind <show>` - Stop reminders for a show
- `!reminders` - List all your reminders

### General
- `!search <query>` - Search for shows/movies
- `!info <show/movie>` - Get detailed info
- `!help` - Show all commands

## Privacy

Users can control their privacy with:
- `!public` - Make profile public
- `!private` - Make profile private 