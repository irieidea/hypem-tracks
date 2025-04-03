from playwright.async_api import async_playwright
import asyncio
import os
import json
from datetime import datetime

class HypemScraper:
    def __init__(self):
        self.username = os.getenv('HYPEM_USERNAME')
        self.password = os.getenv('HYPEM_PASSWORD')
        self.data_file = 'tracks.json'

    async def setup(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def login(self):
        await self.page.goto('https://hypem.com/login')
        await self.page.fill('input[name="username"]', self.username)
        await self.page.fill('input[name="password"]', self.password)
        await self.page.click('button[type="submit"]')
        await self.page.wait_for_load_state('networkidle')

    async def get_liked_tracks(self):
        await self.page.goto(f'https://hypem.com/{self.username}/favorites')
        await self.page.wait_for_load_state('networkidle')

        tracks = await self.page.evaluate("""
            () => {
                const tracks = [];
                document.querySelectorAll('.track').forEach(track => {
                    tracks.push({
                        artist: track.querySelector('.artist').innerText,
                        title: track.querySelector('.track-title').innerText,
                        artwork: track.querySelector('img')?.src,
                        postUrl: track.querySelector('.blog-link')?.href,
                        blogName: track.querySelector('.blog-link')?.innerText,
                        timestamp: track.getAttribute('data-timestamp')
                    });
                });
                return tracks;
            }
        """)
        return tracks

    async def save_tracks(self, tracks):
        existing = []
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                existing = json.load(f)

        timestamp = datetime.now().isoformat()
        new_tracks = [{**track, 'fetched_at': timestamp} for track in tracks]
        
        all_tracks = new_tracks + existing
        with open(self.data_file, 'w') as f:
            json.dump(all_tracks, f, indent=2)

    async def cleanup(self):
        await self.browser.close()
        await self.playwright.stop()

    async def run(self):
        try:
            await self.setup()
            await self.login()
            tracks = await self.get_liked_tracks()
            await self.save_tracks(tracks)
            return tracks
        finally:
            await self.cleanup()
