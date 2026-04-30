#!/bin/bash

# Spotify Matrix MVP - Installation Script
# This script sets up the Spotify Matrix application on a fresh Raspberry Pi or Linux system

set -e  # Exit on error

echo "🎵 Spotify Matrix MVP - Installation Script"
echo "==========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root (required for systemd service setup and GPIO)
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}✗ This script must be run as root (use: sudo ./install.sh)${NC}"
  exit 1
fi

# Determine the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Install directory: $SCRIPT_DIR"
echo ""

# Step 1: Update system packages
echo -e "${YELLOW}[1/7] Updating system packages...${NC}"
apt-get update
apt-get upgrade -y
echo -e "${GREEN}✓ System packages updated${NC}"
echo ""

# Step 2: Install system dependencies
echo -e "${YELLOW}[2/8] Installing system dependencies...${NC}"
apt-get install -y \
  python3 \
  python3-pip \
  python3-dev \
  git \
  build-essential \
  cython3 \
  openssl \
  curl

echo -e "${GREEN}✓ System dependencies installed${NC}"
echo ""

# Step 2.5: Create Python virtual environment
echo -e "${YELLOW}[2.5/9] Creating Python virtual environment...${NC}"
python3 -m venv "$SCRIPT_DIR/.venv"
echo -e "${GREEN}✓ Virtual environment created${NC}"
echo ""

# Step 2.6: Install rpi-rgb-led-matrix Python bindings in venv
echo -e "${YELLOW}[2.6/9] Installing rpi-rgb-led-matrix Python bindings...${NC}"
"$SCRIPT_DIR/.venv/bin/pip" install --upgrade pip setuptools wheel
"$SCRIPT_DIR/.venv/bin/pip" install git+https://github.com/hzeller/rpi-rgb-led-matrix.git
echo -e "${GREEN}✓ rpi-rgb-led-matrix Python bindings installed${NC}"
echo ""

# Step 3: Install Python dependencies in venv
echo -e "${YELLOW}[3/9] Installing Python dependencies...${NC}"
cd "$SCRIPT_DIR"

if [ -f "requirements.txt" ]; then
  "$SCRIPT_DIR/.venv/bin/pip" install -r requirements.txt
  echo -e "${GREEN}✓ Python dependencies installed${NC}"
else
  echo -e "${RED}✗ requirements.txt not found in $SCRIPT_DIR${NC}"
  exit 1
fi
echo ""

# Step 4: Create .env file if it doesn't exist
echo -e "${YELLOW}[4/9] Setting up environment configuration...${NC}"
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo "SPOTIFY_CLIENT_ID=your_client_id_here" > "$SCRIPT_DIR/.env"
  echo "SPOTIFY_CLIENT_SECRET=your_client_secret_here" >> "$SCRIPT_DIR/.env"
  echo "SPOTIFY_REDIRECT_URI=https://matrix.local/callback" >> "$SCRIPT_DIR/.env"
  echo -e "${YELLOW}⚠ Created .env file with placeholders${NC}"
  echo -e "${YELLOW}  Please edit $SCRIPT_DIR/.env and add your Spotify credentials${NC}"
else
  echo -e "${GREEN}✓ .env file already exists${NC}"
fi
echo ""

# Step 5: Generate SSL certificates if they don't exist
echo -e "${YELLOW}[5/9] Setting up SSL certificates...${NC}"
CERT_FILE="$SCRIPT_DIR/cert.pem"
KEY_FILE="$SCRIPT_DIR/key.pem"

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
  openssl req -x509 -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days 3650 \
    -nodes \
    -subj "/CN=matrix.local"
  
  chmod 644 "$CERT_FILE"
  chmod 644 "$KEY_FILE"
  echo -e "${GREEN}✓ SSL certificates generated${NC}"
else
  echo -e "${GREEN}✓ SSL certificates already exist${NC}"
fi
echo ""

# Step 6: Create dietpi user if it doesn't exist (for privilege dropping)
echo -e "${YELLOW}[6/9] Setting up system user for matrix...${NC}"
if ! id "dietpi" &>/dev/null; then
  useradd -r -s /bin/bash -d /home/dietpi -m dietpi
  echo -e "${GREEN}✓ Created dietpi user${NC}"
else
  echo -e "${GREEN}✓ dietpi user already exists${NC}"
fi

# Step 7: Create default settings.json if it doesn't exist
echo -e "${YELLOW}[7/9] Initializing settings file...${NC}"
# Create settings.json with default values if it doesn't exist
if [ ! -f "$SCRIPT_DIR/settings.json" ]; then
  cat > "$SCRIPT_DIR/settings.json" << 'EOF'
{
  "brightness": 100,
  "show_progress": false,
  "progress_color": "#1ED760",
  "idle_mode": "clock",
  "idle_color": "#1ED760",
  "idle_block_start": "00:00",
  "idle_block_end": "00:00",
  "matrix_rows": 64,
  "matrix_cols": 64,
  "gpio_slowdown": 1,
  "limit_refresh_rate_hz": 165,
  "pwm_lsb_nanoseconds": 75,
  "chain_length": 1,
  "parallel": 1,
  "show_refresh_rate": false
}
EOF
  chmod 666 "$SCRIPT_DIR/settings.json"
  echo -e "${GREEN}✓ Created settings.json with defaults${NC}"
else
  echo -e "${GREEN}✓ settings.json already exists${NC}"
fi
echo ""

# Step 8: Install and enable systemd service
echo -e "${YELLOW}[8/9] Setting up systemd service...${NC}"
if [ -f "$SCRIPT_DIR/spotify-matrix.service" ]; then
  # Replace the working directory in the service file with the actual install path
  sed "s|/path/to/spotify-matrix-mvp|$SCRIPT_DIR|g" "$SCRIPT_DIR/spotify-matrix.service" > /etc/systemd/system/spotify-matrix.service
  
  systemctl daemon-reload
  systemctl enable spotify-matrix.service
  echo -e "${GREEN}✓ Systemd service installed and enabled${NC}"
else
  echo -e "${RED}✗ spotify-matrix.service not found${NC}"
  echo -e "${YELLOW}  You may need to install the service manually${NC}"
fi
echo ""

# Step 9: Set file permissions for dietpi user
echo -e "${YELLOW}[9/9] Setting up file permissions...${NC}"
chown -R dietpi:dietpi "$SCRIPT_DIR"
chmod -R 755 "$SCRIPT_DIR"
chmod 644 "$SCRIPT_DIR/settings.json"
chmod 644 "$SCRIPT_DIR/.env" 2>/dev/null || true
chmod 644 "$SCRIPT_DIR/cert.pem"
chmod 644 "$SCRIPT_DIR/key.pem"
echo -e "${GREEN}✓ File permissions configured${NC}"
echo ""

# Final instructions
echo -e "${GREEN}==========================================="
echo "✓ Installation Complete!"
echo "==========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit .env file with your Spotify API credentials:"
echo "   nano $SCRIPT_DIR/.env"
echo ""
echo "2. Start the service:"
echo "   systemctl start spotify-matrix"
echo ""
echo "3. Check service status:"
echo "   systemctl status spotify-matrix"
echo ""
echo "4. View logs:"
echo "   journalctl -u spotify-matrix -f"
echo ""
echo "5. Access the web UI at:"
echo "   https://matrix.local or https://<your-pi-ip>"
echo ""
echo -e "${YELLOW}Configuration files:${NC}"
echo "  - Settings: $SCRIPT_DIR/settings.json"
echo "  - Environment: $SCRIPT_DIR/.env"
echo "  - SSL Certs: $SCRIPT_DIR/cert.pem, $SCRIPT_DIR/key.pem"
echo ""
