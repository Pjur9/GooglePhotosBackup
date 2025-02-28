import os
import pickle
import datetime
import time
import json
from pathlib import Path
import schedule
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import socket
import dns.resolver


SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

class GooglePhotosSync:
    def __init__(self, download_dir):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.last_sync = None
        self.sync_file = self.download_dir / '.last_sync'
        self.progress_file = self.download_dir / '.sync_progress'
        self.load_last_sync()
        
       
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = ['8.8.8.8', '8.8.4.4']  # Google DNS server
        
       
        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
      
        class CustomDNSAdapter(HTTPAdapter):
            def __init__(self, resolver, *args, **kwargs):
                self.resolver = resolver
                super().__init__(*args, **kwargs)
            
            def get_connection(self, url, proxies=None):
                conn = super().get_connection(url, proxies)
                if conn.host.endswith('googleusercontent.com'):
                    try:
                        answer = self.resolver.resolve(conn.host, 'A')
                        conn.sock = socket.create_connection(
                            (str(answer[0]), conn.port),
                            timeout=conn.timeout
                        )
                    except Exception as e:
                        print(f"DNS resolution error: {e}")
                return conn
        
        self.session.mount('https://', CustomDNSAdapter(self.resolver, max_retries=retries))

    def load_last_sync(self):
        if self.sync_file.exists():
            with open(self.sync_file, 'r') as f:
                self.last_sync = f.read().strip()

    def save_last_sync(self):
        with open(self.sync_file, 'w') as f:
            f.write(datetime.datetime.utcnow().isoformat())

    def save_progress(self, page_token, processed_items):
        """Save progress to resume later"""
        with open(self.progress_file, 'w') as f:
            json.dump({
                'page_token': page_token,
                'processed_items': processed_items,
                'timestamp': datetime.datetime.now().isoformat()
            }, f)

    def load_progress(self):
        """Load previous progress"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except:
                return None
        return None

    def clear_progress(self):
        """Clear progress file after successful completion"""
        if self.progress_file.exists():
            self.progress_file.unlink()

    def authenticate(self):
        creds = None
        token_path = self.download_dir / 'token.pickle'
        if token_path.exists():
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired credentials...")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    print("Need to re-authenticate. Please follow the instructions...")
                    if token_path.exists():
                        token_path.unlink()
                    creds = None
            
            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(
'C:\\Users\\milan\\CascadeProjects\\google_photos_sync\\credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
         
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        try:
            service = build('photoslibrary', 'v1', credentials=creds, static_discovery=False)
            service.mediaItems().list(pageSize=1).execute()
            return service
        except Exception as e:
            print(f"Error creating service: {str(e)}")
            print("Please make sure the Google Photos Library API is enabled in your Google Cloud Console")
            print("1. Go to https://console.cloud.google.com")
            print("2. Select your project")
            print("3. Go to APIs & Services > Library")
            print("4. Search for 'Google Photos Library API'")
            print("5. Make sure it's enabled")
            raise

    def handle_auth_error(self, service, error):
        """Handle authentication errors by refreshing token"""
        print(f"Authentication error: {error}")
        print("Attempting to re-authenticate...")
      
        token_path = self.download_dir / 'token.pickle'
        if token_path.exists():
            token_path.unlink()
      
        return self.authenticate()

    def download_media(self, service):
        print("Starting to fetch media items...")
        try:
           
            start_date = datetime.datetime(2025, 2, 1, tzinfo=datetime.timezone.utc)
            end_date = datetime.datetime(2025, 2, 20, tzinfo=datetime.timezone.utc)
            print(f"Will download media items from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

            def parse_time(time_str):
                try:
                    return datetime.datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    return datetime.datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)

            def get_download_url(item):
                base_url = item['baseUrl']
                is_video = 'video' in item['mediaMetadata']
                
                if is_video:
               
                    return f"{base_url}=dv"
                else:
                   
                    width = item['mediaMetadata'].get('width', '4096')
                    height = item['mediaMetadata'].get('height', '4096')
                    return f"{base_url}=w{width}-h{height}-d"

      
            progress = self.load_progress()
            if progress:
                print(f"\nResuming from previous session (last updated: {progress['timestamp']})")
                next_page_token = progress['page_token']
                processed_items = progress['processed_items']
            else:
                next_page_token = None
                processed_items = []

            filtered_items = []
            page_count = 0
            total_items_seen = 0
            auth_retries = 0
            MAX_AUTH_RETRIES = 3
            empty_pages_in_row = 0 
            MAX_EMPTY_PAGES = 90
            
            while True:
                try:
                    print(f"\nRequesting page {page_count + 1} of media items...")
                    
                  
                    time.sleep(0.5)
                    
                    if next_page_token:
                        results = service.mediaItems().list(
                            pageSize=100,
                            pageToken=next_page_token
                        ).execute()
                    else:
                       
                        results = service.mediaItems().list(
                            pageSize=100
                        ).execute()
                    
                  
                    auth_retries = 0
                    
                    items = results.get('mediaItems', [])
                    if not items:
                        print("No more items found")
                        break

                    total_items_seen += len(items)
                    
                   
                    dates = [parse_time(item['mediaMetadata']['creationTime']) for item in items]
                    
                   
                    print("\nSample items from current page:")
                    for item, date in zip(items[:5], dates[:5]):
                        media_type = "VIDEO" if 'video' in item['mediaMetadata'] else "PHOTO"
                        print(f"- {date.strftime('%Y-%m-%d %H:%M:%S')} ({media_type})")
                    
                   
                    new_filtered_items = []
                    for item, date in zip(items, dates):
                        if start_date <= date <= end_date:
                            if item['id'] not in processed_items:  
                                new_filtered_items.append(item)
                                print(f"Found {item['filename']} from {date.strftime('%Y-%m-%d')}")
                    
                    if new_filtered_items:
                      
                        for item in new_filtered_items:
                            date = parse_time(item['mediaMetadata']['creationTime'])
                            if item['id'] not in processed_items:  
                                print(f"Downloading {item['filename']} from {date.strftime('%Y-%m-%d')}")
                                download_url = get_download_url(item)
                                save_path = self.download_dir / item['filename']
                                
                               
                                if save_path.exists():
                                    try:
                                        response = requests.head(download_url)
                                        expected_size = int(response.headers.get('content-length', 0))
                                        actual_size = save_path.stat().st_size
                                        if expected_size == actual_size:
                                            print(f"Skipping existing complete file: {item['filename']}")
                                            processed_items.append(item['id'])
                                            continue
                                        else:
                                            print(f"Re-downloading {item['filename']} (size mismatch: {actual_size} vs {expected_size})")
                                    except Exception as e:
                                        print(f"Error checking file size for {item['filename']}: {e}")
                                        print("Will attempt to re-download")

                               
                                try:
                                    response = requests.get(download_url, stream=True)
                                    response.raise_for_status() 
                                    with open(save_path, 'wb') as f:
                                        for chunk in response.iter_content(chunk_size=8192):
                                            if chunk:
                                                f.write(chunk)
                                    print(f"Successfully downloaded: {item['filename']}")
                                    processed_items.append(item['id'])
                                except Exception as e:
                                    print(f"Error downloading {item['filename']}: {str(e)}")
                        
                        print(f"Total items to download: {len(filtered_items)}")
                    else:
                        print(f"No new items to download in this page")
                        empty_pages_in_row += 1
                        if empty_pages_in_row >= MAX_EMPTY_PAGES:
                            print(f"\nNo new items found in {MAX_EMPTY_PAGES} consecutive pages. Stopping search.")
                            break

                    next_page_token = results.get('nextPageToken')
                    if next_page_token:
                        self.save_progress(next_page_token, processed_items)
                    else:
                        print("\nReached the last page!")
                        break

                    page_count += 1

                except Exception as e:
                    if "403" in str(e) or "unauthorized" in str(e).lower():
                        if auth_retries < MAX_AUTH_RETRIES:
                            auth_retries += 1
                            print(f"\nAuthentication error (attempt {auth_retries}/{MAX_AUTH_RETRIES})")
                            service = self.handle_auth_error(service, e)
                            continue
                        else:
                            print("\nMax authentication retries reached. Please:")
                            print("1. Delete 'token.pickle' from your download directory")
                            print("2. Run the script again to re-authenticate")
                            raise
                    else:
                        print(f"\nError during page fetch: {str(e)}")
                        print("Waiting 60 seconds before trying again...")
                        time.sleep(60)
                        continue

            print(f"\nSearch completed!")
            print(f"Found {len(filtered_items)} items between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")
            
            if len(filtered_items) == 0:
                print("No items found between September 1st, 2023 and November 3rd, 2024. Exiting...")
                self.clear_progress()
                return

            print("Download process completed")
            self.clear_progress()
            self.save_last_sync()
            
        except Exception as e:
            print(f"Error during download: {str(e)}")
            raise

    def sync(self):
        print(f"Starting sync at {datetime.datetime.now()}")
        try:
            service = self.authenticate()
            self.download_media(service)
            print("Sync completed successfully")
        except Exception as e:
            print(f"Error during sync: {str(e)}")
            raise

def main():

    download_dir = Path('D:/GooglePhotosSync')
    syncer = GooglePhotosSync(download_dir)
    
   
    syncer.sync()
    
   
    schedule.every().day.at("03:00").do(syncer.sync)
    
   
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    main()
