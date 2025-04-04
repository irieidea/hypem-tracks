import requests
import json
import time
from datetime import datetime
import os

class HypemSquarespaceIntegration:
    def __init__(self, config_file='config.json'):
        # Load configuration
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        # Hypem configuration
        self.hypem_username = self.config['hypem']['username']
        self.last_processed_id = self.config['hypem'].get('last_processed_id')
        
        # Squarespace configuration
        self.squarespace_api_key = self.config['squarespace']['api_key']
        self.squarespace_domain = self.config['squarespace']['domain']
        
        # Initialize sessions
        self.hypem_session = requests.Session()
        self.hypem_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        })
        
        self.squarespace_session = requests.Session()
        self.squarespace_session.headers.update({
            'Authorization': f'Bearer {self.squarespace_api_key}',
            'User-Agent': 'Hypem-Squarespace-Integration/1.0',
            'Content-Type': 'application/json'
        })
        
        # Find website ID and collection ID if not provided
        self.website_id = self.config['squarespace'].get('website_id')
        self.collection_id = self.config['squarespace'].get('collection_id')
        
        if not self.website_id or not self.collection_id:
            self.find_squarespace_ids()
    
    def find_squarespace_ids(self):
        """Find the website ID and blog collection ID automatically"""
        try:
            # First, get the website ID
            if not self.website_id:
                print("Trying to find website ID...")
                url = "https://api.squarespace.com/1.0/websites"
                response = self.squarespace_session.get(url)
                response.raise_for_status()
                websites = response.json().get('websites', [])
                
                # Look for the website with matching domain
                for website in websites:
                    domains = website.get('domains', [])
                    for domain in domains:
                        if isinstance(domain, dict) and self.squarespace_domain in domain.get('domain', ''):
                            self.website_id = website.get('id')
                            print(f"Found website ID: {self.website_id}")
                            break
                    if self.website_id:
                        break
                
                if not self.website_id and websites:
                    # If we couldn't find by domain but have websites, use the first one
                    self.website_id = websites[0].get('id')
                    print(f"Using first website ID found: {self.website_id}")
            
            # Next, find the collection ID (blog)
            if self.website_id and not self.collection_id:
                print("Trying to find blog collection ID...")
                url = f"https://api.squarespace.com/1.0/websites/{self.website_id}/collections"
                response = self.squarespace_session.get(url)
                response.raise_for_status()
                collections = response.json().get('collections', [])
                
                # Look for blog collections
                blog_collections = [c for c in collections if c.get('type') == 'blog']
                
                if blog_collections:
                    # Use the first blog collection
                    self.collection_id = blog_collections[0].get('id')
                    print(f"Found blog collection ID: {self.collection_id}")
                
                # Update config with the IDs
                self.config['squarespace']['website_id'] = self.website_id
                self.config['squarespace']['collection_id'] = self.collection_id
                
                with open('config.json', 'w') as f:
                    json.dump(self.config, f, indent=2)
                    
                print("Updated config.json with website ID and collection ID")
        except Exception as e:
            print(f"Error finding Squarespace IDs: {e}")
    
    def get_liked_tracks(self, limit=5):
        """Fetch the user's most recently liked tracks from Hypem"""
        url = f"https://hypem.com/api/loved_items_by_user_name?user_name={self.hypem_username}&page=1&count={limit}"
        
        try:
            response = self.hypem_session.get(url)
            response.raise_for_status()
            
            # Hypem returns JSON with some extra characters at the beginning
            content = response.text
            if content.startswith('while(1);'):
                content = content[9:]  # Remove the while(1); prefix
                
            data = json.loads(content)
            return data
        except Exception as e:
            print(f"Error fetching liked tracks: {e}")
            return None
    
    def get_track_details(self, track_id):
        """Get detailed information about a track from Hypem"""
        url = f"https://hypem.com/track/{track_id}"
        
        try:
            response = self.hypem_session.get(url)
            response.raise_for_status()
            html = response.text
            
            # Simple string extraction
            title = self.extract_between(html, '<h1 class="track">', '</h1>')
            artist = self.extract_between(html, '<h2 class="artist">', '</h2>')
            
            # Extract artwork URL
            artwork_url = None
            img_tag = self.extract_between(html, '<img class="thumb', '>')
            if img_tag:
                src_start = img_tag.find('src="') + 5
                if src_start > 5:
                    src_end = img_tag.find('"', src_start)
                    if src_end > src_start:
                        artwork_url = img_tag[src_start:src_end]
                        # Convert to high-res if available
                        artwork_url = artwork_url.replace('_120.jpg', '_320.jpg')
            
            # Extract tags
            tags = []
            tag_section = self.extract_between(html, 'class="tags"', '</div>')
            if tag_section:
                tag_links = tag_section.split('<a href="/tags/')
                for tag_link in tag_links[1:]:
                    tag = self.extract_between(tag_link, '">', '</a>')
                    if tag:
                        tags.append(tag)
            
            # Combine the data
            result = {
                'track_id': track_id,
                'title': title,
                'artist': artist,
                'artwork_url': artwork_url,
                'hypem_url': url,
                'embed_url': f"https://hypem.com/embed/track/{track_id}",
                'tags': tags,
                'date_fetched': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return result
        except Exception as e:
            print(f"Error getting track details: {e}")
            return None
    
    def extract_between(self, text, start_marker, end_marker):
        """Extract text between two markers"""
        if not text:
            return None
        
        start_idx = text.find(start_marker)
        if start_idx == -1:
            return None
        
        start_idx += len(start_marker)
        end_idx = text.find(end_marker, start_idx)
        
        if end_idx == -1:
            return None
        
        return text[start_idx:end_idx].strip()
    
    def generate_description(self, track_info):
        """Generate a simple description for the track"""
        return f"Check out this amazing track from {track_info['artist']}!"
    
    def create_squarespace_post(self, track_info):
        """Create a new Squarespace blog post for the track"""
        if not self.website_id or not self.collection_id:
            print("Missing website ID or collection ID. Cannot create post.")
            return None
        
        try:
            # Generate a simple description
            if 'description' not in track_info or not track_info['description']:
                track_info['description'] = self.generate_description(track_info)
            
            # Format the content
            html_content = f"""
            <div class="track-post">
                <div class="track-artwork">
                    <img src="{track_info['artwork_url']}" alt="{track_info['artist']} - {track_info['title']}">
                </div>
                
                <div class="track-player">
                    <iframe width="100%" height="120" src="{track_info['embed_url']}" frameborder="0" allowfullscreen></iframe>
                </div>
                
                <div class="track-description">
                    <p>{track_info['description']}</p>
                </div>
                
                <div class="track-meta">
                    <p><a href="{track_info['hypem_url']}" target="_blank">View on Hype Machine</a></p>
                </div>
            </div>
            """
            
            # Prepare post data
            post_data = {
                "type": "blog",
                "title": f"{track_info['artist']} - {track_info['title']}",
                "body": html_content,
                "tags": track_info['tags'],
                "categories": ["Music", "Hype Machine"],
                "status": "PUBLISHED"
            }
            
            # Create the post using Squarespace API
            url = f"https://api.squarespace.com/1.0/websites/{self.website_id}/collections/{self.collection_id}/items"
            
            response = self.squarespace_session.post(url, json=post_data)
            response.raise_for_status()
            
            post_info = response.json()
            print(f"Created post for {track_info['artist']} - {track_info['title']} with ID {post_info.get('id')}")
            return post_info.get('id')
        except Exception as e:
            print(f"Error creating Squarespace post: {e}")
            return None
    
    def update_config(self):
        """Update configuration with the last processed track ID"""
        self.config['hypem']['last_processed_id'] = self.last_processed_id
        
        with open('config.json', 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def process_new_likes(self):
        """Process new likes and create blog posts for them"""
        # Get latest liked tracks
        liked_tracks = self.get_liked_tracks(limit=10)
        if not liked_tracks:
            print("No tracks found or error fetching tracks")
            return
        
        # Track if we've found new tracks
        new_tracks_found = False
        
        # Process each track if it's new
        for track in liked_tracks:
            track_id = track.get('itemid')
            
            # Skip if we've already processed this track
            if self.last_processed_id and track_id == self.last_processed_id:
                print(f"Reached last processed track {track_id}, stopping")
                break
            
            # Get detailed track info
            print(f"Processing track {track_id}")
            track_info = self.get_track_details(track_id)
            if not track_info:
                print(f"Failed to get details for track {track_id}")
                continue
            
            # Create Squarespace post
            post_id = self.create_squarespace_post(track_info)
            
            # If this is the newest track and it was processed successfully, update last processed ID
            if not new_tracks_found and post_id:
                self.last_processed_id = track_id
                new_tracks_found = True
            
            # Don't hammer the APIs
            time.sleep(2)
        
        # Update configuration if we found new tracks
        if new_tracks_found:
            self.update_config()
            print(f"Updated last processed ID to {self.last_processed_id}")
        else:
            print("No new tracks found")

if __name__ == "__main__":
    # Create a sample config file if it doesn't exist
    if not os.path.exists('config.json'):
        sample_config = {
            "hypem": {
                "username": "irieidea",
                "last_processed_id": None
            },
            "squarespace": {
                "api_key": "YOUR_SQUARESPACE_API_KEY",
                "domain": "synthesizer-tuna-92rs.squarespace.com",
                "website_id": None,
                "collection_id": None
            }
        }
        
        with open('config.json', 'w') as f:
            json.dump(sample_config, f, indent=2)
        
        print("Created sample config.json - please edit with your actual credentials")
        exit(0)
    
    # Initialize and run the integration
    integration = HypemSquarespaceIntegration()
    integration.process_new_likes()
