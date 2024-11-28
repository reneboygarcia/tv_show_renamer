# TV Show Renamer
A simple script for renaming multiple TV episodes at once using information from TMDb.

## Features

* Search & find the show you want directly on the console.
* Rename all the episode(s) of a show with the official episode name.
* Bulk rename normal files serially.

## Prerequisites

* [Python 3.9](https://www.python.org/downloads/) or newer.
* A TMDb API key (free).

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/tkdnd/tv-show-renamer.git
   cd tv-show-renamer
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## API Setup

1. Get your TMDB API key:
   - Create an account at [The Movie Database](https://www.themoviedb.org/)
   - Go to Settings -> API and request an API key
   - Copy your API key

2. Update `.env` file:
   - Replace `your_tmdb_api_key_here` with your actual TMDB API key

⚠️ Important: Never commit your `.env` file containing real API keys to version control.

## Usage

1. Add files to be renamed:
   - Open the application by running `python main.py`
   - Click on the "Add Files" button in the toolbar
   - Select the files you want to rename

2. Select a renaming method:
   - In the "Renaming Methods" section, choose a method from the list
   - The description of the selected method will be displayed

3. Rename the files:
   - Click on the "Rename" button in the toolbar
   - The files will be renamed according to the selected method

4. Undo the last renaming batch (if needed):
   - Click on the "Undo" button in the toolbar to revert the last renaming operation

5. Clear the file list:
   - Click on the "Clear" button in the toolbar to remove all files from the list

6. Exit the application:
   - Close the application window or press `Ctrl+C` in the terminal

Note: Ensure that you have configured your `.env` file with the correct TMDB API key before using the application.
For more advanced usage and customization, refer to the source code and comments within `main.py`.


