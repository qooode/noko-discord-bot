import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

class Database:
    def __init__(self, db_file: str = 'users.json'):
        self.db_file = db_file
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file."""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {
            'users': {},
            'reminders': {},
            'settings': {}
        }
    
    def _save_data(self):
        """Save data to JSON file."""
        try:
            with open(self.db_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def add_user(self, discord_id: str, trakt_username: str, access_token: str, 
                 refresh_token: str, is_public: bool = False) -> bool:
        """Add or update user data."""
        try:
            self.data['users'][discord_id] = {
                'trakt_username': trakt_username,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'is_public': is_public,
                'connected_at': datetime.now().isoformat()
            }
            self._save_data()
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    def get_user(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """Get user data by Discord ID."""
        return self.data['users'].get(discord_id)
    
    def update_user_tokens(self, discord_id: str, access_token: str, refresh_token: str) -> bool:
        """Update user's access and refresh tokens."""
        try:
            if discord_id in self.data['users']:
                self.data['users'][discord_id]['access_token'] = access_token
                self.data['users'][discord_id]['refresh_token'] = refresh_token
                self._save_data()
                return True
        except Exception as e:
            print(f"Error updating tokens: {e}")
        return False
    
    def set_user_privacy(self, discord_id: str, is_public: bool) -> bool:
        """Set user's privacy setting."""
        try:
            if discord_id in self.data['users']:
                self.data['users'][discord_id]['is_public'] = is_public
                self._save_data()
                return True
        except Exception as e:
            print(f"Error setting privacy: {e}")
        return False
    
    def get_public_users(self) -> List[Dict[str, Any]]:
        """Get all users with public profiles."""
        data = self._load_data()
        public_users = []
        
        for user_id, user_data in data['users'].items():
            if user_data.get('is_public', False):
                public_users.append({
                    'discord_id': user_id,
                    'trakt_username': user_data['trakt_username'],
                    'access_token': user_data.get('access_token', ''),
                    'connected_at': user_data.get('connected_at', '')
                })
        
        return public_users
    
    def get_user_count(self) -> Dict[str, int]:
        """Get user statistics."""
        data = self._load_data()
        total_users = len(data['users'])
        public_users = len([u for u in data['users'].values() if u.get('is_public', False)])
        
        return {
            'total': total_users,
            'public': public_users,
            'private': total_users - public_users
        }
    
    def add_reminder(self, discord_id: str, show_id: str, show_name: str) -> bool:
        """Add a reminder for a show."""
        try:
            if discord_id not in self.data['reminders']:
                self.data['reminders'][discord_id] = {}
            
            self.data['reminders'][discord_id][show_id] = {
                'show_name': show_name,
                'added_at': datetime.now().isoformat()
            }
            self._save_data()
            return True
        except Exception as e:
            print(f"Error adding reminder: {e}")
            return False
    
    def remove_reminder(self, discord_id: str, show_id: str) -> bool:
        """Remove a reminder for a show."""
        try:
            if (discord_id in self.data['reminders'] and 
                show_id in self.data['reminders'][discord_id]):
                del self.data['reminders'][discord_id][show_id]
                if not self.data['reminders'][discord_id]:
                    del self.data['reminders'][discord_id]
                self._save_data()
                return True
        except Exception as e:
            print(f"Error removing reminder: {e}")
        return False
    
    def get_user_reminders(self, discord_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all reminders for a user."""
        return self.data['reminders'].get(discord_id, {})
    
    def get_all_reminders(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get all reminders for all users."""
        return self.data['reminders']
    
    def find_user_by_trakt_username(self, trakt_username: str) -> Optional[str]:
        """Find Discord ID by Trakt username."""
        for discord_id, user_data in self.data['users'].items():
            if user_data.get('trakt_username') == trakt_username:
                return discord_id
        return None
    
    def get_user_by_mention(self, mention: str) -> Optional[Dict[str, Any]]:
        """Get user data by Discord mention (@user)."""
        # Remove @ and < > from mention
        user_id = mention.strip('<@!>')
        return self.get_user(user_id) 