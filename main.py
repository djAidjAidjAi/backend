from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import List
from google import genai
import yt_dlp
import subprocess
from io import BytesIO
import base64
import requests

load_dotenv()

# Initialize client with your API key (set this in your environment)
gemini = os.getenv('GEMINI_API_KEY')
music_model_url = os.getenv('MUSIC_MODEL_URL')


sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
))

client = genai.Client(api_key=gemini)

app = Flask(__name__)

def get_audio_bytes(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'outtmpl': '-',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    # Use ffmpeg to stream the audio directly into memory
    process = subprocess.Popen(
        ['ffmpeg', '-i', audio_url, '-f', 'wav', '-'],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    audio_bytes = process.stdout.read()
    return audio_bytes


def generate_text(prompt: str, songs: str):

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt + songs,
    )
    return response.text

@app.route("/tracks")
def get_tracks():
    # Get playlist URL from query parameter
    youtube_url = request.args.get('youtube')
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

        song_str = "; ".join(
            f"{item['track']['name']} by {item['track']['artists'][0]['name']}"
            for item in tracks
            if item.get('track')
            )       #         })

        response = generate_text("""
                                 Please describe the specific characteristics of the songs' emotions accurately and summarize them in one sentence, 
                                 focusing on the effect of the highlight atmosphere of the songs mentioned on the overall atmosphere of the song. 
                                 Bear in mind that you are summing up the moods and atmosphers of the songs, and summarizing them all in one sentence. 
                                 Also bear in mind that this one sentence is the only output expected; """, song_str)
        print(response)

        audio_bytes = get_audio_bytes(youtube_url)

        files = {
            "audio_file": ("input.wav", BytesIO(audio_bytes), "audio/wav")
        }
        data = {
            "prompt1": response,
            "prompt2": "" 
        }
        print("Music model url is ", music_model_url)
        response = requests.post(music_model_url + "/generate", files=files, data=data)

        if response.ok:
            print("✅ Success:", response.json())
        else:
            print("❌ Error:", response.status_code, response.text)

        return jsonify({"success": "Hurray!" }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

print("Everything should be working now")
app.run()
