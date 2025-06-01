# Noko - Discord Trakt.tv Bot

A powerful Discord bot for managing your Trakt.tv account and tracking shows/movies with friends!

## Features

- 🎬 **Account Management**: Mark shows as watched, unmark, add to watchlist
- 👥 **Social Watching**: See what friends are watching (public profiles only)
- ⏰ **Episode Reminders**: Get notified when new episodes air
- 📺 **Progress Tracking**: Check watching progress and next episodes
- 🔍 **Show Discovery**: Search and get info about shows/movies

## Setup

1. **Clone and Install**
   ```bash
   git clone <your-repo>
   cd trakt-bot
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
   - Copy `.env.example` to `.env`
   - Fill in your tokens and settings

5. **Run the Bot**
   ```bash
   python noko.py
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