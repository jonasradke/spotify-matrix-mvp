import os
import time
import requests
import sys
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
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
loaded_idle_mode = "clock"
loaded_idle_color = "#1ED760"
loaded_idle_block_start = "00:00"
loaded_idle_block_end = "00:00"
try:
    with open(SETTINGS_FILE, 'r') as f:
        saved_settings = json.load(f)
        loaded_brightness = saved_settings.get('brightness', 100)
        loaded_progress = saved_settings.get('show_progress', False)
        loaded_progress_color = saved_settings.get('progress_color', '#1ED760')
        loaded_idle_mode = saved_settings.get('idle_mode', 'clock')
        loaded_idle_color = saved_settings.get('idle_color', '#1ED760')
        loaded_idle_block_start = saved_settings.get('idle_block_start', '00:00')
        loaded_idle_block_end = saved_settings.get('idle_block_end', '00:00')
except FileNotFoundError:
    pass

# Pre-create the settings file as root so the unprivileged thread can write to it later
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump({
            'brightness': loaded_brightness,
            'show_progress': loaded_progress,
            'progress_color': loaded_progress_color,
            'idle_mode': loaded_idle_mode,
            'idle_color': loaded_idle_color,
            'idle_block_start': loaded_idle_block_start,
            'idle_block_end': loaded_idle_block_end
        }, f)
# Ensure it's writable by all users (so the dropped 'dietpi' user can edit it)
os.chmod(SETTINGS_FILE, 0o666)

# Shared state between Web UI and Matrix Loop
app_state = {
    'brightness': loaded_brightness,
    'show_progress': loaded_progress,
    'progress_color': loaded_progress_color,
    'shutdown': False,
    'restart': False,
    'reload_spotify': False,
    'track_name': None,
    'artist_name': None,
    'album_art': None,
    'is_playing': False,
    'progress_ms': 0,
    'duration_ms': 0,
    'idle_mode': loaded_idle_mode,
    'idle_color': loaded_idle_color,
    'idle_block_start': loaded_idle_block_start,
    'idle_block_end': loaded_idle_block_end
}


def parse_hhmm_to_minutes(value, fallback):
    try:
        hour, minute = value.split(':')
        return int(hour) * 60 + int(minute)
    except Exception:
        return fallback


def idle_is_blocked_now(state):
    start = parse_hhmm_to_minutes(state.get('idle_block_start', '00:00'), 0)
    end = parse_hhmm_to_minutes(state.get('idle_block_end', '00:00'), 0)
    if start == end:
        return False

    now_tm = time.localtime()
    now_minutes = now_tm.tm_hour * 60 + now_tm.tm_min

    if start < end:
        return start <= now_minutes < end

    return now_minutes >= start or now_minutes < end


def render_idle_image(state):
    mode = state.get('idle_mode', 'clock')
    img = Image.new('RGB', (64, 64), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    def hex_to_rgb(value):
        try:
            value = value.lstrip('#')
            if len(value) != 6:
                return (29, 185, 84)
            return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
        except Exception:
            return (29, 185, 84)

    def load_font(size):
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        ]
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
        return ImageFont.load_default()

    def draw_centered_text(text, y, font, fill):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = max(0, (64 - text_width) // 2)
        draw.text((x, y), text, fill=fill, font=font)

    idle_rgb = hex_to_rgb(state.get('idle_color', '#1ED760'))
    idle_secondary = tuple(max(40, int(c * 0.65)) for c in idle_rgb)

    if mode == 'off':
        return img

    if mode == 'clock':
        clock_font = load_font(16)
        draw_centered_text(time.strftime('%H:%M'), 24, clock_font, idle_rgb)
        return img

    if mode == 'clock_date':
        clock_font = load_font(15)
        date_font = load_font(10)
        draw_centered_text(time.strftime('%H:%M'), 17, clock_font, idle_rgb)
        draw_centered_text(time.strftime('%d.%m'), 37, date_font, idle_secondary)
        return img

    # Fallback to clock for unknown mode values
    clock_font = load_font(16)
    draw_centered_text(time.strftime('%H:%M'), 24, clock_font, idle_rgb)
    return img

# Spotipy OAuth configuration
sp_oauth = SpotifyOAuth(
    scope='user-read-currently-playing user-read-playback-state user-modify-playback-state',
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
opts.pwm_bits = 11
opts.brightness = app_state['brightness']
opts.gpio_slowdown = 1
opts.drop_privileges = True
opts.drop_priv_user = 'dietpi'
opts.drop_priv_group = 'dietpi'
opts.show_refresh_rate = 0
opts.limit_refresh_rate_hz = 165
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
idle_active = False
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
            if track and track.get('is_playing') and track.get('item'):
                app_state['is_playing'] = True
                app_state['track_name'] = track['item']['name']
                app_state['artist_name'] = track['item']['artists'][0]['name'] if track['item']['artists'] else 'Unknown'
                app_state['progress_ms'] = track.get('progress_ms', 0) or 0
                app_state['duration_ms'] = track['item'].get('duration_ms', 0) or 0
                
                images = track['item']['album']['images']
                if not images:
                    continue
                
                url = images[-1]['url']  # 64x64 smallest image for matrix
                app_state['album_art'] = images[0]['url']  # 640x640 largest image for Web UI

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
                idle_active = False
            else:
                app_state['is_playing'] = False
                app_state['track_name'] = None
                app_state['artist_name'] = None
                app_state['album_art'] = None
                app_state['progress_ms'] = 0
                app_state['duration_ms'] = 0

                show_idle = app_state.get('idle_mode', 'clock') != 'off' and not idle_is_blocked_now(app_state)
                if show_idle:
                    matrix.SetImage(render_idle_image(app_state))
                    idle_active = True
                
                # Clear matrix if paused/stopped with idle disabled in this time window
                if not show_idle and (last_url or idle_active):
                    matrix.Clear()
                    idle_active = False
                    last_url = None
                    last_img = None
        except Exception as e:
            print(f'Error: {e}')
        time.sleep(1)
except KeyboardInterrupt:
    matrix.Clear()
