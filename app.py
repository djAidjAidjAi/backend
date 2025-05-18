from flask import Flask, request, jsonify, send_file, Response, stream_with_context
from flask_cors import CORS
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
CORS(app)

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
    print("Got request from the client")
    # Get playlist URL from query parameter
    youtube_url = request.args.get('youtube')
    playlist_url = request.args.get('url')
    if not playlist_url and not youtube_url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400

    try:
        # Extract playlist URI
        # playlist_uri = playlist_url.split('/')[-1].split('?')[0]

        # Retrieve all tracks with pagination
        print("1")
        results = sp.playlist_tracks(playlist_url)
        print("2")
        tracks = results['items']
        print("3")
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])

        print("4")
        song_str = "; ".join(
            f"{item['track']['name']} by {item['track']['artists'][0]['name']}"
            for item in tracks
            if item.get('track')
            )       #         })

        print("parsed the songs in the playlist", song_str)
        response = generate_text("""
                                 Please describe the specific characteristics of the songs' emotions accurately and summarize them in one sentence, 
                                 focusing on the effect of the highlight atmosphere of the songs mentioned on the overall atmosphere of the song. 
                                 Bear in mind that you are summing up the moods and atmosphers of the songs, and summarizing them all in one sentence. 
                                 Also bear in mind that this one sentence is the only output expected, also bear in mind that you do not need to
                                 reference the artist or title, just describe the vibes; """, song_str)
        print("5")
        print(response)

        audio_bytes = get_audio_bytes(youtube_url)
        print("6")

        files = {
            "audio_file": ("input.wav", BytesIO(audio_bytes), "audio/wav")
        }
        data = {
            "prompt1": response,
            "prompt2": "" 
        }
        print("Music model url is ", music_model_url, "Asking music model")
        music_response = requests.post(
            music_model_url + "/generate",
            files=files,
            data=data,
            stream=True  # IMPORTANT for streaming response
        )
        music_response.raise_for_status()

        # Return streamed response as file download to the client
        return Response(
            stream_with_context(music_response.iter_content(chunk_size=8192)),
            content_type=music_response.headers.get('Content-Type', 'audio/wav'),
            headers={"Content-Disposition": "attachment; filename=output.wav"}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's port or fallback to 5000
    app.run(host="0.0.0.0", port=port)
