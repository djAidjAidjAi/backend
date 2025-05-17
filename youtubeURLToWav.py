import yt_dlp
import subprocess

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
