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
    
    def get_user_history_authenticated(self, access_token: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get authenticated user's watch history with extended data."""
        try:
            response = requests.get(
                f"{self.base_url}/users/me/history",
                params={'limit': limit, 'extended': 'full'},
                headers=self.get_headers(access_token)
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting authenticated user history: {e}")
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
    
    def get_calendar(self, username: str, days: int = 7, access_token: str = None) -> List[Dict[str, Any]]:
        """Get upcoming episodes for user (requires authentication for personal calendar)."""
        start_date = datetime.now().strftime('%Y-%m-%d')
        try:
            if access_token:
                # Use authenticated endpoint for personal calendar
                response = requests.get(
                    f"{self.base_url}/calendars/my/shows/{start_date}/{days}",
                    headers=self.get_headers(access_token)
                )
            else:
                # Fallback to public endpoint (may have limited data)
                response = requests.get(
                    f"{self.base_url}/users/{username}/calendar/shows/{start_date}/{days}",
                    headers=self.get_headers()
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Calendar API returned {response.status_code}: {response.text}")
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
    
    def validate_arena_challenge(self, access_token: str, challenge: Dict[str, Any], challenge_start_time: float) -> Dict[str, Any]:
        """Validate if user completed arena challenge based on their Trakt history."""
        try:
            # Get recent watch history since challenge started
            history = self.get_user_history_authenticated(access_token, 50)
            
            if not history:
                return {'valid': False, 'reason': 'Unable to fetch watch history from Trakt'}
            
            # Filter to movies watched after challenge started
            challenge_movies = []
            for item in history:
                if item.get('action') == 'watch' and item.get('type') == 'movie':
                    try:
                        # Parse watch time with better error handling
                        watched_at_str = item.get('watched_at', '')
                        if not watched_at_str:
                            continue
                        
                        # Handle different timezone formats
                        if watched_at_str.endswith('Z'):
                            watched_at_str = watched_at_str.replace('Z', '+00:00')
                        
                        watched_at = datetime.fromisoformat(watched_at_str)
                        if watched_at.timestamp() >= challenge_start_time:
                            challenge_movies.append(item)
                    except (ValueError, TypeError) as e:
                        print(f"Error parsing watch time for item: {e}")
                        continue
            
            if not challenge_movies:
                return {'valid': False, 'reason': 'No movies watched since challenge started'}
            
            # Check each movie against challenge criteria
            for movie_item in challenge_movies:
                movie = movie_item.get('movie', {})
                
                # If basic movie data is missing detailed info, fetch it
                if not self._has_extended_data(movie):
                    movie = self._fetch_extended_movie_data(movie)
                
                if movie and self._movie_matches_challenge(movie, challenge):
                    return {
                        'valid': True,
                        'movie': movie,
                        'watched_at': movie_item['watched_at']
                    }
            
            return {'valid': False, 'reason': 'No movies found that match the challenge criteria'}
            
        except Exception as e:
            print(f"Error validating arena challenge: {e}")
            return {'valid': False, 'reason': f'Validation system error. Please try again in a few minutes.'}

    def _has_extended_data(self, movie: Dict[str, Any]) -> bool:
        """Check if movie has the extended data needed for validation."""
        required_fields = ['genres', 'rating', 'runtime', 'language', 'votes']
        return any(field in movie for field in required_fields)

    def _fetch_extended_movie_data(self, movie: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetch extended movie data if not available in history."""
        try:
            movie_ids = movie.get('ids', {})
            trakt_id = movie_ids.get('trakt')
            
            if trakt_id:
                return self.get_movie_info(str(trakt_id))
        except Exception as e:
            print(f"Error fetching extended movie data: {e}")
        
        return movie  # Return original if fetch fails

    def _movie_matches_challenge(self, movie: Dict[str, Any], challenge: Dict[str, Any]) -> bool:
        """Check if a movie matches the challenge criteria with robust error handling."""
        try:
            challenge_type = challenge.get('type')
            target = challenge.get('target')
            
            if not challenge_type or target is None:
                return False
            
            if challenge_type == 'genre':
                genres = movie.get('genres', [])
                if not genres:
                    return False
                genre_names = [g.lower() if isinstance(g, str) else str(g).lower() for g in genres]
                return target.lower() in genre_names
                
            elif challenge_type == 'decade':
                year = movie.get('year')
                if not isinstance(year, int) or year <= 0:
                    return False
                    
                if target == '1990s':
                    return 1990 <= year <= 1999
                elif target == '1980s':
                    return 1980 <= year <= 1989
                elif target == '2000s':
                    return 2000 <= year <= 2009
                elif target == '2010s':
                    return 2010 <= year <= 2019
                elif target == '2020s':
                    return 2020 <= year <= 2029
                    
            elif challenge_type == 'rating':
                rating = movie.get('rating')
                if rating is None or not isinstance(rating, (int, float)):
                    return False
                return float(rating) >= target
                
            elif challenge_type == 'runtime':
                runtime = movie.get('runtime')
                if runtime is None or not isinstance(runtime, (int, float)):
                    return False
                return int(runtime) < target  # For "under X minutes" challenges
                
            elif challenge_type == 'classic':
                year = movie.get('year')
                if not isinstance(year, int) or year <= 0:
                    return False
                return year < target
                
            elif challenge_type == 'language':
                language = movie.get('language', '').lower()
                if target == 'non-english':
                    return language != 'en' and language != ''
                else:
                    return language == target.lower()
                    
            elif challenge_type == 'obscure':
                votes = movie.get('votes')
                if votes is None or not isinstance(votes, (int, float)):
                    return False
                return int(votes) < target
                
        except Exception as e:
            print(f"Error in movie matching: {e}")
            return False
            
        return False

    def debug_recent_movies(self, access_token: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Debug method to see what movie data is available for validation."""
        try:
            history = self.get_user_history_authenticated(access_token, limit)
            debug_info = []
            
            for item in history:
                if item.get('action') == 'watch' and item.get('type') == 'movie':
                    movie = item.get('movie', {})
                    
                    # Get extended data if needed
                    if not self._has_extended_data(movie):
                        movie = self._fetch_extended_movie_data(movie)
                    
                    debug_info.append({
                        'title': movie.get('title', 'Unknown'),
                        'year': movie.get('year'),
                        'watched_at': item.get('watched_at'),
                        'has_genres': bool(movie.get('genres')),
                        'genres': movie.get('genres', []),
                        'has_rating': movie.get('rating') is not None,
                        'rating': movie.get('rating'),
                        'has_runtime': movie.get('runtime') is not None,
                        'runtime': movie.get('runtime'),
                        'has_language': bool(movie.get('language')),
                        'language': movie.get('language'),
                        'has_votes': movie.get('votes') is not None,
                        'votes': movie.get('votes')
                    })
            
            return debug_info
        except Exception as e:
            print(f"Error in debug method: {e}")
            return []

    def get_user_watchlist(self, access_token: str) -> List[Dict[str, Any]]:
        """Get user's watchlist with authentication."""
        try:
            response = requests.get(
                f"{self.base_url}/users/me/watchlist",
                params={'extended': 'full'},
                headers=self.get_headers(access_token)
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Watchlist API returned {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Error getting user watchlist: {e}")
        return []
    
    def get_popular_movies(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get popular movies from Trakt."""
        try:
            response = requests.get(
                f"{self.base_url}/movies/popular",
                params={'limit': limit, 'extended': 'full'},
                headers=self.get_headers()
            )
            if response.status_code == 200:
                movies_data = response.json()
                # Convert to search result format for consistency
                return [{'movie': movie} for movie in movies_data]
        except Exception as e:
            print(f"Error getting popular movies: {e}")
        return []
    
    def get_popular_shows(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get popular shows from Trakt."""
        try:
            response = requests.get(
                f"{self.base_url}/shows/popular", 
                params={'limit': limit, 'extended': 'full'},
                headers=self.get_headers()
            )
            if response.status_code == 200:
                shows_data = response.json()
                # Convert to search result format for consistency
                return [{'show': show} for show in shows_data]
        except Exception as e:
            print(f"Error getting popular shows: {e}")
        return [] 