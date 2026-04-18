import time
import requests
from io import BytesIO
from PIL import Image
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from rgbmatrix import RGBMatrix, RGBMatrixOptions

load_dotenv()

# 1. Setup Matrix (Optimized for Pi Zero)
opts = RGBMatrixOptions()
opts.rows = 64
opts.cols = 64
opts.hardware_mapping = 'adafruit-hat-pwm'
opts.pwm_bits = 8
opts.brightness = 100
opts.gpio_slowdown = 0
opts.drop_privileges = True
opts.drop_priv_user = 'dietpi'
opts.drop_priv_group = 'dietpi'
opts.show_refresh_rate = 1
opts.limit_refresh_rate_hz = 120
opts.pwm_lsb_nanoseconds =75

matrix = RGBMatrix(options=opts)

# 2. Setup Spotify
sp = Spotify(auth_manager=SpotifyOAuth(
    scope='user-read-currently-playing user-read-playback-state',
    open_browser=False
))

# 3. Main Loop
last_url = None
print('Spotify MVP Running... Press Ctrl+C to exit.')

try:
    while True:
        try:
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
