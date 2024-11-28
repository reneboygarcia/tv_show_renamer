import unittest
import tkinter as tk
from tkinter import ttk
from src.gui.widgets.file_list import FileListWidget
from src.core.models.file_entry import FileEntry

class TestFileListWidget(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.selection_changed = False
        self.file_list = FileListWidget(self.root, self.on_selection_change)

    def tearDown(self):
        self.root.destroy()

    def on_selection_change(self, selected_files):
        self.selection_changed = True
        self.selected_files = selected_files

    def test_add_file(self):
        """Test adding a file to the list"""
        test_file = FileEntry("/path/to/test.mkv")
        self.file_list.add_file(test_file)
        
        # Check if file was added
        items = self.file_list.treeview.get_children()
        self.assertEqual(len(items), 1)
        
        # Check values
        values = self.file_list.treeview.item(items[0])['values']
        self.assertEqual(values[0], test_file.original_name)
        self.assertEqual(values[2], test_file.path)

    def test_clear(self):
        """Test clearing the list"""
        # Add some files
        test_files = [
            FileEntry("/path/to/test1.mkv"),
            FileEntry("/path/to/test2.mkv")
        ]
        for file in test_files:
            self.file_list.add_file(file)
            
        # Clear the list
        self.file_list.clear()
        
        # Check if list is empty
        self.assertEqual(len(self.file_list.treeview.get_children()), 0)
        self.assertEqual(len(self.file_list.files), 0)

    def test_sort_by_column(self):
        """Test sorting functionality"""
        # Add files in non-alphabetical order
        test_files = [
            FileEntry("/path/to/c.mkv"),
            FileEntry("/path/to/a.mkv"),
            FileEntry("/path/to/b.mkv")
        ]
        for file in test_files:
            self.file_list.add_file(file)
            
        # Sort by original name
        self.file_list.sort_by_column("Original Name")
        
        # Check if sorted
        items = self.file_list.treeview.get_children()
        values = [self.file_list.treeview.item(item)['values'][0] for item in items]
        self.assertEqual(values, ['a.mkv', 'b.mkv', 'c.mkv'])

    def test_selection_callback(self):
        """Test selection change callback"""
        test_file = FileEntry("/path/to/test.mkv")
        self.file_list.add_file(test_file)
        
        # Select the item
        items = self.file_list.treeview.get_children()
        self.file_list.treeview.selection_set(items[0])
        
        # Check if callback was triggered
        self.assertTrue(self.selection_changed)
        self.assertEqual(len(self.selected_files), 1)
        self.assertEqual(self.selected_files[0].path, test_file.path)

if __name__ == '__main__':
    unittest.main() 