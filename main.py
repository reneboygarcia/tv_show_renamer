import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
from pathlib import Path
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
from tv_show_renamer import TVShowRenamer


class RenamingMethod:
    def __init__(self, name: str, pattern: str, description: str):
        self.name = name
        self.pattern = pattern
        self.description = description


class FileEntry:
    def __init__(self, path: str, new_name: str = ""):
        self.path = path
        self.original_name = os.path.basename(path)
        self.new_name = new_name
        self.status = "Pending"


class AdvancedRenamer(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Advanced Renamer 4.0")
        self.geometry("1200x800")

        # Initialize variables
        self.files: List[FileEntry] = []
        self.undo_stack: List[Dict] = []
        self.current_method: Optional[RenamingMethod] = None
        self.tv_renamer = TVShowRenamer()

        self.setup_ui()
        self.load_renaming_methods()

    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Top toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        # Add buttons
        ttk.Button(toolbar, text="Add Files", command=self.add_files).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(toolbar, text="Clear", command=self.clear_files).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(toolbar, text="Undo", command=self.undo_last_batch).pack(
            side=tk.LEFT, padx=2
        )

        # Renaming method selection
        method_frame = ttk.LabelFrame(main_frame, text="Renaming Methods")
        method_frame.pack(fill=tk.X, pady=5)

        self.method_tree = ttk.Treeview(
            method_frame, columns=("description"), show="tree"
        )
        self.method_tree.pack(fill=tk.X, pady=5)
        self.method_tree.bind("<<TreeviewSelect>>", self.on_method_select)

        # Preview frame
        preview_frame = ttk.LabelFrame(main_frame, text="Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # File list
        columns = ("Original Name", "New Name", "Path", "Status")
        self.file_list = ttk.Treeview(preview_frame, columns=columns, show="headings")

        for col in columns:
            self.file_list.heading(col, text=col)
            self.file_list.column(col, width=100)

        self.file_list.pack(fill=tk.BOTH, expand=True)

        # Bottom toolbar
        bottom_toolbar = ttk.Frame(main_frame)
        bottom_toolbar.pack(fill=tk.X, pady=5)

        ttk.Button(bottom_toolbar, text="Start Batch", command=self.start_batch).pack(
            side=tk.RIGHT
        )

    def load_renaming_methods(self):
        # Default renaming methods
        methods = [
            RenamingMethod(
                "TV Show (TVDB)",
                "",
                "Rename TV show episodes using TVDB database"
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
        for file_path in files:
            entry = FileEntry(file_path)
            self.files.append(entry)
            self.file_list.insert(
                "",
                "end",
                values=(
                    entry.original_name,
                    entry.new_name or "Not processed",
                    entry.path,
                    entry.status,
                ),
            )

    def clear_files(self):
        self.files.clear()
        for item in self.file_list.get_children():
            self.file_list.delete(item)

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

    def preview_tv_show_rename(self, file_entry: FileEntry):
        """Preview TV show rename using TVDB."""
        try:
            new_name = self.tv_renamer.generate_new_name(file_entry.original_name)
            if new_name:
                file_entry.new_name = new_name
                file_entry.status = "Ready"
            else:
                file_entry.status = "No match"
        except Exception as e:
            file_entry.status = f"Error: {str(e)}"

    def update_preview(self):
        """Update the preview based on selected method."""
        self.file_list.delete(*self.file_list.get_children())
        
        for file_entry in self.files:
            if self.current_method and self.current_method.name == "TV Show (TVDB)":
                self.preview_tv_show_rename(file_entry)
            elif self.current_method:
                new_name = self.generate_new_name(file_entry, 1)
                file_entry.new_name = new_name
                file_entry.status = "Ready"
            
            self.file_list.insert(
                "",
                "end",
                values=(
                    file_entry.original_name,
                    file_entry.new_name,
                    file_entry.path,
                    file_entry.status,
                ),
            )

    def generate_new_name(self, file_entry: FileEntry, index: int) -> str:
        original_name = file_entry.original_name
        name, ext = os.path.splitext(original_name)

        if self.current_method.name == "<Inc Nr>":
            return f"{index:03d}{ext}"
        elif self.current_method.name == "<Name>":
            return name
        elif self.current_method.name == "<Ext>":
            return ext[1:] if ext else ""
        elif self.current_method.name == "<Date>":
            timestamp = os.path.getctime(file_entry.path)
            date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
            return f"{date_str}{ext}"

        return original_name

    def start_batch(self):
        if not self.files:
            messagebox.showwarning("No Files", "Please add files to rename first.")
            return

        if not self.current_method:
            messagebox.showwarning(
                "No Method", "Please select a renaming method first."
            )
            return

        # Store current state for undo
        undo_batch = {
            "timestamp": datetime.now().isoformat(),
            "files": [(f.path, f.original_name) for f in self.files],
        }

        success_count = 0
        for file_entry in self.files:
            if not file_entry.new_name:
                continue

            try:
                new_path = os.path.join(
                    os.path.dirname(file_entry.path), file_entry.new_name
                )
                os.rename(file_entry.path, new_path)
                file_entry.status = "Success"
                success_count += 1
            except Exception as e:
                file_entry.status = f"Error: {str(e)}"

            # Update status in treeview
            for item in self.file_list.get_children():
                if self.file_list.item(item)["values"][2] == file_entry.path:
                    self.file_list.item(
                        item,
                        values=(
                            file_entry.original_name,
                            file_entry.new_name,
                            (
                                new_path
                                if file_entry.status == "Success"
                                else file_entry.path
                            ),
                            file_entry.status,
                        ),
                    )

        self.undo_stack.append(undo_batch)
        messagebox.showinfo(
            "Batch Complete", f"Successfully renamed {success_count} files."
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


if __name__ == "__main__":
    app = AdvancedRenamer()
    app.mainloop()
