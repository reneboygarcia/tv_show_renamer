import os

class FileEntry:
    def __init__(self, path: str, new_name: str = ""):
        self.path = path
        self.original_name = os.path.basename(path)
        self.new_name = new_name
        self.status = "Pending"
