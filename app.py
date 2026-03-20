import os
import mimetypes
import syncedlyrics
from flask import Flask, send_file, jsonify, render_template
from flask_cors import CORS
from mutagen.easyid3 import EasyID3
from waitress import serve

app = Flask(__name__, template_folder='templates')
CORS(app)

MUSIC_DIR = r"C:\Users\Owner\Documents\OtherProjects\MusiStore\Music" # Change this to your path

def get_metadata(full_path):
    parts = os.path.normpath(full_path).split(os.sep)
    fallback_album = parts[-2] if len(parts) > 2 else "Unknown Album"
    fallback_artist = parts[-3] if len(parts) > 3 else "Unknown Artist"
    
    try:
        audio = EasyID3(full_path)
        return {
            "title": audio.get("title", [os.path.basename(full_path)])[0],
            "artist": audio.get("artist", [fallback_artist])[0],
            "album": audio.get("album", [fallback_album])[0]
        }
    except:
        return {"title": os.path.basename(full_path), "artist": fallback_artist, "album": fallback_album}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/library')
def get_library():
    library = {}
    extensions = {'.mp3', '.flac', '.wav', '.ogg'}
    
    # Iterate through each folder in the Music directory
    for artist_entry in os.scandir(MUSIC_DIR):
        if artist_entry.is_dir():
            artist_name = artist_entry.name
            library[artist_name] = {}
            
            # Iterate through each folder inside the Artist folder (Albums)
            for album_entry in os.scandir(artist_entry.path):
                if album_entry.is_dir():
                    album_name = album_entry.name
                    library[artist_name][album_name] = []
                    
                    # Find all music files within that Album folder
                    for root, _, files in os.walk(album_entry.path):
                        for file in files:
                            if os.path.splitext(file)[1].lower() in extensions:
                                full_path = os.path.join(root, file)
                                rel_path = os.path.relpath(full_path, MUSIC_DIR).replace("\\", "/")
                                
                                # Try to get track title from metadata, fallback to filename
                                try:
                                    audio = EasyID3(full_path)
                                    title = audio.get("title", [file])[0]
                                except:
                                    title = file
                                    
                                library[artist_name][album_name].append({
                                    "id": rel_path,
                                    "title": title
                                })
    return jsonify(library)

@app.route('/api/lyrics/<path:track_id>')
def get_lyrics(track_id):
    full_path = os.path.join(MUSIC_DIR, track_id.replace("/", os.path.sep))
    lrc_path = os.path.splitext(full_path)[0] + ".lrc"
    if not os.path.exists(lrc_path):
        meta = get_metadata(full_path)
        try:
            lrc_data = syncedlyrics.search(f"{meta['title']} {meta['artist']}")
            if lrc_data:
                with open(lrc_path, 'w', encoding='utf-8') as f: f.write(lrc_data)
        except: pass
    if os.path.exists(lrc_path):
        with open(lrc_path, 'r', encoding='utf-8') as f: return jsonify({"lyrics": f.read()})
    return jsonify({"lyrics": "[00:00.00] No lyrics found."})

@app.route('/api/stream/<path:track_id>')
def stream(track_id):
    return send_file(os.path.join(MUSIC_DIR, track_id.replace("/", os.path.sep)))

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000, threads=12)
