from flask import Flask, render_template
import json
import os

app = Flask(__name__)

def load_tracks():
    """Load tracks from local JSON file"""
    try:
        with open('tracks.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@app.route('/')
def index():
    tracks = load_tracks()
    return render_template('index.html', tracks=tracks)

if __name__ == '__main__':
    app.run(debug=True)
