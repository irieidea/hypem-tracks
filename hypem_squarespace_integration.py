import requests
import json
import time
import os
from datetime import datetime

# Configuration from environment variables
HYPEM_USERNAME = os.environ.get('HYPEM_USERNAME', 'irieidea')
SQUARESPACE_API_KEY = os.environ.get('SQUARESPACE_API_KEY')
SQUARESPACE_DOMAIN = os.environ.get('SQUARESPACE_DOMAIN')
LAST_PROCESSED_ID = os.environ.get('LAST_PROCESSED_ID')

# Initialize sessions
hypem_session = requests.Session()
hypem_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
})

squarespace_session = requests.Session()
squarespace_session.headers.update({
    'Authorization': f'Bearer {SQUARESPACE_API_KEY}',
    'User-Agent': 'Hypem-Squarespace-Integration/1.0',
    'Content-Type': 'application/json'
})

# Logging function for better visibility in GitHub Actions
def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def get_liked_tracks(limit=5):
    """Fetch the user's most recently liked tracks from Hypem"""
    url = f"https://hypem.com/api/loved_items_by_user_name?user_name={HYPEM_USERNAME}&page=1&count={limit}"
    
    try:
        response = hypem_session.get(url)
        response.raise_for_status()
        
        # Hypem returns JSON with some extra characters at the beginning
        content = response.text
        if content.startswith('while(1);'):
            content = content[9:]  # Remove the while(1); prefix
            
        data = json.loads(content)
        return data
    except Exception as e:
        log(f"Error fetching liked tracks: {e}")
        return None

def find_squarespace_ids():
    """Find the website ID and blog collection ID"""
    website_id = None
    collection_id = None
    
    try:
        # Get the website ID
        log("Trying to find website ID...")
        url = "https://api.squarespace.com/1.0/websites"
        response = squarespace_session.get(url)
        response.raise_for_status()
        websites = response.json().get('websites', [])
        
        # Print all website data for debugging
        log(f"Found {len(websites)} websites")
        for i, website in enumerate(websites):
            log(f"Website {i+1}: {json.dumps(website)}")
        
        # Try to find website by domain
        for website in websites:
            domains = website.get('domains', [])
            for domain in domains:
                if isinstance(domain, dict) and SQUARESPACE_DOMAIN in domain.get('domain', ''):
                    website_id = website.get('id')
                    log(f"Found website ID: {website_id}")
                    break
            if website_id:
                break
        
        if not website_id and websites:
            # If we couldn't find by domain but have websites, use the first one
            website_id = websites[0].get('id')
            log(f"Using first website ID found: {website_id}")
        
        # Find the collection ID (blog)
        if website_id:
            log("Trying to find blog collection ID...")
            url = f"https://api.squarespace.com/1.0/websites/{website_id}/collections"
            response = squarespace_session.get(url)
            response.raise_for_status()
            collections = response.json().get('collections', [])
            
            # Print all collections for debugging
            log(f"Found {len(collections)} collections")
            for i, collection in enumerate(collections):
                log(f"Collection {i+1}: {json.dumps(collection)}")
            
            # Look for blog collections
            blog_collections = [c for c in collections if c.get('type') == 'blog']
            
            if blog_collections:
                # Use the first blog collection
                collection_id = blog_collections[0].get('id')
                log(f"Found blog collection ID: {collection_id}")
        
        return website_id, collection_id
    except Exception as e:
        log(f"Error finding Squarespace IDs: {e}")
        return None, None

def create_simple_post(website_id, collection_id, title, body):
    """Create a very simple Squarespace blog post for testing"""
    if not website_id or not collection_id:
        log("Missing website ID or collection ID. Cannot create post.")
        return None
    
    try:
        # Prepare post data (very simple)
        post_data = {
            "type": "blog",
            "title": title,
            "body": body,
            "status": "PUBLISHED"
        }
        
        # Create the post using Squarespace API
        url = f"https://api.squarespace.com/1.0/websites/{website_id}/collections/{collection_id}/items"
        
        log(f"Creating post with title: {title}")
        log(f"API endpoint: {url}")
        log(f"Post data: {json.dumps(post_data)}")
        
        response = squarespace_session.post(url, json=post_data)
        response.raise_for_status()
        
        post_info = response.json()
        log(f"Successfully created post with ID {post_info.get('id')}")
        return post_info.get('id')
    except Exception as e:
        log(f"Error creating Squarespace post: {e}")
        log(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
        log(f"Response text: {getattr(e.response, 'text', 'N/A')}")
        return None

def main():
    # Find Squarespace IDs
    website_id, collection_id = find_squarespace_ids()
    
    if not website_id or not collection_id:
        log("Could not determine website ID or collection ID. Exiting.")
        return
    
    # Create a test post to verify basic functionality
    test_post_id = create_simple_post(
        website_id, 
        collection_id,
        "Test Post - Hypem Integration", 
        "<p>This is a test post to verify the Hypem to Squarespace integration.</p>"
    )
    
    if not test_post_id:
        log("Failed to create test post. Exiting.")
        return
    
    log("Test successful! Now we can implement the full integration.")

if __name__ == "__main__":
    main()
