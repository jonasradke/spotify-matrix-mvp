import os
import time
import requests
import sys
import json
from io import BytesIO
from PIL import Image, ImageDraw
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from rgbmatrix import RGBMatrix, RGBMatrixOptions

from web_ui import start_web_server

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')

# Load saved settings if they exist
loaded_brightness = 100
loaded_progress = False
loaded_progress_color = "#1ED760"
try:
    with open(SETTINGS_FILE, 'r') as f:
        saved_settings = json.load(f)
        loaded_brightness = saved_settings.get('brightness', 100)
        loaded_progress = saved_settings.get('show_progress', False)
        loaded_progress_color = saved_settings.get('progress_color', '#1ED760')
except FileNotFoundError:
    pass

# Pre-create the settings file as root so the unprivileged thread can write to it later
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump({'brightness': loaded_brightness, 'show_progress': loaded_progress, 'progress_color': loaded_progress_color}, f)
# Ensure it's writable by all users (so the dropped 'dietpi' user can edit it)
os.chmod(SETTINGS_FILE, 0o666)

# Shared state between Web UI and Matrix Loop
app_state = {
    'brightness': loaded_brightness,
    'show_progress': loaded_progress,
    'progress_color': loaded_progress_color,
    'shutdown': False,
    'restart': False,
    'reload_spotify': False
}

# Spotipy OAuth configuration
sp_oauth = SpotifyOAuth(
    scope='user-read-currently-playing user-read-playback-state',
    open_browser=False,
    redirect_uri="https://matrix.local/callback" # Change matrix IP if mDNS isn't working
)

# Start web interface in the background
start_web_server(app_state, sp_oauth)

# Give the background web server thread 2 seconds to actually start 
# and bind to Port 80 while the script still has 'root' privileges!
time.sleep(2)

# --- 2. Setup Matrix ---

load_dotenv()

# 1. Setup Matrix (Optimized for Pi Zero)
opts = RGBMatrixOptions()
opts.rows = 64
opts.cols = 64
opts.hardware_mapping = 'adafruit-hat-pwm'
opts.pwm_bits = 8
opts.brightness = app_state['brightness']
opts.gpio_slowdown = 0
opts.drop_privileges = True
opts.drop_priv_user = 'dietpi'
opts.drop_priv_group = 'dietpi'
opts.show_refresh_rate = 1
opts.limit_refresh_rate_hz = 120
opts.pwm_lsb_nanoseconds =75

matrix = RGBMatrix(options=opts)

# 2. Setup Spotify
try:
    # If .cache exists, we can init Spotipy and poll.
    sp = Spotify(auth_manager=sp_oauth)
    sp.current_playback()  # Check token validity
except Exception as e:
    sp = None
    print("Not logged into Spotify yet. Visit https://<raspberry-pi-ip> to do first-time setup.")

# 3. Main Loop
last_url = None
last_img = None
print('Spotify MVP Running... Connect to https://<pi-ip> to configure.')

try:
    while True:
        # Check if the Web UI requested a restart
        if app_state['restart']:
            print("Restarting gracefully per Web UI request...")
            matrix.Clear()
            sys.exit(0)

        # Sync live brightness changes
        if matrix.brightness != app_state['brightness']:
            matrix.brightness = app_state['brightness']
            # We don't need to force matrix.SetImage(last_img) here anymore 
            # because the progress bar loop below will redraw it instantly anyway!

        # Handle live Spotify linking and unlinking
        if app_state.get('reload_spotify'):
            app_state['reload_spotify'] = False
            print("Reloading Spotify credentials live...")
            try:
                sp = Spotify(auth_manager=sp_oauth)
                sp.current_playback()
            except Exception as e:
                sp = None
                matrix.Clear()
                last_url = None
                last_img = None
                print("Spotify unlinked or invalid token.")

        try:
            if not sp:
                # Still waiting on a valid token from the web UI
                time.sleep(2)
                continue

            track = sp.current_playback()

            # Check if music is playing
            if track and track.get('is_playing'):
                url = track['item']['album']['images'][-1]['url']

                # Only redraw if the song changed
                if url != last_url:
                    res = requests.get(url, timeout=5)
                    img = Image.open(BytesIO(res.content)).convert('RGB')
                    # Only resize if Spotify gave us a weird size.
                    # NEAREST is the fastest possible resize method for a Pi Zero.
                    if img.size != (64, 64):
                        img = img.resize((64, 64), Image.Resampling.NEAREST)

                    last_url = url
                    last_img = img

                # Dynamic progress bar redrawing over the cached image
                display_img = last_img.copy()
                if app_state.get('show_progress'):
                    progress_ms = track.get('progress_ms', 0) or 0
                    duration_ms = track['item'].get('duration_ms', 1) or 1
                    width = int((progress_ms / duration_ms) * 64)
                    draw = ImageDraw.Draw(display_img)
                    draw.line((0, 63, width, 63), fill=app_state.get('progress_color', '#1ED760'))
                
                matrix.SetImage(display_img)
            else:
                # Clear matrix if paused/stopped
                if last_url:
                    matrix.Clear()
                    last_url = None
                    last_img = None
        except Exception as e:
            print(f'Error: {e}')
        time.sleep(1)
except KeyboardInterrupt:
    matrix.Clear()
