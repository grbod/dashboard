#!/bin/bash

# FreightView Dashboard Deployment Script (Safe Version)
# Deploy to dash.bodytools.work with conflict detection
# Usage: sudo bash deploy_safe.sh

set -e  # Exit on error

# Configuration
DOMAIN="dash.bodytools.work"
APP_NAME="dashboard"
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
BLUE='\033[0;34m'
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

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root (use sudo)"
   exit 1
fi

log_info "Starting SAFE deployment of Dashboard to ${DOMAIN}"

# ============================================
# SAFETY CHECKS
# ============================================

log_info "Performing safety checks..."

# Check 1: Port availability
log_debug "Checking if port ${STREAMLIT_PORT} is available..."
if lsof -Pi :${STREAMLIT_PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_error "Port ${STREAMLIT_PORT} is already in use!"
    log_info "Current process using port ${STREAMLIT_PORT}:"
    lsof -Pi :${STREAMLIT_PORT} -sTCP:LISTEN
    log_warn "Please choose a different port or stop the existing service"
    
    # Suggest alternative ports
    for port in 8503 8504 8505 8506; do
        if ! lsof -Pi :${port} -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_info "Port ${port} is available as an alternative"
            break
        fi
    done
    
    read -p "Enter alternative port number (or Ctrl+C to exit): " STREAMLIT_PORT
    
    # Verify new port
    if lsof -Pi :${STREAMLIT_PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_error "Port ${STREAMLIT_PORT} is also in use. Exiting."
        exit 1
    fi
fi

# Check 2: Nginx configuration conflicts
log_debug "Checking for Nginx configuration conflicts..."
if [ -f "${NGINX_SITE}" ]; then
    log_warn "Nginx configuration for ${DOMAIN} already exists!"
    log_info "Backing up existing configuration to ${NGINX_SITE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "${NGINX_SITE}" "${NGINX_SITE}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Check 3: Check existing services
log_debug "Checking for existing services..."
if systemctl list-units --full --all | grep -q "${SERVICE_NAME}"; then
    log_warn "Service ${SERVICE_NAME} already exists!"
    read -p "Do you want to stop and replace it? (y/N): " replace_service
    if [[ $replace_service =~ ^[Yy]$ ]]; then
        systemctl stop "${SERVICE_NAME}" || true
        systemctl disable "${SERVICE_NAME}" || true
    else
        log_error "Cannot proceed without replacing the service. Exiting."
        exit 1
    fi
fi

# Check 4: List all running web services
log_info "Detecting existing web services on this server..."
echo "----------------------------------------"
echo "Existing Nginx sites:"
ls -la /etc/nginx/sites-enabled/ 2>/dev/null || echo "No Nginx sites found"
echo "----------------------------------------"
echo "Services listening on ports:"
netstat -tlnp | grep -E ':(80|443|3000|3001|5000|8000|8001|8080|8501|8502|8503)' || echo "No common web ports in use"
echo "----------------------------------------"
echo "Running Node.js/React apps:"
ps aux | grep -E 'node|npm|yarn' | grep -v grep || echo "No Node.js processes found"
echo "----------------------------------------"
echo "Running Python/Streamlit apps:"
ps aux | grep -E 'streamlit|python.*dashboard|python.*app' | grep -v grep || echo "No Streamlit processes found"
echo "----------------------------------------"

read -p "Review the above services. Continue with deployment? (y/N): " continue_deploy
if [[ ! $continue_deploy =~ ^[Yy]$ ]]; then
    log_info "Deployment cancelled by user"
    exit 0
fi

# Check 5: System resources
log_debug "Checking system resources..."
mem_available=$(free -m | awk 'NR==2{printf "%.1f", $7/1024}')
disk_available=$(df -h /opt | awk 'NR==2{print $4}')
log_info "Available memory: ${mem_available}GB"
log_info "Available disk space in /opt: ${disk_available}"

if (( $(echo "$mem_available < 0.5" | bc -l) )); then
    log_warn "Low memory available! This might affect performance."
    read -p "Continue anyway? (y/N): " continue_low_mem
    if [[ ! $continue_low_mem =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ============================================
# DEPLOYMENT
# ============================================

log_info "Safety checks passed. Proceeding with deployment..."

# Step 1: Update system packages (skip if recently updated)
if [ -f /var/lib/apt/periodic/update-success-stamp ]; then
    last_update=$(stat -c %Y /var/lib/apt/periodic/update-success-stamp)
    current_time=$(date +%s)
    age=$((current_time - last_update))
    if [ $age -lt 86400 ]; then  # Less than 24 hours
        log_info "System packages recently updated, skipping..."
    else
        log_info "Updating system packages..."
        apt-get update
    fi
else
    log_info "Updating system packages..."
    apt-get update
fi

# Step 2: Install required system packages (only if not present)
log_info "Checking required system packages..."
packages_to_install=""
for package in python3 python3-pip python3-venv git nginx; do
    if ! dpkg -l | grep -q "^ii.*$package"; then
        packages_to_install="$packages_to_install $package"
    fi
done

if [ -n "$packages_to_install" ]; then
    log_info "Installing required packages:$packages_to_install"
    apt-get install -y $packages_to_install
else
    log_info "All required packages already installed"
fi

# Step 3: Create application directory
log_info "Setting up application directory at ${APP_DIR}..."
if [ -d "${APP_DIR}" ]; then
    log_warn "Directory ${APP_DIR} already exists. Backing up..."
    mv "${APP_DIR}" "${APP_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
fi
mkdir -p "${APP_DIR}"

# Step 4: Clone repository
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

# Step 7: Create Streamlit configuration
log_info "Creating Streamlit production configuration..."
mkdir -p .streamlit
cat > .streamlit/config.toml << EOF
[server]
port = ${STREAMLIT_PORT}
address = "127.0.0.1"
headless = true
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 50

[browser]
gatherUsageStats = false
serverAddress = "${DOMAIN}"
serverPort = 443

[theme]
base = "dark"
primaryColor = "#033f63"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#262730"
textColor = "#fafafa"
font = "sans serif"

[runner]
fastReruns = false
EOF

# Step 8: Set up environment variables
log_info "Setting up environment variables template..."
if [ ! -f "${APP_DIR}/.env" ]; then
    cat > "${APP_DIR}/.env.template" << 'EOF'
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
    log_warn "Created template .env.template file."
    log_error "IMPORTANT: Copy .env.template to .env and update with actual credentials!"
    log_warn "cp ${APP_DIR}/.env.template ${APP_DIR}/.env"
    log_warn "nano ${APP_DIR}/.env"
fi

# Step 9: Set proper permissions
log_info "Setting file permissions..."
chown -R ${USER}:${USER} "${APP_DIR}"
if [ -f "${APP_DIR}/.env" ]; then
    chmod 600 "${APP_DIR}/.env"
fi

# Step 10: Create systemd service with resource limits
log_info "Creating systemd service with resource limits..."
cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=Dashboard Streamlit App
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=${USER}
Group=${USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin"
ExecStart=${APP_DIR}/venv/bin/streamlit run unified_dashboard.py --server.port ${STREAMLIT_PORT} --server.address 127.0.0.1
Restart=always
RestartSec=10

# Resource limits to prevent affecting other services
MemoryLimit=1G
CPUQuota=50%
Nice=10

# Logging
StandardOutput=append:/var/log/${APP_NAME}/output.log
StandardError=append:/var/log/${APP_NAME}/error.log

# Security hardening
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${APP_DIR} /var/log/${APP_NAME}

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
mkdir -p "/var/log/${APP_NAME}"
chown -R ${USER}:${USER} "/var/log/${APP_NAME}"

# Step 11: Configure Nginx (with conflict prevention)
log_info "Configuring Nginx..."

# Test if upstream name already exists
upstream_name="streamlit_app_${STREAMLIT_PORT}"

cat > "${NGINX_SITE}" << EOF
# Upstream configuration for Streamlit WebSocket
upstream ${upstream_name} {
    server 127.0.0.1:${STREAMLIT_PORT};
}

server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    # Redirect all HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN};

    # SSL configuration will be added by certbot
    # ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Request size limit
    client_max_body_size 50M;

    # Proxy settings
    location / {
        proxy_pass http://${upstream_name};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
        proxy_read_timeout 86400;
        proxy_redirect off;
        proxy_buffering off;
    }

    # WebSocket support for Streamlit
    location /_stcore/stream {
        proxy_pass http://${upstream_name}/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }

    # Static files
    location /_stcore/static {
        proxy_pass http://${upstream_name}/_stcore/static;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_cache_valid 200 1d;
        proxy_cache_bypass \$http_pragma;
        add_header X-Proxy-Cache \$upstream_cache_status;
    }

    # Health check endpoint
    location /_stcore/health {
        proxy_pass http://${upstream_name}/_stcore/health;
        access_log off;
    }
}
EOF

# Step 12: Test Nginx configuration before applying
log_info "Testing Nginx configuration..."
nginx -t
if [ $? -ne 0 ]; then
    log_error "Nginx configuration test failed!"
    log_info "Reverting changes..."
    rm -f "${NGINX_SITE}"
    exit 1
fi

# Step 13: Enable Nginx site
log_info "Enabling Nginx site..."
ln -sf "${NGINX_SITE}" /etc/nginx/sites-enabled/

# Step 14: Reload systemd and start services
log_info "Starting services..."
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

# Check if .env exists before starting
if [ ! -f "${APP_DIR}/.env" ]; then
    log_error ".env file not found! Service will not start properly."
    log_warn "Please create the .env file before starting the service:"
    log_warn "cp ${APP_DIR}/.env.template ${APP_DIR}/.env"
    log_warn "nano ${APP_DIR}/.env"
    log_warn "Then start the service: sudo systemctl start ${SERVICE_NAME}"
else
    systemctl start "${SERVICE_NAME}"
fi

systemctl reload nginx

# Step 15: SSL Certificate (optional)
log_info "SSL Certificate Setup"
log_warn "Make sure your domain ${DOMAIN} points to this server's IP address!"
read -p "Do you want to set up SSL with Let's Encrypt? (y/N): " setup_ssl

if [[ $setup_ssl =~ ^[Yy]$ ]]; then
    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        log_info "Installing certbot..."
        apt-get install -y certbot python3-certbot-nginx
    fi
    
    log_info "Setting up SSL certificate..."
    certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos --email admin@bodytools.work --redirect
    
    # Restart nginx after SSL setup
    systemctl restart nginx
fi

# Step 16: Final checks
log_info "Performing final checks..."

# Check if service is running (only if .env exists)
if [ -f "${APP_DIR}/.env" ]; then
    sleep 3  # Give service time to start
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log_info "✅ Service is running!"
    else
        log_warn "Service is not running. This is expected if .env is not configured."
        log_info "Check logs: journalctl -u ${SERVICE_NAME} -f"
    fi
else
    log_warn "Service not started - waiting for .env configuration"
fi

# Check Nginx
if systemctl is-active --quiet nginx; then
    log_info "✅ Nginx is running!"
else
    log_error "Nginx is not running!"
    systemctl status nginx
fi

# Step 17: Create update script
log_info "Creating update script..."
cat > "${APP_DIR}/update.sh" << EOF
#!/bin/bash
cd ${APP_DIR}
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ${SERVICE_NAME}
echo "Update complete!"
EOF
chmod +x "${APP_DIR}/update.sh"

# Step 18: Display summary
echo ""
echo "=========================================="
log_info "Deployment completed!"
echo "=========================================="
log_info "Dashboard URL: https://${DOMAIN}"
log_info "Service name: ${SERVICE_NAME}"
log_info "App directory: ${APP_DIR}"
log_info "Port: ${STREAMLIT_PORT}"
log_info "Logs: /var/log/${APP_NAME}/"
echo ""

if [ ! -f "${APP_DIR}/.env" ]; then
    log_error "ACTION REQUIRED: Configure environment variables!"
    log_warn "1. Copy template: cp ${APP_DIR}/.env.template ${APP_DIR}/.env"
    log_warn "2. Edit file: nano ${APP_DIR}/.env"
    log_warn "3. Start service: sudo systemctl start ${SERVICE_NAME}"
fi

echo ""
log_info "Useful commands:"
log_info "  View logs: journalctl -u ${SERVICE_NAME} -f"
log_info "  Restart service: sudo systemctl restart ${SERVICE_NAME}"
log_info "  Check status: sudo systemctl status ${SERVICE_NAME}"
log_info "  Update app: ${APP_DIR}/update.sh"
log_info "  Monitor resources: htop"
echo ""
log_info "Resource limits applied:"
log_info "  - Memory limit: 1GB"
log_info "  - CPU quota: 50%"
log_info "  - Nice level: 10 (lower priority)"
echo ""
log_info "This ensures the dashboard won't impact other services on the server."