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
        """Search for shows/movies with extended information including images."""
        try:
            response = requests.get(
                f"{self.base_url}/search/{content_type}",
                params={'query': query, 'limit': 10, 'extended': 'full'},
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error searching content: {e}")
        return []
    
    def get_show_info(self, show_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed show information with images."""
        try:
            response = requests.get(
                f"{self.base_url}/shows/{show_id}?extended=full",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                show_data = response.json()
                
                # Get images for the show
                images_response = requests.get(
                    f"https://api.themoviedb.org/3/tv/{show_data.get('ids', {}).get('tmdb')}?api_key=YOUR_TMDB_KEY&append_to_response=images",
                    headers={'Content-Type': 'application/json'}
                )
                
                # For now, we'll use a simpler approach - construct image URLs
                if show_data.get('ids', {}).get('tmdb'):
                    tmdb_id = show_data['ids']['tmdb']
                    show_data['poster_url'] = f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg"  # This is a simplified approach
                
                return show_data
        except Exception as e:
            print(f"Error getting show info: {e}")
        return None
    
    def get_movie_info(self, movie_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed movie information with images."""
        try:
            response = requests.get(
                f"{self.base_url}/movies/{movie_id}?extended=full",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                movie_data = response.json()
                
                # Add poster URL if TMDB ID is available
                if movie_data.get('ids', {}).get('tmdb'):
                    tmdb_id = movie_data['ids']['tmdb']
                    movie_data['poster_url'] = f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg"
                
                return movie_data
        except Exception as e:
            print(f"Error getting movie info: {e}")
        return None
    
    def get_content_images(self, content_type: str, tmdb_id: int) -> Dict[str, str]:
        """Get image URLs for content using TMDB ID."""
        images = {}
        try:
            # Using fanart.tv API patterns for common poster locations
            # This is a simplified approach - in production you'd want proper TMDB API integration
            base_url = "https://image.tmdb.org/t/p"
            
            images['poster_small'] = f"{base_url}/w300/{tmdb_id}.jpg"
            images['poster_medium'] = f"{base_url}/w500/{tmdb_id}.jpg" 
            images['poster_large'] = f"{base_url}/w780/{tmdb_id}.jpg"
            images['backdrop'] = f"{base_url}/w1280/{tmdb_id}.jpg"
            
        except Exception as e:
            print(f"Error getting images: {e}")
        
        return images
    
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
    
    def get_show_seasons(self, show_id: str) -> List[Dict[str, Any]]:
        """Get all seasons for a show with episode counts."""
        try:
            response = requests.get(
                f"{self.base_url}/shows/{show_id}/seasons?extended=episodes",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting show seasons: {e}")
        return []
    
    def get_season_episodes(self, show_id: str, season_number: int) -> List[Dict[str, Any]]:
        """Get all episodes for a specific season."""
        try:
            response = requests.get(
                f"{self.base_url}/shows/{show_id}/seasons/{season_number}?extended=full",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting season episodes: {e}")
        return []
    
    def get_show_progress(self, access_token: str, show_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed watching progress for a show."""
        try:
            url = f"{self.base_url}/shows/{show_id}/progress/watched"
            headers = self.get_headers(access_token)
            
            print(f"Getting progress for show {show_id} from {url}")
            
            response = requests.get(url, headers=headers)
            
            print(f"Progress response: {response.status_code}")
            
            if response.status_code == 200:
                progress_data = response.json()
                print(f"Progress data keys: {list(progress_data.keys())}")
                return progress_data
            elif response.status_code == 404:
                print(f"Show {show_id} not found or no progress data")
                return None
            elif response.status_code == 401:
                print(f"Authentication failed for show progress")
                return None
            else:
                print(f"Unexpected status code {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting show progress: {e}")
            return None
    
    def mark_episode_watched(self, access_token: str, show_id: str, season: int, episode: int) -> bool:
        """Mark a specific episode as watched."""
        data = {
            'shows': [{
                'ids': {'trakt': int(show_id)},
                'seasons': [{
                    'number': season,
                    'episodes': [{
                        'number': episode
                    }]
                }]
            }]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/sync/history",
                json=data,
                headers=self.get_headers(access_token)
            )
            print(f"Mark episode response: {response.status_code}, {response.text}")
            return response.status_code == 201
        except Exception as e:
            print(f"Error marking episode as watched: {e}")
        return False
    
    def mark_season_watched(self, access_token: str, show_id: str, season: int) -> bool:
        """Mark an entire season as watched."""
        data = {
            'shows': [{
                'ids': {'trakt': int(show_id)},
                'seasons': [{
                    'number': season
                }]
            }]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/sync/history",
                json=data,
                headers=self.get_headers(access_token)
            )
            print(f"Mark season response: {response.status_code}, {response.text}")
            return response.status_code == 201
        except Exception as e:
            print(f"Error marking season as watched: {e}")
        return False
    
    def unmark_episode_watched(self, access_token: str, show_id: str, season: int, episode: int) -> bool:
        """Unmark a specific episode as watched."""
        data = {
            'shows': [{
                'ids': {'trakt': int(show_id)},
                'seasons': [{
                    'number': season,
                    'episodes': [{
                        'number': episode
                    }]
                }]
            }]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/sync/history/remove",
                json=data,
                headers=self.get_headers(access_token)
            )
            print(f"Unmark episode response: {response.status_code}, {response.text}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error unmarking episode: {e}")
        return False
    
    def unmark_season_watched(self, access_token: str, show_id: str, season: int) -> bool:
        """Unmark an entire season as watched."""
        data = {
            'shows': [{
                'ids': {'trakt': int(show_id)},
                'seasons': [{
                    'number': season
                }]
            }]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/sync/history/remove",
                json=data,
                headers=self.get_headers(access_token)
            )
            print(f"Unmark season response: {response.status_code}, {response.text}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error unmarking season: {e}")
        return False 