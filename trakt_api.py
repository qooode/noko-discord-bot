import requests
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import config

class TraktAPI:
    def __init__(self):
        self.client_id = config.TRAKT_CLIENT_ID
        self.client_secret = config.TRAKT_CLIENT_SECRET
        self.redirect_uri = config.TRAKT_REDIRECT_URI
        self.base_url = config.TRAKT_BASE_URL
        self.auth_url = config.TRAKT_AUTH_URL
        
    def get_headers(self, access_token: Optional[str] = None) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id
        }
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
        return headers
    
    def get_auth_url(self) -> str:
        """Get the authorization URL for OAuth."""
        return f"{self.auth_url}/authorize?response_type=code&client_id={self.client_id}&redirect_uri={self.redirect_uri}"
    
    def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post(f"{self.auth_url}/token", json=data)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error exchanging code for token: {e}")
        return None
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an access token."""
        data = {
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(f"{self.auth_url}/token", json=data)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error refreshing token: {e}")
        return None
    
    def get_user_profile(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user profile information."""
        try:
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=self.get_headers(access_token)
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting user profile: {e}")
        return None
    
    def search_content(self, query: str, content_type: str = 'show,movie') -> List[Dict[str, Any]]:
        """Search for shows/movies."""
        try:
            response = requests.get(
                f"{self.base_url}/search/{content_type}",
                params={'query': query, 'limit': 10},
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error searching content: {e}")
        return []
    
    def get_show_info(self, show_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed show information."""
        try:
            response = requests.get(
                f"{self.base_url}/shows/{show_id}?extended=full",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting show info: {e}")
        return None
    
    def get_movie_info(self, movie_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed movie information."""
        try:
            response = requests.get(
                f"{self.base_url}/movies/{movie_id}?extended=full",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting movie info: {e}")
        return None
    
    def mark_as_watched(self, access_token: str, content_type: str, item_id: str) -> bool:
        """Mark content as watched."""
        if content_type == 'show':
            # For shows, we need to mark episodes as watched
            return self._mark_show_watched(access_token, item_id)
        else:
            # For movies
            return self._mark_movie_watched(access_token, item_id)
    
    def _mark_movie_watched(self, access_token: str, movie_id: str) -> bool:
        """Mark a movie as watched."""
        data = {
            'movies': [{'ids': {'trakt': int(movie_id)}}]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/sync/history",
                json=data,
                headers=self.get_headers(access_token)
            )
            return response.status_code == 201
        except Exception as e:
            print(f"Error marking movie as watched: {e}")
        return False
    
    def _mark_show_watched(self, access_token: str, show_id: str) -> bool:
        """Mark all episodes of a show as watched."""
        data = {
            'shows': [{'ids': {'trakt': int(show_id)}}]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/sync/history",
                json=data,
                headers=self.get_headers(access_token)
            )
            return response.status_code == 201
        except Exception as e:
            print(f"Error marking show as watched: {e}")
        return False
    
    def unmark_as_watched(self, access_token: str, content_type: str, item_id: str) -> bool:
        """Remove content from watched history."""
        if content_type == 'show':
            data = {'shows': [{'ids': {'trakt': int(item_id)}}]}
        else:
            data = {'movies': [{'ids': {'trakt': int(item_id)}}]}
        
        try:
            response = requests.post(
                f"{self.base_url}/sync/history/remove",
                json=data,
                headers=self.get_headers(access_token)
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error unmarking as watched: {e}")
        return False
    
    def add_to_watchlist(self, access_token: str, content_type: str, item_id: str) -> bool:
        """Add content to watchlist."""
        if content_type == 'show':
            data = {'shows': [{'ids': {'trakt': int(item_id)}}]}
        else:
            data = {'movies': [{'ids': {'trakt': int(item_id)}}]}
        
        try:
            response = requests.post(
                f"{self.base_url}/sync/watchlist",
                json=data,
                headers=self.get_headers(access_token)
            )
            return response.status_code == 201
        except Exception as e:
            print(f"Error adding to watchlist: {e}")
        return False
    
    def get_watching_now(self, username: str) -> Optional[Dict[str, Any]]:
        """Get what a user is currently watching."""
        try:
            response = requests.get(
                f"{self.base_url}/users/{username}/watching",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting current watching: {e}")
        return None
    
    def get_user_history(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's watch history."""
        try:
            response = requests.get(
                f"{self.base_url}/users/{username}/history",
                params={'limit': limit},
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting user history: {e}")
        return []
    
    def get_user_progress(self, username: str) -> List[Dict[str, Any]]:
        """Get user's show progress."""
        try:
            response = requests.get(
                f"{self.base_url}/users/{username}/watched/shows?extended=full",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting user progress: {e}")
        return []
    
    def get_calendar(self, username: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming episodes for user."""
        start_date = datetime.now().strftime('%Y-%m-%d')
        try:
            response = requests.get(
                f"{self.base_url}/users/{username}/calendar/shows/{start_date}/{days}",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting calendar: {e}")
        return [] 