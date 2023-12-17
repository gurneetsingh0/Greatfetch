# Import necessary modules
from flask import Flask, request, render_template, jsonify
from pytube import YouTube
import os
import subprocess
import re
import threading

app = Flask(__name__)

# Function to sanitize file names
def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', '', filename)

# Dictionary to store video info and streams for caching
video_info_cache = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch_info', methods=['POST'])
def fetch_info():
    uservidurl = request.form.get('uservidurl')
    link = uservidurl

    if link in video_info_cache:
        video_info = video_info_cache[link]
    else:
        try:
            youtube_1 = YouTube(link)
            title = youtube_1.title
            thumbnail = youtube_1.thumbnail_url
            video_info = {'title': title, 'thumbnail': thumbnail}
            video_info_cache[link] = video_info
        except Exception as e:
            return jsonify({'error': str(e)})

    return jsonify(video_info)

# Function to download video and audio streams
def download_streams(link, resolution):
    try:
        youtube_1 = YouTube(link)
        title = sanitize_filename(youtube_1.title)  # Sanitize the title
        thumbnail = youtube_1.thumbnail_url

        # Get the stream with the selected resolution
        if resolution == '0':
            selected_stream = youtube_1.streams.filter(res='144p', progressive=True, file_extension='mp4').first()
        elif resolution == '1':
            selected_stream = youtube_1.streams.filter(res='360p', progressive=True, file_extension='mp4').first()
        elif resolution == '2':
            selected_stream = youtube_1.streams.filter(res='720p', progressive=True, file_extension='mp4').first()
        elif resolution == '3':
            # Get the best available video and audio streams (adaptive)
            video_stream = youtube_1.streams.filter(adaptive=True, file_extension='mp4').first()
            audio_stream = youtube_1.streams.filter(adaptive=True, only_audio=True, file_extension='webm').first()

            if video_stream and audio_stream:
                # Download the video and audio streams with explicit extensions
                video_stream.download(output_path='downloads', filename=f'{title}_video.mp4')
                audio_stream.download(output_path='downloads', filename=f'{title}_audio.webm')

                # Use FFmpeg to merge video and audio into a playable mp4 file
                video_file = os.path.join('downloads', f'{title}_video.mp4')
                audio_file = os.path.join('downloads', f'{title}_audio.webm')
                output_file = os.path.join('downloads', f'{title}.mp4')
                subprocess.run(['ffmpeg', '-i', video_file, '-i', audio_file, '-c:v', 'copy', '-c:a', 'aac', output_file])

                # Clean up temporary files
                os.remove(video_file)
                os.remove(audio_file)

                response_data = {'title': title, 'thumbnail': thumbnail}
                return response_data
            else:
                return {'error': 'Unable to find video or audio streams'}

        else:
            return {'error': 'Invalid resolution selection'}

    except Exception as e:
        return {'error': str(e)}

@app.route('/download', methods=['POST'])
def initiate_download():
    uservidurl = request.form.get('uservidurl')
    resolution = request.form.get('resolution')

    # Create a thread to download streams
    download_thread = threading.Thread(target=download_streams, args=(uservidurl, resolution))
    download_thread.start()

    return jsonify({'message': 'Download initiated. Please wait.'})

if __name__ == '__main__':
    app.run(debug=True)
