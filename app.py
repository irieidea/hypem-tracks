from flask import Flask, render_template, jsonify
from scraper.hypem import HypemScraper
from apscheduler.schedulers.background import BackgroundScheduler
import os
from datetime import datetime
import json

app = Flask(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()

def load_tracks():
    """Load tracks from JSON file"""
    try:
        with open('tracks.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@app.route('/')
def index():
    tracks = load_tracks()
    return render_template('index.html', tracks=tracks)

@app.route('/api/tracks')
def get_tracks():
    tracks = load_tracks()
    return jsonify(tracks)

@app.route('/api/sync', methods=['POST'])
def sync_tracks():
    try:
        scraper = HypemScraper()
        tracks = await scraper.run()
        return jsonify({
            'success': True,
            'tracks_count': len(tracks)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
