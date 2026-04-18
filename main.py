import os
import time
import requests
import sys
import json
from io import BytesIO
from PIL import Image
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
try:
    with open(SETTINGS_FILE, 'r') as f:
        saved_settings = json.load(f)
        loaded_brightness = saved_settings.get('brightness', 100)
except FileNotFoundError:
    pass

# Pre-create the settings file as root so the unprivileged thread can write to it later
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump({'brightness': loaded_brightness}, f)
# Ensure it's writable by all users (so the dropped 'dietpi' user can edit it)
os.chmod(SETTINGS_FILE, 0o666)

# Shared state between Web UI and Matrix Loop
app_state = {
    'brightness': loaded_brightness,
    'shutdown': False,
    'restart': False
}

# Spotipy OAuth configuration
sp_oauth = SpotifyOAuth(
    scope='user-read-currently-playing user-read-playback-state',
    open_browser=False,
    redirect_uri="http://spotify-matrix.local/callback" # Change matrix IP if mDNS isn't working
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
    print("Not logged into Spotify yet. Visit http://<raspberry-pi-ip> to do first-time setup.")

# 3. Main Loop
last_url = None
print('Spotify MVP Running... Connect to http://<pi-ip> to configure.')

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

                    matrix.SetImage(img)
                    last_url = url
            else:
                # Clear matrix if paused/stopped
                if last_url:
                    matrix.Clear()
                    last_url = None
        except Exception as e:
            print(f'Error: {e}')
        time.sleep(1)
except KeyboardInterrupt:
    matrix.Clear()
