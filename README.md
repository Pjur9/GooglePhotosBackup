<<<<<<< HEAD
# GooglePhotosBackup
=======
# Google Photos Sync

This script automatically downloads all your Google Photos images and videos to a local folder and keeps them in sync by checking for new media daily.

## Setup Instructions

1. First, set up a Google Cloud Project and enable the Google Photos API:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable the Google Photos Library API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials and save them as `credentials.json` in the same directory as the script

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the script:
   ```bash
   python photos_sync.py
   ```

On first run, the script will:
- Open your browser for Google authentication
- Create a folder called 'GooglePhotosSync' in your D drive (D:\GooglePhotosSync)
- Download all your Google Photos media
- Continue running and check for new photos daily at 3 AM

## Features
- Downloads all photos and videos from Google Photos
- Maintains original file names
- Checks for new media daily at 3 AM
- Skips already downloaded files
- Keeps track of sync status
- Handles authentication tokens securely

## Notes
- The script creates a `.last_sync` file to keep track of the last successful sync
- Authentication tokens are stored in `token.pickle` for future use
- The script runs continuously to perform daily checks
- You can modify the sync schedule by editing the script
>>>>>>> 5d1fc10 (Uploading finished project)
