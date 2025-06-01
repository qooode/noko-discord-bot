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
            'settings': {},
            'arena': {
                'participants': {},
                'teams': [],
                'current_challenge': None,
                'active': False,
                'week_start': None,
                'vote_state': {}
            }
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
    
    def add_reminder(self, discord_id: str, show_id: str, show_name: str, hours_before: int = 1, custom_message: str = "") -> bool:
        """Add a reminder for a show with enhanced settings."""
        try:
            if discord_id not in self.data['reminders']:
                self.data['reminders'][discord_id] = {}
            
            self.data['reminders'][discord_id][show_id] = {
                'show_name': show_name,
                'hours_before': hours_before,
                'message': custom_message,
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

    # Arena System Functions
    def get_arena_status(self) -> Dict[str, Any]:
        """Get current arena status."""
        return self.data.get('arena', {
            'participants': {},
            'teams': [],
            'current_challenge': None,
            'active': False
        })
    
    def is_in_arena(self, discord_id: str) -> bool:
        """Check if user is already in arena."""
        arena = self.data.get('arena', {})
        return discord_id in arena.get('participants', {})
    
    def add_arena_participant(self, discord_id: str, trakt_username: str) -> bool:
        """Add user to arena."""
        try:
            if 'arena' not in self.data:
                self.data['arena'] = {
                    'participants': {},
                    'teams': [],
                    'current_challenge': None,
                    'active': False
                }
            
            if discord_id not in self.data['arena']['participants']:
                self.data['arena']['participants'][discord_id] = {
                    'username': trakt_username,
                    'points': 0,
                    'challenges_won': 0,
                    'team': None,
                    'joined_at': datetime.now().isoformat()
                }
                self._save_data()
                return True
        except Exception as e:
            print(f"Error adding arena participant: {e}")
        return False
    
    def get_arena_participants(self) -> List[Dict[str, Any]]:
        """Get all arena participants."""
        arena = self.data.get('arena', {})
        participants = []
        
        for discord_id, participant_data in arena.get('participants', {}).items():
            participant_info = participant_data.copy()
            participant_info['discord_id'] = discord_id
            participants.append(participant_info)
        
        return participants
    
    def create_arena_teams(self, team_size: int) -> List[Dict[str, Any]]:
        """Create balanced teams from participants."""
        try:
            participants = list(self.data['arena']['participants'].keys())
            teams = []
            
            # Create teams
            for i in range(0, len(participants), team_size):
                team_members = participants[i:i + team_size]
                team_name = f"Team {len(teams) + 1}"
                
                team = {
                    'name': team_name,
                    'members': [self.data['arena']['participants'][p]['username'] for p in team_members],
                    'points': 0
                }
                teams.append(team)
                
                # Update participant team assignments
                for member_id in team_members:
                    self.data['arena']['participants'][member_id]['team'] = team_name
            
            self.data['arena']['teams'] = teams
            self._save_data()
            return teams
        except Exception as e:
            print(f"Error creating teams: {e}")
            return []
    
    def get_arena_teams(self) -> List[Dict[str, Any]]:
        """Get current arena teams."""
        arena = self.data.get('arena', {})
        return arena.get('teams', [])
    
    def balance_arena_teams(self, discord_id: str, trakt_username: str) -> str:
        """Add new participant to smallest team."""
        try:
            teams = self.data['arena'].get('teams', [])
            if not teams:
                return "No Team"
            
            # Find smallest team
            smallest_team = min(teams, key=lambda t: len(t['members']))
            team_name = smallest_team['name']
            
            # Add to team
            smallest_team['members'].append(trakt_username)
            self.data['arena']['participants'][discord_id]['team'] = team_name
            
            self._save_data()
            return team_name
        except Exception as e:
            print(f"Error balancing teams: {e}")
            return "No Team"
    
    def rebalance_all_arena_teams(self) -> List[Dict[str, Any]]:
        """Rebalance all teams to be roughly equal."""
        try:
            participants = list(self.data['arena']['participants'].items())
            teams = self.data['arena']['teams']
            
            if not teams:
                return []
            
            # Clear current teams
            for team in teams:
                team['members'] = []
            
            # Redistribute participants
            for i, (discord_id, participant_data) in enumerate(participants):
                team_index = i % len(teams)
                team_name = teams[team_index]['name']
                
                teams[team_index]['members'].append(participant_data['username'])
                self.data['arena']['participants'][discord_id]['team'] = team_name
            
            self._save_data()
            return teams
        except Exception as e:
            print(f"Error rebalancing teams: {e}")
            return []
    
    def set_arena_challenge(self, challenge: Dict[str, Any]) -> bool:
        """Set current arena challenge."""
        try:
            if 'arena' not in self.data:
                self.data['arena'] = {}
            
            self.data['arena']['current_challenge'] = challenge
            self._save_data()
            return True
        except Exception as e:
            print(f"Error setting challenge: {e}")
            return False
    
    def get_arena_challenge(self) -> Optional[Dict[str, Any]]:
        """Get current arena challenge."""
        arena = self.data.get('arena', {})
        return arena.get('current_challenge')
    
    def set_arena_active(self, active: bool) -> bool:
        """Set arena active status."""
        try:
            if 'arena' not in self.data:
                self.data['arena'] = {}
            
            self.data['arena']['active'] = active
            self._save_data()
            return True
        except Exception as e:
            print(f"Error setting arena status: {e}")
            return False
    
    def add_arena_points(self, discord_id: str, points: int) -> bool:
        """Add points to participant."""
        try:
            if discord_id in self.data['arena']['participants']:
                self.data['arena']['participants'][discord_id]['points'] += points
                self._save_data()
                return True
        except Exception as e:
            print(f"Error adding points: {e}")
        return False
    
    def complete_arena_challenge(self, discord_id: str) -> bool:
        """Mark challenge as completed for user."""
        try:
            if discord_id in self.data['arena']['participants']:
                challenge = self.data['arena'].get('current_challenge', {})
                challenge_name = challenge.get('name', 'unknown')
                challenge_end_time = challenge.get('end_time', 0)
                
                # Create unique challenge ID with name and end time
                challenge_id = f"{challenge_name}_{challenge_end_time}"
                
                # Check if already completed this specific challenge instance
                participant = self.data['arena']['participants'][discord_id]
                completed_challenges = participant.get('completed_challenges', [])
                
                if challenge_id in completed_challenges:
                    return False  # Already completed
                
                # Mark as completed
                if 'completed_challenges' not in participant:
                    participant['completed_challenges'] = []
                participant['completed_challenges'].append(challenge_id)
                
                # Add wins and points
                participant['challenges_won'] += 1
                points = challenge.get('points', 10)
                participant['points'] += points
                
                self._save_data()
                return True
        except Exception as e:
            print(f"Error completing challenge: {e}")
        return False
    
    def has_completed_arena_challenge(self, discord_id: str, challenge_name: str) -> bool:
        """Check if user has already completed the current specific challenge instance."""
        try:
            if discord_id in self.data.get('arena', {}).get('participants', {}):
                # Get current challenge end time to create unique ID
                current_challenge = self.data.get('arena', {}).get('current_challenge', {})
                challenge_end_time = current_challenge.get('end_time', 0)
                challenge_id = f"{challenge_name}_{challenge_end_time}"
                
                participant = self.data['arena']['participants'][discord_id]
                completed_challenges = participant.get('completed_challenges', [])
                return challenge_id in completed_challenges
        except Exception as e:
            print(f"Error checking completed challenge: {e}")
        return False
    
    def reset_arena(self) -> bool:
        """Reset entire arena (weekly reset)."""
        try:
            self.data['arena'] = {
                'participants': {},
                'teams': [],
                'current_challenge': None,
                'active': False,
                'week_start': datetime.now().isoformat()
            }
            self._save_data()
            return True
        except Exception as e:
            print(f"Error resetting arena: {e}")
            return False

    # Arena Voting State Management
    def get_arena_vote_state(self) -> Dict[str, Any]:
        """Get current voting state."""
        arena = self.data.get('arena', {})
        return arena.get('vote_state', {})
    
    def save_arena_vote_state(self, vote_state: Dict[str, Any]) -> bool:
        """Save voting state to survive bot restarts."""
        try:
            if 'arena' not in self.data:
                self.data['arena'] = {}
            self.data['arena']['vote_state'] = vote_state
            self._save_data()
            return True
        except Exception as e:
            print(f"Error saving vote state: {e}")
            return False
    
    def clear_arena_vote_state(self) -> bool:
        """Clear voting state after successful vote."""
        try:
            if 'arena' in self.data:
                self.data['arena']['vote_state'] = {}
                self._save_data()
                return True
        except Exception as e:
            print(f"Error clearing vote state: {e}")
            return False
    
    # Arena Exit Mechanisms
    def leave_arena(self, discord_id: str) -> bool:
        """Remove user from arena completely."""
        try:
            arena = self.data.get('arena', {})
            
            # Remove from participants
            if discord_id in arena.get('participants', {}):
                username = arena['participants'][discord_id]['username']
                del arena['participants'][discord_id]
                
                # Remove from teams
                teams = arena.get('teams', [])
                for team in teams:
                    if username in team['members']:
                        team['members'].remove(username)
                
                self._save_data()
                return True
        except Exception as e:
            print(f"Error leaving arena: {e}")
            return False
    
    def get_inactive_participants(self, days_inactive: int = 7) -> List[str]:
        """Get participants who haven't been active recently."""
        # Simple implementation - can be enhanced with actual activity tracking
        arena = self.data.get('arena', {})
        inactive = []
        
        for discord_id, participant in arena.get('participants', {}).items():
            # For now, just return empty list - would need activity tracking
            pass
        
        return inactive
    
    def cleanup_arena_data(self) -> bool:
        """Clean up old challenge data and reset weekly if needed."""
        try:
            arena = self.data.get('arena', {})
            
            # Clear old completed challenges if too many
            for participant in arena.get('participants', {}).values():
                completed = participant.get('completed_challenges', [])
                if len(completed) > 50:  # Keep only last 50
                    participant['completed_challenges'] = completed[-50:]
            
            # Check if weekly reset is needed
            from datetime import datetime, timedelta
            week_start = arena.get('week_start')
            if week_start:
                start_date = datetime.fromisoformat(week_start)
                if datetime.now() - start_date > timedelta(days=7):
                    # Auto weekly reset
                    return self.reset_arena()
            
            self._save_data()
            return True
        except Exception as e:
            print(f"Error cleaning up arena: {e}")
            return False

    def get_challenge_completions(self) -> List[Dict[str, Any]]:
        """Get list of participants who completed the current challenge."""
        try:
            current_challenge = self.data.get('arena', {}).get('current_challenge', {})
            if not current_challenge:
                return []
            
            challenge_name = current_challenge.get('name', '')
            challenge_end_time = current_challenge.get('end_time', 0)
            challenge_id = f"{challenge_name}_{challenge_end_time}"
            
            completions = []
            participants = self.data.get('arena', {}).get('participants', {})
            
            for discord_id, participant in participants.items():
                completed_challenges = participant.get('completed_challenges', [])
                if challenge_id in completed_challenges:
                    completions.append({
                        'discord_id': discord_id,
                        'username': participant['username'],
                        'team': participant.get('team', 'No Team'),
                        'points': participant.get('points', 0),
                        'challenges_won': participant.get('challenges_won', 0)
                    })
            
            return completions
        except Exception as e:
            print(f"Error getting challenge completions: {e}")
            return [] 