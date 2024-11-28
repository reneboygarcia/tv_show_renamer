import tkinter as tk
from tkinter import ttk
from tmdbv3api import TMDb, TV, Season
from dotenv import load_dotenv
import os
from src.utils.logger import setup_logger, log_safely, format_show_name


class ShowInputDialog:
    def __init__(self, parent):
        # Initialize TMDb
        load_dotenv()
        self.tmdb = TMDb()
        self.tmdb.api_key = os.getenv("TMDB_API_KEY")
        self.tv = TV()
        self.season_api = Season()
        self.logger = setup_logger(__name__)

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("TV Show Search")
        self.dialog.geometry("800x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.center_window()

        # Selected data
        self.selected_show = None
        self.selected_season = None
        self.selected_episode = None
        self.shows_dict = {}
        self.seasons_dict = {}
        self.episodes_dict = {}

        self.create_widgets()

    def center_window(self):
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def create_widgets(self):
        # Main container with padding
        main_container = ttk.Frame(self.dialog, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Search frame
        search_frame = ttk.LabelFrame(main_container, text="Search Show", padding="5")
        search_frame.pack(fill=tk.X, pady=(0, 10))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10))

        search_btn = ttk.Button(search_frame, text="Search", command=self.search_shows)
        search_btn.pack(side=tk.RIGHT)

        # Create a frame for lists with equal column weights
        lists_frame = ttk.Frame(main_container)
        lists_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Configure grid weights for equal column distribution
        for i in range(3):
            lists_frame.columnconfigure(i, weight=1)
        lists_frame.rowconfigure(1, weight=1)

        # Shows list with label and frame
        ttk.Label(lists_frame, text="Shows").grid(row=0, column=0, sticky="w", padx=5)
        shows_frame = ttk.Frame(lists_frame)
        shows_frame.grid(row=1, column=0, sticky="nsew", padx=5)

        self.shows_list = tk.Listbox(shows_frame, exportselection=0)
        shows_scroll = ttk.Scrollbar(shows_frame, orient="vertical", command=self.shows_list.yview)
        self.shows_list.configure(yscrollcommand=shows_scroll.set)
        shows_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.shows_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Seasons list with label and frame
        ttk.Label(lists_frame, text="Seasons").grid(row=0, column=1, sticky="w", padx=5)
        seasons_frame = ttk.Frame(lists_frame)
        seasons_frame.grid(row=1, column=1, sticky="nsew", padx=5)

        self.seasons_list = tk.Listbox(seasons_frame, exportselection=0)
        seasons_scroll = ttk.Scrollbar(seasons_frame, orient="vertical", command=self.seasons_list.yview)
        self.seasons_list.configure(yscrollcommand=seasons_scroll.set)
        seasons_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.seasons_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Episodes list with label and frame
        ttk.Label(lists_frame, text="Episodes").grid(row=0, column=2, sticky="w", padx=5)
        episodes_frame = ttk.Frame(lists_frame)
        episodes_frame.grid(row=1, column=2, sticky="nsew", padx=5)

        self.episodes_list = tk.Listbox(episodes_frame, exportselection=0)
        episodes_scroll = ttk.Scrollbar(episodes_frame, orient="vertical", command=self.episodes_list.yview)
        self.episodes_list.configure(yscrollcommand=episodes_scroll.set)
        episodes_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.episodes_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Show info frame
        info_frame = ttk.LabelFrame(main_container, text="Show Information", padding="5")
        info_frame.pack(fill=tk.X, pady=10)

        self.info_text = tk.Text(info_frame, height=4, wrap=tk.WORD)
        self.info_text.pack(fill=tk.X, padx=5, pady=5)
        self.info_text.config(state=tk.DISABLED)

        # Buttons frame
        buttons_frame = ttk.Frame(main_container)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(buttons_frame, text="Select", command=self.select_show).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT)

        # Bind events with proper event handling
        self.search_entry.bind("<Return>", lambda e: self.search_shows())
        self.shows_list.bind("<<ListboxSelect>>", self.on_show_select)
        self.seasons_list.bind("<<ListboxSelect>>", self.on_season_select)
        self.episodes_list.bind("<<ListboxSelect>>", self.on_episode_select)

        # Set focus to search entry
        self.search_entry.focus_set()

    def search_shows(self):
        query = self.search_var.get().strip()
        if not query:
            return

        self.shows_list.delete(0, tk.END)
        self.seasons_list.delete(0, tk.END)
        self.episodes_list.delete(0, tk.END)
        self.shows_dict.clear()
        self.seasons_dict.clear()
        self.episodes_dict.clear()
        self.update_info("")

        try:
            # Get search results with pagination and limit
            page = 1
            shows = self.tv.search(query, page=page)
            
            # Only process first 10 shows for better performance
            for i, show in enumerate(shows):
                if i >= 10:  # Limit to first 10 results
                    break
                    
                # Only store essential data
                show_data = {
                    'id': show.id,
                    'name': show.name,
                    'first_air_date': getattr(show, 'first_air_date', 'N/A'),
                    'overview': getattr(show, 'overview', '')[:200]  # Limit overview length
                }
                
                show_name = format_show_name(show_data['name'])
                year = show_data['first_air_date'][:4] if show_data['first_air_date'] != 'N/A' else 'N/A'
                display_text = f"{show_name} ({year})"
                
                self.shows_list.insert(tk.END, display_text)
                self.shows_dict[display_text] = show  # Keep original show object for compatibility
                
        except Exception as e:
            self.logger.error(f"Error searching shows: {str(e)}")
            self.shows_list.insert(tk.END, f"Error: {str(e)}")

    def on_show_select(self, event):
        selection = self.shows_list.curselection()
        if not selection:
            return

        display_text = self.shows_list.get(selection[0])
        show = self.shows_dict.get(display_text)
        if not show:
            return

        # Update show info using object attributes
        info_text = (f"Title: {show.name}\n"
                    f"First Aired: {show.first_air_date if hasattr(show, 'first_air_date') else 'N/A'}\n"
                    f"Overview: {show.overview[:200] if hasattr(show, 'overview') else ''}")
        self.update_info(info_text)

        # Load seasons using show object
        self.load_seasons(show)

    def load_seasons(self, show):
        self.seasons_list.delete(0, tk.END)
        self.seasons_dict.clear()

        try:
            # Access show.id directly
            details = self.tv.details(show.id)
            for season in range(1, details.number_of_seasons + 1):
                display_text = f"Season {season}"
                self.seasons_list.insert(tk.END, display_text)
                self.seasons_dict[display_text] = season
        except Exception as e:
            self.logger.error(f"Error loading seasons: {str(e)}")
            self.seasons_list.insert(tk.END, f"Error: {str(e)}")

    def on_season_select(self, event):
        show_selection = self.shows_list.curselection()
        season_selection = self.seasons_list.curselection()
        if not show_selection or not season_selection:
            return

        show = self.shows_dict.get(self.shows_list.get(show_selection[0]))
        season_num = self.seasons_dict.get(self.seasons_list.get(season_selection[0]))

        if show and season_num:
            self.selected_season = season_num
            self.load_episodes(show, season_num)

    def load_episodes(self, show, season_num):
        """Load episodes for the selected season"""
        self.episodes_list.delete(0, tk.END)
        self.episodes_dict.clear()

        try:
            # Access show.id directly
            season_details = self.season_api.details(show.id, season_num)
            if not season_details or not hasattr(season_details, 'episodes'):
                self.episodes_list.insert(tk.END, "No episodes found")
                return

            # Sort and display episodes
            episodes = sorted(season_details.episodes, key=lambda x: x.episode_number)

            for episode in episodes:
                episode_name = format_show_name(episode.name)
                air_date = f" ({episode.air_date})" if hasattr(episode, 'air_date') else ""
                display_text = f"E{episode.episode_number:02d} - {episode_name}{air_date}"
                
                self.episodes_list.insert(tk.END, display_text)
                self.episodes_dict[display_text] = episode

        except Exception as e:
            error_msg = f"Error loading episodes: {str(e)}"
            self.logger.error(error_msg)
            self.episodes_list.insert(tk.END, error_msg)

    def on_episode_select(self, event):
        selection = self.episodes_list.curselection()
        if not selection:
            return

        display_text = self.episodes_list.get(selection[0])
        episode = self.episodes_dict.get(display_text)

        if episode:
            self.selected_episode = episode

            # Update info text with episode details
            if hasattr(episode, 'overview') and episode.overview:
                episode_info = (
                    f"Episode: {episode.name}\n"
                    f"Air Date: {episode.air_date if hasattr(episode, 'air_date') else 'N/A'}\n"
                    f"Overview: {episode.overview[:200]}..."
                )
                self.update_info(episode_info)

    def update_info(self, text):
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, text)
        self.info_text.config(state=tk.DISABLED)

    def select_show(self):
        """Handle show selection and dialog closure"""
        show_selection = self.shows_list.curselection()
        if not show_selection:
            return

        display_text = self.shows_list.get(show_selection[0])
        show_data = self.shows_dict.get(display_text)
        
        if show_data:
            # Convert dictionary back to TMDb show object
            self.selected_show = type('TMDbShow', (), {
                'id': show_data['id'],
                'name': show_data['name'],
                'first_air_date': show_data['first_air_date'],
                'overview': show_data['overview']
            })

            # Get selected season
            season_selection = self.seasons_list.curselection()
            if season_selection:
                season_text = self.seasons_list.get(season_selection[0])
                self.selected_season = self.seasons_dict.get(season_text)

                # Get selected episode
                episode_selection = self.episodes_list.curselection()
                if episode_selection:
                    episode_text = self.episodes_list.get(episode_selection[0])
                    self.selected_episode = self.episodes_dict.get(episode_text)

            self.dialog.destroy()

    def get_result(self):
        self.dialog.wait_window()
        return self.selected_show, self.selected_season, self.selected_episode

    def get_season_details(self, show_id, season_num):
        """Get detailed information about a specific season"""
        try:
            # Use the TV class to get season details
            season = self.tv.season(show_id, season_num)
            if not season:
                print(f"No season found for show {show_id}, season {season_num}")
                return None

            # Add debug information
            print(
                f"Season data received: {season.__dict__ if hasattr(season, '__dict__') else 'No details'}"
            )
            return season

        except Exception as e:
            print(f"Error getting season details: {e}")
            return None
