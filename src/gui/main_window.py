import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
from src.core.renamer import TVShowRenamer
from src.gui.dialogs.show_dialog import ShowInputDialog
from src.utils.logger import setup_logger, log_safely
import time
import threading
import queue
from src.core.models.file_entry import FileEntry
from src.core.models.renaming_method import RenamingMethod
from src.gui.widgets.file_list import FileListManager

# Try to import drag and drop support
DRAG_DROP_SUPPORTED = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD # type: ignore

    DRAG_DROP_SUPPORTED = True
except (ImportError, RuntimeError) as e:
    print(f"Drag and drop support not available: {e}")
    print("Using basic file selection instead.")


class AdvancedRenamer(TkinterDnD.Tk if DRAG_DROP_SUPPORTED else tk.Tk):
    def __init__(self):
        self.logger = setup_logger(__name__)
        try:
            super().__init__()
        except Exception as e:
            print(f"Error initializing drag and drop: {e}")
            # Fallback to basic Tk
            DRAG_DROP_SUPPORTED = False
            self.__class__ = tk.Tk
            tk.Tk.__init__(self)

        self.title("TV Show Renamer")
        self.geometry("1200x800")

        # Initialize variables
        self.files: List[FileEntry] = []
        self.undo_stack: List[Dict] = []
        self.current_method: Optional[RenamingMethod] = None
        self.tv_renamer = TVShowRenamer(self)
        self.current_show = None
        self.current_season = None
        self.current_episode = None
        self.show_info_var = tk.StringVar()
        self.show_info_var.set("No show selected")

        # Initialize sorting state for columns
        self.sort_state = {
            "Original Name": False,
            "New Name": False,
            "Path": False,
            "Status": False,
        }

        # Initialize statistics variables
        self.api_calls_var = tk.StringVar(value="API Calls: 0")
        self.cache_hits_var = tk.StringVar(value="Cache Hits: 0")
        self.response_time_var = tk.StringVar(value="Avg Response: 0ms")
        self.cache_rate_var = tk.StringVar(value="Cache Rate: 0%")

        # Add queue for background processing
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.processing = False

        # Start background worker
        self.start_background_worker()

        self.setup_ui()
        self.load_renaming_methods()

    def setup_ui(self):
        # Configure weight for root window
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Main container
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        main_frame.grid_rowconfigure(3, weight=1)  # Make preview frame expandable
        main_frame.grid_columnconfigure(0, weight=1)

        # Top toolbar
        self.toolbar = ttk.Frame(main_frame)
        self.toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Add buttons
        ttk.Button(self.toolbar, text="Add Files", command=self.add_files).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(self.toolbar, text="Clear", command=self.clear_files).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(self.toolbar, text="Undo", command=self.undo_last_batch).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(
            self.toolbar, text="Select Show", command=self.open_show_dialog
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(self.toolbar, textvariable=self.show_info_var).pack(
            side=tk.LEFT, padx=10
        )

        # Renaming method selection
        method_frame = ttk.LabelFrame(main_frame, text="Renaming Methods")
        method_frame.grid(row=1, column=0, sticky="ew", pady=5)
        method_frame.grid_columnconfigure(0, weight=1)

        self.method_tree = ttk.Treeview(
            method_frame, columns=("description"), show="tree", height=3
        )
        self.method_tree.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.method_tree.bind("<<TreeviewSelect>>", self.on_method_select)

        # Preview frame
        preview_frame = ttk.LabelFrame(main_frame, text="Preview")
        preview_frame.grid(row=3, column=0, sticky="nsew", pady=5)
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        # Replace the file list creation with:
        self.file_list = FileListManager(preview_frame)
        self.file_list.grid(row=0, column=0, sticky="nsew")
        
        # Bind the undo event
        self.file_list.bind("<<UndoRequested>>", lambda e: self.undo_selected())

        # Configure drag and drop if supported
        if DRAG_DROP_SUPPORTED:
            self.file_list.tree.drop_target_register(DND_FILES)
            self.file_list.tree.dnd_bind("<<Drop>>", self.handle_drop)

            # Add drop zone label
            self.drop_label = ttk.Label(
                preview_frame,
                text="Drag and drop files here",
                style="DropZone.TLabel"
            )
            self.drop_label.place(relx=0.5, rely=0.5, anchor="center")
            self.update_drop_zone()

        # Add right-click menu for undo
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Undo", command=self.undo_selected)
        self.file_list.bind("<Button-3>", self.show_context_menu)

        # Add undo history frame
        history_frame = ttk.LabelFrame(main_frame, text="Undo History")
        history_frame.grid(row=4, column=0, sticky="ew", pady=5)
        history_frame.grid_columnconfigure(0, weight=1)

        self.history_list = ttk.Treeview(
            history_frame,
            columns=("Time", "Files", "Status"),
            show="headings",
            height=3,
        )

        # Configure history columns
        self.history_list.heading("Time", text="Time")
        self.history_list.heading("Files", text="Files")
        self.history_list.heading("Status", text="Status")
        self.history_list.column("Time", width=100)
        self.history_list.column("Files", width=200)
        self.history_list.column("Status", width=100)

        self.history_list.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Bottom frame for progress and stats
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=5, column=0, sticky="ew", pady=5)
        bottom_frame.grid_columnconfigure(0, weight=1)

        # Progress bar frame
        self.progress_frame = ttk.Frame(bottom_frame)
        self.progress_frame.grid(row=0, column=0, sticky="ew", pady=5)
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(5, 0))

        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.grid(row=0, column=1, padx=5)

        # Stats frame
        self.stats_frame = ttk.Frame(bottom_frame)
        self.stats_frame.grid(row=1, column=0, sticky="ew", pady=5)

        # Stats labels with consistent widths
        ttk.Label(self.stats_frame, textvariable=self.api_calls_var, width=20).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Label(self.stats_frame, textvariable=self.cache_hits_var, width=20).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Label(self.stats_frame, textvariable=self.response_time_var, width=20).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Label(self.stats_frame, textvariable=self.cache_rate_var, width=20).pack(
            side=tk.LEFT, padx=5
        )

        # Refresh stats button
        ttk.Button(self.stats_frame, text="↻", width=3, command=self.update_stats).pack(
            side=tk.RIGHT, padx=5
        )

        # Add bottom frame for Start Batch button
        bottom_button_frame = ttk.Frame(preview_frame)
        bottom_button_frame.grid(row=2, column=0, columnspan=2, sticky="e", padx=5, pady=5)
        
        self.start_batch_btn = ttk.Button(
            bottom_button_frame,
            text="Start Batch",
            command=self.start_batch
        )
        self.start_batch_btn.pack(side=tk.RIGHT)

    def load_renaming_methods(self):
        # Default renaming methods
        methods = [
            RenamingMethod(
                "TV Show (TVDB)", "", "Rename TV show episodes using TVDB database"
            ),
            RenamingMethod("<Inc Nr>", "{nr}", "Incrementing number"),
            RenamingMethod("<Name>", "{name}", "Original filename without extension"),
            RenamingMethod("<Ext>", "{ext}", "File extension"),
            RenamingMethod("<Date>", "{date}", "File creation date"),
        ]

        for method in methods:
            self.method_tree.insert(
                "", "end", text=method.name, values=(method.description,)
            )

    def add_files(self):
        files = filedialog.askopenfilenames()
        self.process_new_files(files)

    def process_new_files(self, files: tuple):
        """Process new files and update UI"""
        for file_path in files:
            entry = FileEntry(file_path)
            self.file_list.add_file(
                entry.original_name,
                entry.path,
                status="Not processed",
            )
        self.update_drop_zone()
        # Trigger preview update when files are added
        self.update_preview()

    def clear_files(self):
        """Clear file list and show drop zone"""
        self.file_list.clear()
        self.update_drop_zone()

    def on_method_select(self, event):
        selection = self.method_tree.selection()
        if selection:
            item = self.method_tree.item(selection[0])
            method_name = item["text"]
            # Find the corresponding method
            for method in [m for m in self.method_tree.get_children()]:
                if self.method_tree.item(method)["text"] == method_name:
                    self.current_method = RenamingMethod(
                        method_name,
                        self.method_tree.item(method)["text"],
                        self.method_tree.item(method)["values"][0],
                    )
                    self.update_preview()
                    break

    @log_safely
    def preview_tv_show_rename(self, file_entry: FileEntry):
        """Preview TV show rename using TMDb."""
        if not self.current_show:
            file_entry.status = "No show selected"
            file_entry.new_name = ""
            return

        if not self.current_season:
            file_entry.status = "No season selected"
            file_entry.new_name = ""
            return

        try:
            # Extract episode number from filename
            show_info = self.tv_renamer.extract_episode_number(file_entry.original_name)
            if not show_info:
                file_entry.status = "No episode number found"
                file_entry.new_name = ""
                return

            episode_num = show_info

            # Use the selected season and episode number
            try:
                # Get episode information from TMDb
                episode_info = self.tv_renamer.get_episode_info(
                    self.current_show.id, self.current_season, episode_num
                )

                if episode_info:
                    # Create new filename
                    extension = os.path.splitext(file_entry.original_name)[1]
                    new_name = (
                        f"{self.current_show.name}-S{self.current_season:02d}E{episode_num:02d}-"
                        f"{episode_info['name']}{extension}"
                    )
                    file_entry.new_name = self.tv_renamer.sanitize_filename(new_name)
                    file_entry.status = "Ready"
                else:
                    file_entry.status = (
                        f"Episode not found in season {self.current_season}"
                    )
                    file_entry.new_name = ""

            except Exception as e:
                file_entry.status = f"Error: {str(e)}"
                file_entry.new_name = ""

        except Exception as e:
            file_entry.status = f"Error: {str(e)}"
            file_entry.new_name = ""

        # Update stats after API calls
        self.update_stats()

    def update_preview(self):
        """Update the preview based on selected method."""
        # Don't clear the file list - just update existing entries
        if not self.file_list.tree.get_children():
            return

        # Process files in batch
        for item in self.file_list.tree.get_children():
            values = self.file_list.tree.item(item)["values"]
            file_path = values[2]  # Get path from treeview
            
            # Create FileEntry from existing item
            file_entry = FileEntry(file_path)
            file_entry.original_name = values[0]  # Preserve original name
            
            # Process the preview
            self.preview_tv_show_rename(file_entry)
            
            # Update the item in treeview
            self.file_list.update_item(item, original_name=file_entry.original_name, new_name=file_entry.new_name, path=file_entry.path, status=file_entry.status)
            
            # Force update of the UI
            self.update_idletasks()

    def process_batch(self, files):
        """Process multiple files with progress updates"""
        total_files = len(files)
        processed = 0
        failed = []
        retry_count = 3  # Number of retries for failed API calls

        for file_entry in files:
            try:
                # Update progress
                processed += 1
                progress = (processed / total_files) * 100
                self.progress_var.set(progress)
                self.progress_label.config(text=f"Processing {processed}/{total_files}")
                self.update_idletasks()

                # Process file with retries
                for attempt in range(retry_count):
                    try:
                        self.preview_tv_show_rename(file_entry)
                        break
                    except Exception as e:
                        if attempt == retry_count - 1:
                            failed.append((file_entry, str(e)))
                            self.logger.error(
                                f"Failed to process {file_entry.original_name} after {retry_count} attempts: {e}"
                            )
                        else:
                            self.logger.warning(
                                f"Attempt {attempt + 1} failed for {file_entry.original_name}: {e}. Retrying..."
                            )
                            time.sleep(1)  # Wait before retry

            except Exception as e:
                failed.append((file_entry, str(e)))
                self.logger.error(f"Error processing {file_entry.original_name}: {e}")

        # Show summary of failures if any
        if failed:
            error_msg = "The following files failed to process:\n\n"
            for file_entry, error in failed:
                error_msg += f"• {file_entry.original_name}: {error}\n"
            messagebox.showerror("Processing Errors", error_msg)

        # Reset progress
        self.progress_var.set(0)
        self.progress_label.config(text="")
        self.update_idletasks()

    def start_batch(self):
        """Execute the batch renaming operation."""
        files = [
            FileEntry(self.file_list.tree.item(item)["values"][2])  # Create FileEntry from path
            for item in self.file_list.tree.get_children()
        ]
        
        if not files:
            messagebox.showwarning("No Files", "Please add files to rename first.")
            return

        if not self.current_method:
            messagebox.showwarning("No Method", "Please select a renaming method first.")
            return

        # Store current state for undo
        undo_batch = {
            "timestamp": datetime.now().isoformat(),
            "files": []
        }

        success_count = 0
        for item in self.file_list.tree.get_children():
            values = self.file_list.tree.item(item)["values"]
            original_name = values[0]
            new_name = values[1]
            current_path = values[2]
            
            if not new_name or new_name == "Not processed":
                continue

            try:
                new_path = os.path.join(os.path.dirname(current_path), new_name)
                os.rename(current_path, new_path)
                
                # Store original state for undo
                undo_batch["files"].append((new_path, original_name))
                
                # Update status in treeview
                self.file_list.update_item(item, new_name=new_name, path=new_path, status="Success")
                success_count += 1
                
            except Exception as e:
                self.file_list.update_item(item, new_name=new_name, path=current_path, status=f"Error: {str(e)}")

        if undo_batch["files"]:
            self.undo_stack.append(undo_batch)
            
        messagebox.showinfo(
            "Batch Complete",
            f"Successfully renamed {success_count} files."
        )

    def undo_last_batch(self):
        if not self.undo_stack:
            messagebox.showinfo("No Undo Available", "No previous batch to undo.")
            return

        last_batch = self.undo_stack.pop()

        for file_path, original_name in last_batch["files"]:
            try:
                current_dir = os.path.dirname(file_path)
                new_path = os.path.join(current_dir, original_name)
                if os.path.exists(file_path):
                    os.rename(file_path, new_path)
            except Exception as e:
                messagebox.showerror("Undo Error", f"Error undoing rename: {str(e)}")

        self.clear_files()
        messagebox.showinfo("Undo Complete", "Successfully undid last batch rename.")

    def open_show_dialog(self):
        dialog = ShowInputDialog(self)
        result = dialog.get_result()
        if result:
            show, season, episode = result
            if show:
                self.current_show = show
                self.current_season = season
                self.current_episode = episode

                # Update the show info display with season and episode
                season_info = f" - Season {season}" if season else ""
                episode_info = (
                    f" Episode {episode.episode_number} - {episode.name}"
                    if episode
                    else ""
                )

                self.show_info_var.set(
                    f"Selected: {show.name}{season_info}{episode_info} "
                    f"({show.first_air_date[:4] if show.first_air_date else 'N/A'})"
                )

                # If TV Show method is not selected, select it
                for item in self.method_tree.get_children():
                    if self.method_tree.item(item)["text"] == "TV Show (TVDB)":
                        self.method_tree.selection_set(item)
                        self.on_method_select(None)  # Trigger method selection
                        break

                # Update the preview with new show/season information
                self.update_preview()

        # Update stats after dialog closes
        self.update_stats()

    def handle_drop(self, event):
        """Handle dropped files"""
        try:
            self.logger.debug("Handling file drop event")
            files = self.parse_drop_data(event.data)

            if files:
                self.logger.info(f"Processing {len(files)} dropped files")
                self.process_new_files(files)
                self.update_drop_zone()
            else:
                self.logger.warning("No valid files found in drop event")

        except Exception as e:
            self.logger.error(f"Error handling drop event: {e}")

    def parse_drop_data(self, data):
        """Parse dropped data into a list of file paths, handling multiple files.

        Args:
            data: String containing file paths from drag & drop event

        Returns:
            List of cleaned file paths
        """
        self.logger.debug(f"Parsing drop data: {data}")
        files = []

        try:
            if not isinstance(data, str):
                return list(data)

            # Handle Windows-style paths
            if os.name == "nt":
                # Split by '} {' and clean up the braces
                paths = data.split("} {")
                files = [p.strip("{}") for p in paths]

            # Handle macOS/Linux paths
            else:
                # Handle paths with spaces and special characters
                if data.startswith("{") and data.endswith("}"):
                    # Multiple files are separated by spaces within braces
                    paths = data[1:-1].split("} {")
                    files = [p.strip("{}") for p in paths]
                else:
                    # Single file or space-separated paths
                    files = data.split()

            # Clean up paths
            cleaned_files = []
            for file_path in files:
                # Remove any escape characters
                cleaned_path = file_path.replace("\\", "")
                # Remove any remaining braces
                cleaned_path = cleaned_path.strip("{}")
                # Add to cleaned files list
                cleaned_files.append(cleaned_path)

            self.logger.debug(f"Parsed files: {cleaned_files}")
            return cleaned_files

        except Exception as e:
            self.logger.error(f"Error parsing drop data: {e}")
            return []

    def update_drop_zone(self):
        """Update drop zone visibility based on file list content"""
        if len(self.file_list.tree.get_children()) == 0:
            self.drop_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.drop_label.place_forget()

    def update_stats(self):
        """Update the statistics display"""
        try:
            stats = self.tv_renamer.get_stats()
            perf_stats = self.tv_renamer.get_performance_stats()

            # Update statistics variables
            total_api_calls = sum(stats["api_calls"].values())
            self.api_calls_var.set(f"API Calls: {total_api_calls}")

            total_cache_hits = sum(stats["cache_hits"].values())
            self.cache_hits_var.set(f"Cache Hits: {total_cache_hits}")

            # Calculate average response time
            if perf_stats["avg_api_time"] != "N/A":
                avg_time = float(perf_stats["avg_api_time"].replace("s", "")) * 1000
                self.response_time_var.set(f"Avg Response: {avg_time:.0f}ms")

            self.cache_rate_var.set(f"Cache Rate: {stats['cache_hit_rate']}")

        except Exception as e:
            self.logger.error(f"Error updating stats: {e}")

    def start_background_worker(self):
        """Start background worker thread"""

        def worker():
            while True:
                task = self.task_queue.get()
                if task is None:
                    break
                try:
                    result = task()
                    self.result_queue.put(("success", result))
                except Exception as e:
                    self.result_queue.put(("error", str(e)))
                self.task_queue.task_done()

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()
        self.after(100, self.check_results)

    def check_results(self):
        """Check for completed background tasks"""
        try:
            while True:
                status, result = self.result_queue.get_nowait()
                if status == "error":
                    self.logger.error(f"Background task error: {result}")
                    messagebox.showerror("Error", f"Background task failed: {result}")
                self.result_queue.task_done()
        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_results)

    def process_in_background(self, func, *args, **kwargs):
        """Queue a task for background processing"""
        self.task_queue.put(lambda: func(*args, **kwargs))

    def sort_treeview(self, col):
        """Sort treeview by column."""
        # Get all items
        items = [
            (self.file_list.set(item, col), item)
            for item in self.file_list.get_children("")
        ]

        # Sort items
        items.sort(reverse=self.sort_state[col])

        # Rearrange items in sorted positions
        for index, (_, item) in enumerate(items):
            self.file_list.move(item, "", index)

        # Reverse sort state
        self.sort_state[col] = not self.sort_state[col]

        # Update header
        self.file_list.heading(
            col, text=f"{col} {'↓' if self.sort_state[col] else '↑'}"
        )

    def show_context_menu(self, event):
        """Show context menu on right click."""
        item = self.file_list.tree.identify_row(event.y)
        if item:
            self.file_list.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def undo_selected(self):
        """Undo rename for selected files."""
        selected = self.file_list.tree.selection()
        if not selected:
            return

        # Store undo information
        undo_batch = {
            "timestamp": datetime.now().isoformat(),
            "files": []
        }

        for item in selected:
            values = self.file_list.tree.item(item)["values"]
            original_name = values[0]
            current_path = values[2]
            
            try:
                # Get original path
                original_path = os.path.join(
                    os.path.dirname(current_path),
                    original_name
                )
                
                # Perform undo
                if os.path.exists(current_path):
                    os.rename(current_path, original_path)
                    undo_batch["files"].append((current_path, original_name))
                    
                    # Update treeview
                    self.file_list.update_item(item, new_name="", path=original_path, status="Undone")
            
            except Exception as e:
                self.logger.error(f"Error undoing rename: {e}")
                self.file_list.update_item(item, new_name="", path=current_path, status=f"Undo failed: {str(e)}")

        # Add to undo history
        if undo_batch["files"]:
            self.add_to_history(undo_batch)

    def add_to_history(self, batch):
        """Add batch operation to history."""
        time_str = datetime.fromisoformat(batch["timestamp"]).strftime("%H:%M:%S")
        files_count = len(batch["files"])

        self.history_list.insert(
            "", 0, values=(time_str, f"{files_count} files", "Undone")
        )

        # Limit history items
        if len(self.history_list.get_children()) > 10:
            self.history_list.delete(self.history_list.get_children()[-1])

    def on_file_selection_change(self, selected_files):
        """Handle file selection changes"""
        if selected_files:
            # Enable/disable buttons based on selection
            self.update_button_states(True)
        else:
            self.update_button_states(False)

    def update_button_states(self, has_selection: bool):
        """Update button states based on selection"""
        # Enable/disable buttons based on selection
        state = "normal" if has_selection else "disabled"
        for child in self.toolbar.winfo_children():
            if isinstance(child, ttk.Button) and child["text"] in ["Clear", "Undo"]:
                child.configure(state=state)


if __name__ == "__main__":
    app = AdvancedRenamer()

    # Configure style for drop zone if drag and drop is supported
    if DRAG_DROP_SUPPORTED:
        style = ttk.Style()
        style.configure(
            "DropZone.TLabel",
            font=("Helvetica", 12),
            foreground="gray",
            background="white",
            padding=20,
        )

    app.mainloop()
