#!/bin/bash

# FreightView Dashboard Deployment Script
# Deploy to dash.bodytools.work
# Usage: sudo bash deploy.sh

set -e  # Exit on error

# Configuration
DOMAIN="dash.bodytools.work"
APP_NAME="freightview-dashboard"
APP_DIR="/opt/${APP_NAME}"
REPO_URL="https://github.com/grbod/dashboard.git"
STREAMLIT_PORT=8502
NGINX_SITE="/etc/nginx/sites-available/${DOMAIN}"
SERVICE_NAME="${APP_NAME}.service"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"
USER="www-data"  # Change this to your preferred user

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root (use sudo)"
   exit 1
fi

log_info "Starting deployment of FreightView Dashboard to ${DOMAIN}"

# Step 1: Update system packages
log_info "Updating system packages..."
apt-get update
apt-get upgrade -y

# Step 2: Install required system packages
log_info "Installing required system packages..."
apt-get install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Step 3: Create application directory
log_info "Setting up application directory at ${APP_DIR}..."
if [ -d "${APP_DIR}" ]; then
    log_warn "Directory ${APP_DIR} already exists. Backing up..."
    mv "${APP_DIR}" "${APP_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
fi
mkdir -p "${APP_DIR}"

# Step 4: Clone or update repository
log_info "Cloning repository from ${REPO_URL}..."
git clone "${REPO_URL}" "${APP_DIR}"
cd "${APP_DIR}"

# Step 5: Create Python virtual environment
log_info "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Step 6: Install Python dependencies
log_info "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Step 7: Create .streamlit directory for config
log_info "Creating Streamlit production configuration..."
mkdir -p .streamlit
cat > .streamlit/config.toml << 'EOF'
[server]
port = 8502
address = "127.0.0.1"
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
serverAddress = "dash.bodytools.work"
serverPort = 443

[theme]
base = "dark"
primaryColor = "#033f63"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#262730"
textColor = "#fafafa"
font = "sans serif"
EOF

# Step 8: Set up environment variables
log_info "Setting up environment variables..."
if [ ! -f "${APP_DIR}/.env" ]; then
    cat > "${APP_DIR}/.env" << 'EOF'
# FreightView Credentials
FREIGHTVIEW_CLIENT_ID=your_freightview_client_id
FREIGHTVIEW_CLIENT_SECRET=your_freightview_client_secret

# ShipStation Credentials
SS_CLIENT_ID=your_shipstation_api_key
SS_CLIENT_SECRET=your_shipstation_api_secret

# Airtable Credentials
AIRTABLE_API_KEY=your_airtable_api_key
AIRTABLE_BASE_ID=your_airtable_base_id
AIRTABLE_TABLE_NAME=Procurement
EOF
    log_warn "Created template .env file. Please update with actual credentials!"
    log_warn "Edit the file: nano ${APP_DIR}/.env"
fi

# Step 9: Set proper permissions
log_info "Setting file permissions..."
chown -R ${USER}:${USER} "${APP_DIR}"
chmod 600 "${APP_DIR}/.env"

# Step 10: Create systemd service
log_info "Creating systemd service..."
cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=FreightView Dashboard Streamlit App
After=network.target

[Service]
Type=simple
User=${USER}
Group=${USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin"
ExecStart=${APP_DIR}/venv/bin/streamlit run unified_dashboard.py --server.port ${STREAMLIT_PORT} --server.address 127.0.0.1
Restart=always
RestartSec=10
StandardOutput=append:/var/log/${APP_NAME}/output.log
StandardError=append:/var/log/${APP_NAME}/error.log

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
mkdir -p "/var/log/${APP_NAME}"
chown -R ${USER}:${USER} "/var/log/${APP_NAME}"

# Step 11: Configure Nginx
log_info "Configuring Nginx..."
cat > "${NGINX_SITE}" << 'EOF'
# Upstream configuration for Streamlit WebSocket
upstream streamlit_app {
    server 127.0.0.1:8502;
}

server {
    listen 80;
    listen [::]:80;
    server_name dash.bodytools.work;

    # Redirect all HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name dash.bodytools.work;

    # SSL configuration will be added by certbot
    # ssl_certificate /etc/letsencrypt/live/dash.bodytools.work/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/dash.bodytools.work/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Proxy settings
    location / {
        proxy_pass http://streamlit_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_read_timeout 86400;
        proxy_redirect off;
        proxy_buffering off;
    }

    # WebSocket support for Streamlit
    location /_stcore/stream {
        proxy_pass http://streamlit_app/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # Static files
    location /_stcore/static {
        proxy_pass http://streamlit_app/_stcore/static;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check endpoint
    location /_stcore/health {
        proxy_pass http://streamlit_app/_stcore/health;
    }
}
EOF

# Step 12: Enable Nginx site
log_info "Enabling Nginx site..."
ln -sf "${NGINX_SITE}" /etc/nginx/sites-enabled/
nginx -t  # Test configuration

# Step 13: Reload systemd and start services
log_info "Starting services..."
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"
systemctl reload nginx

# Step 14: Set up SSL certificate with Let's Encrypt
log_info "Setting up SSL certificate..."
log_warn "Make sure your domain ${DOMAIN} points to this server's IP address!"
read -p "Press Enter to continue with SSL setup, or Ctrl+C to skip..."

certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos --email admin@bodytools.work --redirect

# Step 15: Final restart
log_info "Performing final service restart..."
systemctl restart nginx
systemctl restart "${SERVICE_NAME}"

# Step 16: Check service status
log_info "Checking service status..."
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    log_info "✅ Service is running!"
else
    log_error "Service is not running. Check logs: journalctl -u ${SERVICE_NAME} -f"
    exit 1
fi

# Step 17: Display important information
echo ""
log_info "=========================================="
log_info "Deployment completed successfully!"
log_info "=========================================="
log_info "Dashboard URL: https://${DOMAIN}"
log_info "Service name: ${SERVICE_NAME}"
log_info "App directory: ${APP_DIR}"
log_info "Logs: /var/log/${APP_NAME}/"
echo ""
log_warn "IMPORTANT: Update the .env file with your actual API credentials:"
log_warn "sudo nano ${APP_DIR}/.env"
log_warn "Then restart the service: sudo systemctl restart ${SERVICE_NAME}"
echo ""
log_info "Useful commands:"
log_info "  View logs: journalctl -u ${SERVICE_NAME} -f"
log_info "  Restart service: sudo systemctl restart ${SERVICE_NAME}"
log_info "  Check status: sudo systemctl status ${SERVICE_NAME}"
log_info "  Update code: cd ${APP_DIR} && git pull && sudo systemctl restart ${SERVICE_NAME}"