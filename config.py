import os
from dotenv import load_dotenv

load_dotenv()

# Discord settings
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')

# Trakt.tv API settings
TRAKT_CLIENT_ID = os.getenv('TRAKT_CLIENT_ID')
TRAKT_CLIENT_SECRET = os.getenv('TRAKT_CLIENT_SECRET')
TRAKT_REDIRECT_URI = os.getenv('TRAKT_REDIRECT_URI', 'urn:ietf:wg:oauth:2.0:oob')

# Bot settings
BOT_NAME = os.getenv('BOT_NAME', 'Noko')
REMINDER_CHANNEL_ID = os.getenv('REMINDER_CHANNEL_ID')

# Trakt.tv API URLs
TRAKT_BASE_URL = 'https://api.trakt.tv'
TRAKT_AUTH_URL = 'https://trakt.tv/oauth'

# Required for validation
REQUIRED_VARS = [
    'DISCORD_TOKEN',
    'TRAKT_CLIENT_ID',
    'TRAKT_CLIENT_SECRET'
]

def validate_config():
    """Validate that all required environment variables are set."""
    missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    return True 