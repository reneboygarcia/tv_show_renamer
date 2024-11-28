import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import os

class FileListManager(ttk.Frame):
    """Manages and displays a list of files with sorting and undo capabilities."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.sort_state: Dict[str, bool] = {
            "Original Name": False,
            "New Name": False,
            "Path": False,
            "Status": False,
        }
        self.setup_ui()
        self.create_context_menu()

    def setup_ui(self):
        """Initialize the UI components."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create file list with sorting capability
        columns = ("Original Name", "New Name", "Path", "Status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        x_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)

        # Configure columns
        column_widths = {
            "Original Name": 200,
            "New Name": 300,
            "Path": 300,
            "Status": 100
        }
        
        for col in columns:
            self.tree.heading(col, text=col, 
                command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=column_widths[col], minwidth=100)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

    def create_context_menu(self):
        """Create right-click context menu."""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Undo", command=self.undo_selected)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def add_file(self, original_name: str, path: str, new_name: str = "", status: str = "Not processed") -> str:
        """Add a single file to the list."""
        item_id = self.tree.insert("", "end", values=(original_name, new_name, path, status))
        return item_id

    def add_files(self, files: List[Tuple[str, str]]):
        """Add multiple files to the list."""
        for original_name, path in files:
            self.add_file(original_name, path)

    def clear(self):
        """Clear all items from the list."""
        self.tree.delete(*self.tree.get_children())

    def get_selected_items(self) -> List[Dict[str, str]]:
        """Get information about selected items."""
        selected = []
        for item_id in self.tree.selection():
            values = self.tree.item(item_id)["values"]
            selected.append({
                "id": item_id,
                "original_name": values[0],
                "new_name": values[1],
                "path": values[2],
                "status": values[3]
            })
        return selected

    def update_item(self, item_id: str, **kwargs):
        """Update specific fields of an item."""
        current_values = list(self.tree.item(item_id)["values"])
        if "original_name" in kwargs:
            current_values[0] = kwargs["original_name"]
        if "new_name" in kwargs:
            current_values[1] = kwargs["new_name"]
        if "path" in kwargs:
            current_values[2] = kwargs["path"]
        if "status" in kwargs:
            current_values[3] = kwargs["status"]
        self.tree.item(item_id, values=current_values)

    def sort_by_column(self, col: str):
        """Sort items by the specified column."""
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children("")]
        items.sort(reverse=self.sort_state[col])
        
        for index, (_, item) in enumerate(items):
            self.tree.move(item, "", index)
        
        self.sort_state[col] = not self.sort_state[col]
        self.tree.heading(col, text=f"{col} {'↓' if self.sort_state[col] else '↑'}")

    def show_context_menu(self, event):
        """Show context menu at mouse position."""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def undo_selected(self):
        """Trigger undo event for selected items."""
        self.event_generate("<<UndoRequested>>")

    def get_all_items(self) -> List[Dict[str, str]]:
        """Get information about all items in the list."""
        items = []
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id)["values"]
            items.append({
                "id": item_id,
                "original_name": values[0],
                "new_name": values[1],
                "path": values[2],
                "status": values[3]
            })
        return items
        
    def update_file_status(self, file_path: str, new_status: str):
        """Update the status of a file in the list."""
        for item in self.tree.get_children():
            if self.tree.item(item)["values"][2] == file_path:
                values = list(self.tree.item(item)["values"])
                values[3] = new_status
                self.tree.item(item, values=values)
                break
        
    def _on_select(self, event):
        """Handle selection change event."""
        if self.on_selection_change:
            self.on_selection_change(self.get_selected_files()) 