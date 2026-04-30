# Spotify Matrix MVP - Installation & Quick Start Guide

This guide walks you through installing Spotify Matrix MVP on a fresh Raspberry Pi or Linux system with a 64x64 RGB LED matrix.

## Prerequisites

- Raspberry Pi 4+ or similar Linux system (DietPi, Raspbian, etc.)
- 64x64 RGB LED matrix with Adafruit HAT driver
- Internet connection
- Spotify Developer account (for API credentials)
- SSH access or local terminal

## Quick Install (Automated)

The fastest way to get up and running:

```bash
# 1. Clone the repository
git clone https://github.com/jonasradke/spotify-matrix-mvp.git
cd spotify-matrix-mvp

# 2. Run the installer (requires sudo)
sudo ./install.sh

# 3. Configure Spotify credentials
nano .env
# Add your SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET
# Get these from: https://developer.spotify.com/dashboard

# 4. Start the service
sudo systemctl start spotify-matrix

# 5. Access the web UI
# Open a browser and navigate to: https://matrix.local (or https://<your-pi-ip>)
```

## What the Install Script Does

The `install.sh` script automates the following setup steps:

1. **Updates system packages** - Ensures your system is current
2. **Installs dependencies** - Python, build tools, OpenSSL, and Cython
2.5. **Creates Python virtual environment** - Isolated Python environment at `.venv/`
2.6. **Installs rpi-rgb-led-matrix** - Installs hzeller's LED matrix Python bindings in the venv (uses scikit-build-core)
3. **Installs Python packages** - From requirements.txt into the venv (Spotipy, Bottle, etc.)
4. **Creates .env file** - Template for Spotify API credentials
5. **Generates SSL certificates** - Self-signed certs for HTTPS on matrix.local
6. **Sets up system user** - Creates `dietpi` user for privilege dropping
7. **Initializes settings** - Creates default settings.json configuration
8. **Installs systemd service** - Enables auto-start on boot using venv Python
9. **Sets file permissions** - Configures ownership and permissions for the dietpi user

## Manual Installation (Step-by-Step)

If you prefer more control or need to troubleshoot:

**Note:** This installation uses a Python virtual environment (`.venv/`) for package isolation. This avoids PEP 668 restrictions and keeps dependencies separate from the system Python.

```bash
# 1. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install system dependencies
sudo apt-get install -y python3 python3-venv python3-pip python3-dev git build-essential \
  python3-pil cython3 openssl curl

# 3. Clone and navigate to repo
git clone https://github.com/jonasradke/spotify-matrix-mvp.git
cd spotify-matrix-mvp

# 4. Create Python virtual environment
python3 -m venv .venv

# 5. Install rpi-rgb-led-matrix Python bindings in venv
.venv/bin/pip install --upgrade pip setuptools wheel
.venv/bin/pip install git+https://github.com/hzeller/rpi-rgb-led-matrix.git

# 6. Install Python dependencies in venv
.venv/bin/pip install -r requirements.txt

# 7. Create .env file with Spotify credentials
cat > .env << EOF
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=https://matrix.local/callback
EOF

# 8. Generate SSL certificates
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem \
  -days 3650 -nodes -subj "/CN=matrix.local"

# 9. Create system user
sudo useradd -r -s /bin/bash -d /home/dietpi -m dietpi

# 10. Copy systemd service
sudo cp spotify-matrix.service /etc/systemd/system/
sudo sed -i "s|/path/to/spotify-matrix-mvp|$(pwd)|g" /etc/systemd/system/spotify-matrix.service
sudo systemctl daemon-reload
sudo systemctl enable spotify-matrix

# 11. Set permissions
sudo chown -R dietpi:dietpi .
chmod 644 settings.json
chmod 644 .env
chmod 644 cert.pem key.pem

# 12. Start the service
sudo systemctl start spotify-matrix
```

## Getting Spotify API Credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new application
3. Accept the terms and create the app
4. Copy your **Client ID** and **Client Secret**
5. Add a Redirect URI: `https://matrix.local/callback` (or your Pi's IP)
6. Add these to your `.env` file

## Service Management

```bash
# Start the service
sudo systemctl start spotify-matrix

# Stop the service
sudo systemctl stop spotify-matrix

# Restart the service
sudo systemctl restart spotify-matrix

# Check status
sudo systemctl status spotify-matrix

# View logs
sudo journalctl -u spotify-matrix -f

# Enable/disable auto-start on boot
sudo systemctl enable spotify-matrix
sudo systemctl disable spotify-matrix
```

## Web Interface Access

Once running, access the settings and control interface at:

- **HTTPS**: `https://matrix.local` (or `https://<your-pi-ip>`)
- **Port**: 443 (HTTPS)

The interface includes:
- Spotify connection and playback controls
- Display settings (brightness, progress bar, idle mode)
- Matrix hardware configuration (rows, cols, refresh rate, etc.)
- Network settings (WiFi configuration)
- System management (updates, restart, shutdown)

## Configuration

All settings are stored in `settings.json` and can be managed via the web UI:

- **Display Settings**: Brightness, progress bar, idle mode options
- **Matrix Hardware**: Rows, columns, GPIO slowdown, refresh rate, chain length, parallel
- **Performance**: PWM settings, refresh rate limits
- **Advanced**: GPIO-specific tuning for your hardware
- **Spotify Credentials**: Loaded from `.env` using Spotipy's `SPOTIPY_*` variable names

## Troubleshooting

### Service won't start
```bash
# Check the logs
sudo journalctl -u spotify-matrix -n 50

# Check if port 443 is in use
sudo ss -tlnp | grep 443

# Manually run the script to see errors
cd /path/to/spotify-matrix-mvp
sudo python3 main.py
```

### Can't connect to web interface
- Verify Pi is on the network: `ping matrix.local` or use your Pi's IP address
- Check if service is running: `sudo systemctl status spotify-matrix`
- Ensure port 443 is open and accessible
- Try accessing via IP instead of hostname: `https://<your-pi-ip>`

### Spotify won't connect
- Verify Client ID and Secret in `.env` are correct
- Check that Redirect URI in Spotify Dashboard matches your setup
- Check logs for authentication errors

### LED matrix not displaying
- Verify matrix is powered separately (does not use Pi power)
- Check GPIO pins are configured correctly
- Verify libgpiod and rpi-rgb-led-matrix are installed
- Run with GPIO debug: check `opts.show_refresh_rate = 1` in settings

## PWA Features

This is now a Progressive Web App (PWA), meaning you can:
- Install as an app on your phone or tablet
- Add to home screen for quick access
- Works offline (basic caching of app shell)

## Next Steps

After installation, consider:
1. Tuning matrix hardware settings for your display
2. Setting up WiFi connection via web UI
3. Configuring idle mode and brightness to your preference
4. Linking your Spotify account
5. Setting up systemd service to auto-start on boot

## Support

For issues, feature requests, or contributions, see the [GitHub repository](https://github.com/jonasradke/spotify-matrix-mvp).

