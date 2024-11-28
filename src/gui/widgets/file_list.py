import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Optional, Callable
from src.core.models.file_entry import FileEntry

class FileListWidget(ttk.Frame):
    """A custom widget for displaying and managing a list of files with sorting and undo capabilities."""
    
    def __init__(self, parent, on_selection_change: Optional[Callable] = None):
        super().__init__(parent)
        self.files: List[FileEntry] = []
        self.on_selection_change = on_selection_change
        
        # Initialize sorting state
        self.sort_state = {
            "Original Name": False,
            "New Name": False,
            "Path": False,
            "Status": False
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI components of the file list."""
        # File list with sorting capability
        columns = ("Original Name", "New Name", "Path", "Status")
        self.treeview = ttk.Treeview(self, columns=columns, show="headings")
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.treeview.yview)
        x_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.treeview.xview)
        self.treeview.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)

        # Configure columns and add sorting
        column_widths = {
            "Original Name": 200,
            "New Name": 300,
            "Path": 300,
            "Status": 100
        }
        
        for col in columns:
            self.treeview.heading(col, text=col, 
                command=lambda c=col: self.sort_by_column(c))
            self.treeview.column(col, width=column_widths[col], minwidth=100)

        # Grid layout
        self.treeview.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Bind selection event
        self.treeview.bind("<<TreeviewSelect>>", self._on_select)

    def add_file(self, file_entry: FileEntry):
        """Add a single file to the list."""
        self.files.append(file_entry)
        self.treeview.insert(
            "",
            "end",
            values=(
                file_entry.original_name,
                file_entry.new_name or "Not processed",
                file_entry.path,
                file_entry.status,
            ),
        )

    def clear(self):
        """Clear all files from the list."""
        self.files.clear()
        for item in self.treeview.get_children():
            self.treeview.delete(item)

    def get_selected_files(self) -> List[FileEntry]:
        """Get currently selected files."""
        selected_items = self.treeview.selection()
        return [
            file for file in self.files
            if any(self.treeview.item(item)["values"][2] == file.path
                  for item in selected_items)
        ]

    def sort_by_column(self, col):
        """Sort the list by the specified column."""
        items = [(self.treeview.set(item, col), item) 
                for item in self.treeview.get_children("")]
        
        items.sort(reverse=self.sort_state[col])
        
        for index, (_, item) in enumerate(items):
            self.treeview.move(item, "", index)
        
        self.sort_state[col] = not self.sort_state[col]
        self.treeview.heading(col, 
            text=f"{col} {'↓' if self.sort_state[col] else '↑'}")

    def update_file_status(self, file_path: str, new_status: str):
        """Update the status of a file in the list."""
        for item in self.treeview.get_children():
            if self.treeview.item(item)["values"][2] == file_path:
                values = list(self.treeview.item(item)["values"])
                values[3] = new_status
                self.treeview.item(item, values=values)
                break

    def _on_select(self, event):
        """Handle selection change event."""
        if self.on_selection_change:
            self.on_selection_change(self.get_selected_files()) 