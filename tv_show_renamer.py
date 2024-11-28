import os
import re
from typing import Dict, List, Optional, Tuple
from tmdbv3api import TMDb, TV, Episode, Search
from dotenv import load_dotenv

class TVShowRenamer:
    def __init__(self):
        """
        Initialize the TVShowRenamer class by loading environment variables,
        setting up the TMDb API, and initializing TV, Search, and Episode objects.
        """
        load_dotenv()
        api_key = os.getenv('TMDB_API_KEY')
        if not api_key:
            raise ValueError("TMDB_API_KEY not found in environment variables")
        
        self.tmdb = TMDb()
        self.tmdb.api_key = api_key
        self.tmdb.language = "en"
        
        self.tv = TV()
        self.search = Search()
        self.episode = Episode()
        self.show_cache: Dict[str, Dict] = {}

    def extract_show_info(self, filename: str) -> Optional[Tuple[str, int, int]]:
        """
        Extract show name, season number, and episode number from filename.
        Returns (show_name, season_number, episode_number) or None if no match.
        """
        # Common TV show filename patterns
        patterns = [
            # Pattern: Show.Name.S01E02
            r"^(.*?)[\. _]S(\d{1,2})E(\d{1,2})",
            # Pattern: Show.Name.1x02
            r"^(.*?)[\. _](\d{1,2})x(\d{1,2})",
            # Pattern: Show.Name.102 (assuming first digit is season, next two are episode)
            r"^(.*?)[\. _](\d{1})(\d{2})\D",
        ]

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                show_name = match.group(1).replace(".", " ").strip()
                season = int(match.group(2))
                episode = int(match.group(3))
                return show_name, season, episode
        
        return None

    def get_show_info(self, show_name: str) -> Optional[Dict]:
        """Get show information from TMDb."""
        if show_name in self.show_cache:
            return self.show_cache[show_name]
        
        try:
            search_results = self.search.tv_shows(term=show_name)
            if not search_results:
                return None
                
            show = search_results[0]  # Get the first (most relevant) result
            show_details = self.tv.details(show.id)
            
            self.show_cache[show_name] = {
                'id': show.id,
                'name': show_details.name,
                'original_name': show_details.original_name
            }
            return self.show_cache[show_name]
        except Exception as e:
            print(f"Error finding show '{show_name}': {e}")
            return None

    def get_episode_info(self, show_id: int, season: int, episode: int) -> Optional[Dict]:
        """Get episode information from TMDb."""
        try:
            details = self.episode.details(show_id, season, episode)
            return {
                'name': details.name,
                'air_date': details.air_date,
                'episode_number': details.episode_number,
                'season_number': details.season_number
            }
        except Exception as e:
            print(f"Error finding episode S{season:02d}E{episode:02d}: {e}")
            return None

    def generate_new_name(self, original_filename: str, template: str = "{show_name} - S{season:02d}E{episode:02d} - {title}") -> Optional[str]:
        """
        Generate new filename based on TMDb information.
        Template variables: {show_name}, {season}, {episode}, {title}
        """
        # Get file extension
        name, ext = os.path.splitext(original_filename)
        
        # Extract show info from filename
        show_info = self.extract_show_info(name)
        if not show_info:
            return None
            
        show_name, season, episode = show_info
        
        # Get show information from TMDb
        show = self.get_show_info(show_name)
        if not show:
            return None
            
        # Get episode information
        episode_info = self.get_episode_info(show['id'], season, episode)
        if not episode_info:
            return None
            
        # Clean episode title
        episode_title = episode_info['name'].replace('/', '-').replace('\\', '-')
        
        # Generate new filename
        new_name = template.format(
            show_name=show['name'],
            season=season,
            episode=episode,
            title=episode_title
        )
        
        # Clean filename of invalid characters
        new_name = re.sub(r'[<>:"/\\|?*]', '-', new_name)
        
        return f"{new_name}{ext}"
