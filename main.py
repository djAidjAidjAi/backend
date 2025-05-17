from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import List
from google.genai import create_user_content, Part
from google import genai
import base64

# Initialize client with your API key (set this in your environment)
api_key = os.getenv('GEMINI_API_KEY')

load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
))

client = genai.Client()

app = Flask(__name__)

def generate_text(prompt: str, songs: List[str]):
    contents = [
        create_user_content([prompt, *songs])
    ]
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=str + "".join(songs),
    )
    return response.text

@app.route("/tracks")
def get_tracks():
    # Get playlist URL from query parameter
    playlist_url = request.args.get('url')
    if not playlist_url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400

    try:
        # Extract playlist URI
        playlist_uri = playlist_url.split('/')[-1].split('?')[0]

        # Retrieve all tracks with pagination
        results = sp.playlist_tracks(playlist_uri)
        tracks = results['items']
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])

        # Format track info
        song_list = []
        for item in tracks:
            track = item['track']
            if track:
                song_list.append({
                    "title": track['name'],
                    "artist": track['artists'][0]['name']
                })

        response = generate_text("Generate the vibes of this song, based on the songs I send you", song_list)
        print(response)

        return jsonify(song_list)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

print("Everything should be working now")
app.run()
