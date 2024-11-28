import os
import re
import time
from typing import Dict, List, Optional, Tuple
from tmdbv3api import TMDb, TV, Episode, Search
from dotenv import load_dotenv
from src.utils.logger import setup_logger, log_safely, format_show_name


class TVShowRenamer:
    def __init__(self, parent):
        """
        Initialize the TVShowRenamer class by loading environment variables,
        setting up the TMDb API, and initializing TV, Search, and Episode objects.
        """
        self.parent = parent
        load_dotenv()
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            raise ValueError("TMDB_API_KEY not found in environment variables")

        # Set up secure logging
        self.logger = setup_logger(__name__)

        self.tmdb = TMDb()
        self.tmdb.api_key = api_key
        self.tmdb.language = "en"

        self.tv = TV()
        self.search = Search()
        self.episode = Episode()
        self.show_cache: Dict[str, Dict] = {}
        self.season_cache = {}
        self.episode_cache = {}
        self.search_cache = {}

        # Add API call counters
        self.api_call_count = {
            'search': 0,
            'show_details': 0,
            'season_details': 0,
            'episode_details': 0
        }
        
        # Add cache hit counters
        self.cache_hits = {
            'show': 0,
            'season': 0,
            'episode': 0,
            'search': 0
        }

        self.performance_stats = {
            'api_times': [],
            'cache_times': []
        }

    def measure_performance(func):
        """Decorator to measure function execution time"""
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            result = func(self, *args, **kwargs)
            end_time = time.time()
            
            # Store timing based on whether it was a cache hit
            if result and any(hit > 0 for hit in self.cache_hits.values()):
                self.performance_stats['cache_times'].append(end_time - start_time)
            else:
                self.performance_stats['api_times'].append(end_time - start_time)
            
            return result
        return wrapper

    @log_safely
    def extract_show_info(self, filename: str) -> Optional[Tuple[str, int, int]]:
        """
        Extract show name, season number, and episode number from filename.
        Searches TMDB for best show name match.
        Returns (show_name, season_number, episode_number) or None if no match.
        """
        self.logger.debug(f"Extracting show info from filename: {filename}")

        # Special handling for episode-only format with show title
        episode_only_pattern = r"^(\d{1,2})[\. _]-[\. _](.*?)(?:\[.*?\])*\..*$"
        match = re.search(episode_only_pattern, filename, re.IGNORECASE)
        if match:
            try:
                episode_num = int(match.group(1))
                show_title = match.group(2).strip()

                # Try to find season number in the title
                season_match = re.search(
                    r"season[\. _](\d+)", show_title, re.IGNORECASE
                )
                if season_match:
                    season_num = int(season_match.group(1))
                else:
                    # If no season found in title, get it from the current show context
                    if hasattr(self, "current_season") and self.current_season:
                        season_num = self.current_season
                    else:
                        self.logger.warning(
                            f"No season information found for: {filename}"
                        )
                        return None

                # Remove any remaining tags in square brackets
                show_title = re.sub(r"\[.*?\]", "", show_title).strip()
                # Clean up the show title
                show_title = show_title.split("-")[0].strip()

                self.logger.debug(
                    f"Matched episode-only format: Show='{show_title}', S{season_num:02d}E{episode_num:02d}"
                )
                return show_title, season_num, episode_num

            except (IndexError, ValueError) as e:
                self.logger.error(f"Error parsing episode-only format: {e}")
                return None

        # Common TV show filename patterns
        patterns = [
            # Pattern: Show.Name.S01E02 or Show.Name.S1E02
            r"^(.*?)[\. _]S0?(\d{1,2})E(\d{1,2})",
            # Pattern: Show.Name.1x02 or Show.Name.01x02
            r"^(.*?)[\. _]0?(\d{1,2})x(\d{1,2})",
            # Pattern: Show.Name.102 (assuming first digit is season, next two are episode)
            r"^(.*?)[\. _](\d{1})(\d{2})\D",
            # Pattern: Show.Name.Season.1.Episode.02
            r"^(.*?)[\. _]Season[\. _]0?(\d{1,2})[\. _]Episode[\. _](\d{1,2})",
            # Pattern: Show.Name.E02.S01
            r"^(.*?)[\. _]E(\d{1,2})[\. _]S0?(\d{1,2})",
        ]

        # Try standard patterns
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                try:
                    raw_show_name = match.group(1).replace(".", " ").strip()
                    season = int(match.group(2))
                    episode = int(match.group(3))

                    # Clean up show name
                    show_name = re.sub(r"\[.*?\]", "", raw_show_name).strip()
                    show_name = show_name.split("-")[0].strip()

                    self.logger.info(
                        f"Matched: Show='{show_name}', S{season:02d}E{episode:02d}"
                    )
                    return show_name, season, episode

                except (IndexError, ValueError) as e:
                    self.logger.error(f"Error parsing filename '{filename}': {e}")
                    continue

        self.logger.warning(f"No pattern matched for filename: {filename}")
        return None

    def get_stats(self):
        """Get API and cache statistics"""
        total_calls = sum(self.api_call_count.values())
        total_hits = sum(self.cache_hits.values())
        
        return {
            'api_calls': self.api_call_count,
            'cache_hits': self.cache_hits,
            'total_calls': total_calls,
            'total_hits': total_hits,
            'cache_hit_rate': f"{(total_hits / (total_calls + total_hits) * 100):.2f}%" if total_calls + total_hits > 0 else "0%"
        }

    @measure_performance
    def get_show_info(self, show_name: str) -> Optional[Dict]:
        """Get show information from TMDb with caching."""
        cache_key = show_name.lower()
        if cache_key in self.show_cache:
            self.cache_hits['show'] += 1
            self.logger.debug(f"Cache hit for show: {show_name}")
            return self.show_cache[cache_key]

        try:
            self.api_call_count['search'] += 1
            # Cache miss - fetch from API
            self.logger.debug(f"Cache miss for show: {show_name}")
            search_results = self.search.tv_shows(term=show_name)
            if not search_results:
                return None

            show = search_results[0]
            show_details = self.tv.details(show.id)

            # Store in cache
            show_data = {
                "id": show.id,
                "name": show_details.name,
                "original_name": show_details.original_name,
                "first_air_date": getattr(show_details, 'first_air_date', None),
                "overview": getattr(show_details, 'overview', '')[:200]  # Limit overview length
            }
            self.show_cache[cache_key] = show_data
            return show_data

        except Exception as e:
            self.logger.error(f"Error finding show '{show_name}': {str(e)}")
            return None

    def get_episode_info(self, show_id: int, season: int, episode: int) -> Optional[Dict]:
        """Get episode information from TMDb with caching."""
        cache_key = f"{show_id}_{season}_{episode}"
        if cache_key in self.episode_cache:
            self.cache_hits['episode'] += 1
            self.logger.debug(f"Cache hit for episode: {cache_key}")
            return self.episode_cache[cache_key]

        try:
            self.api_call_count['episode_details'] += 1
            # Cache miss - fetch from API
            self.logger.debug(f"Cache miss for episode: {cache_key}")
            details = self.episode.details(show_id, season, episode)
            
            # Store minimal data in cache
            episode_data = {
                "name": details.name,
                "air_date": getattr(details, 'air_date', None),
                "episode_number": details.episode_number,
                "season_number": details.season_number,
                "overview": getattr(details, 'overview', '')[:200]  # Limit overview length
            }
            self.episode_cache[cache_key] = episode_data
            return episode_data

        except Exception as e:
            self.logger.error(f"Error finding episode S{season:02d}E{episode:02d}: {e}")
            return None

    def get_season_details(self, show_id: int, season_num: int) -> Optional[Dict]:
        """Get season details with caching."""
        cache_key = f"{show_id}_{season_num}"
        if cache_key in self.season_cache:
            self.cache_hits['season'] += 1
            self.logger.debug(f"Cache hit for season: {cache_key}")
            return self.season_cache[cache_key]

        try:
            self.api_call_count['season_details'] += 1
            # Cache miss - fetch from API
            self.logger.debug(f"Cache miss for season: {cache_key}")
            season = self.tv.season(show_id, season_num)
            
            # Store minimal data in cache
            season_data = {
                "episodes": [
                    {
                        "episode_number": ep.episode_number,
                        "name": ep.name,
                        "air_date": getattr(ep, 'air_date', None)
                    }
                    for ep in season.episodes
                ]
            }
            self.season_cache[cache_key] = season_data
            return season_data

        except Exception as e:
            self.logger.error(f"Error getting season details: {e}")
            return None

    def generate_new_name(
        self, original_name: str, show_id: int = None
    ) -> Optional[str]:
        """Generate new name for the file based on TV show information."""
        if not show_id:
            return None

        # Extract season and episode numbers from filename
        show_info = self.extract_show_info(original_name)
        if not show_info:
            return None

        _, season_num, episode_num = show_info

        try:
            # Get episode information directly using get_episode_info
            episode_info = self.get_episode_info(show_id, season_num, episode_num)
            if not episode_info:
                return None

            # Create new filename with consistent casing
            extension = os.path.splitext(original_name)[1]
            show_name = format_show_name(show_info[0])
            episode_name = format_show_name(episode_info["name"])
            new_name = f"{show_name}-S{season_num:02d}E{episode_num:02d}-{episode_name}{extension}"
            return self.sanitize_filename(new_name)

        except Exception as e:
            self.logger.error(f"Error getting episode info: {e}")
            return None

    def sanitize_filename(self, filename: str) -> str:
        """Remove invalid characters from filename."""
        # Replace invalid characters with underscore
        invalid_chars = r'[<>:"/\\|?*]'
        return re.sub(invalid_chars, "_", filename)

    @log_safely
    def extract_episode_number(self, filename: str) -> Optional[int]:
        """Extract episode number from filename."""
        # Patterns to match episode numbers
        patterns = [
            r"E(\d{1,2})",  # Match E01, E1, etc.
            r"^(\d{1,2})[\. _]-",  # Match episode numbers at start (e.g., "01 - ")
            r"x(\d{1,2})",  # Match 1x01 format
            r"(\d{2})(?=\D|$)",  # Match two digits followed by non-digit or end
        ]

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                try:
                    episode_num = int(match.group(1))
                    self.logger.debug(f"Found episode number: {episode_num}")
                    return episode_num
                except (IndexError, ValueError) as e:
                    self.logger.error(f"Error parsing episode number: {e}")
                    continue

        self.logger.warning(f"No episode number found in filename: {filename}")
        return None

    def get_performance_stats(self):
        """Get performance statistics"""
        api_times = self.performance_stats['api_times']
        cache_times = self.performance_stats['cache_times']
        
        return {
            'avg_api_time': f"{sum(api_times) / len(api_times):.3f}s" if api_times else "N/A",
            'avg_cache_time': f"{sum(cache_times) / len(cache_times):.3f}s" if cache_times else "N/A",
            'total_api_time': f"{sum(api_times):.3f}s",
            'total_cache_time': f"{sum(cache_times):.3f}s",
            'api_calls_count': len(api_times),
            'cache_hits_count': len(cache_times)
        }
