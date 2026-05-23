#!/bin/bash

# =========================================================================
# ⚡ GPLINKS AFFILIATE FORWARDER - ORACLE CLOUD & LINUX AUTO-INSTALLER ⚡
# =========================================================================
# Designed to perform a fully automated, premium configuration, dependency audit,
# password provisioning, and systemd service registration on standard VPS systems.
# =========================================================================

# Ensure the script is run with sudo/root privileges
if [ "$EUID" -ne 0 ]; then
    echo -e "\033[1;31m[ERROR] Please run this installer with sudo or as root!\033[0m"
    echo -e "Command: \033[1;36msudo ./install.sh\033[0m"
    exit 1
fi

# Detect absolute repository directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Detect real user (non-root) who invoked sudo
REAL_USER=${SUDO_USER:-$(logname 2>/dev/null || echo "root")}
REAL_HOME=$(eval echo "~$REAL_USER")

# ANSI color codes for rich console formatting
CYAN='\033[1;36m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
PURPLE='\033[1;35m'
RESET='\033[0m'
BOLD='\033[1m'

clear
echo -e "${CYAN}=========================================================================${RESET}"
echo -e "${CYAN}${BOLD}       ⚡ GPLINKS AFFILIATE FORWARDER - ENTERPRISE INSTALLER ⚡${RESET}"
echo -e "${CYAN}=========================================================================${RESET}"
echo -e "Target Directory: ${GREEN}$DIR${RESET}"
echo -e "Operational User: ${GREEN}$REAL_USER${RESET}"
echo -e "Home Directory:   ${GREEN}$REAL_HOME${RESET}"
echo -e "${CYAN}=========================================================================${RESET}"
echo

# -------------------------------------------------------------------------
# Step 1: Detect OS & Install System Prerequisites
# -------------------------------------------------------------------------
echo -e "${CYAN}[1/5] Detecting OS Distribution & Installing Prereqs...${RESET}"

if command -v apt-get &> /dev/null; then
    echo -e "${GREEN}• Debian/Ubuntu based system detected.${RESET}"
    echo -e "${YELLOW}• Updating system package lists...${RESET}"
    apt-get update -y > /dev/null 2>&1
    
    echo -e "${YELLOW}• Installing Python3, Pip, Venv, Git, Curl & OpenSSL...${RESET}"
    apt-get install -y python3 python3-pip python3-venv git curl openssl > /dev/null 2>&1
elif command -v dnf &> /dev/null; then
    echo -e "${GREEN}• RedHat/CentOS/Oracle Linux (DNF) detected.${RESET}"
    echo -e "${YELLOW}• Installing Python3, Pip, Git, Curl & OpenSSL...${RESET}"
    dnf install -y python3 python3-pip git curl openssl > /dev/null 2>&1
elif command -v yum &> /dev/null; then
    echo -e "${GREEN}• RedHat/CentOS/Oracle Linux (YUM) detected.${RESET}"
    echo -e "${YELLOW}• Installing Python3, Pip, Git, Curl & OpenSSL...${RESET}"
    yum install -y python3 python3-pip git curl openssl > /dev/null 2>&1
else
    echo -e "${RED}[ERROR] Package manager not recognized. Please install python3, pip, venv, git, curl manually.${RESET}"
    exit 1
fi

echo -e "${GREEN}[SUCCESS] System packages successfully installed!${RESET}\n"

# -------------------------------------------------------------------------
# Step 2: Establish Python Virtual Environment & Install Dependencies
# -------------------------------------------------------------------------
echo -e "${CYAN}[2/5] Deploying isolated Python Virtual Environment (.venv)...${RESET}"

# Remove existing venv if it is corrupted
if [ -d ".venv" ] && [ ! -f ".venv/bin/python" ]; then
    echo -e "${YELLOW}• Cleaning up corrupted environment...${RESET}"
    rm -rf .venv
fi

# Create Virtual Environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}• Creating new virtual environment...${RESET}"
    python3 -m venv .venv
fi

# Set ownership of files to the real user so they can edit it
chown -R $REAL_USER:$REAL_USER "$DIR"

# Install requirements using the virtual environment's pip
echo -e "${YELLOW}• Auditing and installing Python library dependencies...${RESET}"
.venv/bin/pip install --upgrade pip > /dev/null
.venv/bin/pip install -r requirements.txt > /dev/null

if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Python packages installation failed. Please check internet connection!${RESET}"
    exit 1
fi

echo -e "${GREEN}[SUCCESS] Virtual environment and dependencies verified!${RESET}\n"

# -------------------------------------------------------------------------
# Step 3: Provision Environmental Configuration (.env) & Secure Password
# -------------------------------------------------------------------------
echo -e "${CYAN}[3/5] Provisioning Environmental Configuration File (.env)...${RESET}"

ENV_FILE=".env"
GEN_PASSWORD=""

# Check if password already exists in existing .env to preserve it
if [ -f "$ENV_FILE" ]; then
    EXISTING_PWD=$(grep -E "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2-)
    if [ ! -z "$EXISTING_PWD" ]; then
        GEN_PASSWORD="$EXISTING_PWD"
        echo -e "${GREEN}• Existing configuration detected. Retaining current dashboard password.${RESET}"
    fi
fi

# Generate password if not exists
if [ -z "$GEN_PASSWORD" ]; then
    # Generate 12 characters cryptographically secure hex password
    GEN_PASSWORD=$(openssl rand -hex 6)
    echo -e "${YELLOW}• Cryptographically generated a secure dashboard password: ${PURPLE}$GEN_PASSWORD${RESET}"
fi

# Create .env from template if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}• Generating .env config from template...${RESET}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        # Fallback raw environment setup
        cat <<EOT > .env
TELEGRAM_BOT_TOKEN=
TELEGRAM_SOURCE_CHANNEL=
TELEGRAM_DEST_CHANNEL=
DISCORD_MODE=webhook
DISCORD_WEBHOOK_URL=
DISCORD_BOT_TOKEN=
DISCORD_CHANNEL_IDS=
GPLINKS_API_TOKEN=a0e6a6c4443a5e524a02ea016a3dd79139a2e2a7
EOT
    fi
fi

# Update password in .env cleanly
# Remove any existing password line and append the secure one
sed -i '/^DASHBOARD_PASSWORD=/d' "$ENV_FILE"
echo "DASHBOARD_PASSWORD=$GEN_PASSWORD" >> "$ENV_FILE"

# Correct file permissions
chown $REAL_USER:$REAL_USER "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo -e "${GREEN}[SUCCESS] Environmental parameters set up securely!${RESET}\n"

# -------------------------------------------------------------------------
# Step 4: Register & Configure Systemd Background Service Daemon
# -------------------------------------------------------------------------
echo -e "${CYAN}[4/5] Registering Background System Service Daemon (gplinks-bot.service)...${RESET}"

SERVICE_FILE="/etc/systemd/system/gplinks-bot.service"

# Create the service configuration
cat <<EOT > "$SERVICE_FILE"
[Unit]
Description=GPLinks Affiliate Deal Forwarder Daemon Service
After=network.target

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$DIR
ExecStart=$DIR/.venv/bin/python web_dashboard.py
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=gplinks-bot

[Install]
WantedBy=multi-user.target
EOT

# Reload systemd and launch service
echo -e "${YELLOW}• Enabling and starting gplinks-bot background daemon...${RESET}"
systemctl daemon-reload
systemctl enable gplinks-bot.service > /dev/null 2>&1
systemctl restart gplinks-bot.service

echo -e "${GREEN}[SUCCESS] System service successfully configured and launched!${RESET}\n"

# -------------------------------------------------------------------------
# Step 5: Network Diagnostics & Public IP Resolution
# -------------------------------------------------------------------------
echo -e "${CYAN}[5/5] Performing Final Subsystem Network Diagnostics...${RESET}"

# Fetch public IP address
PUBLIC_IP=$(curl -s https://api.ipify.org || curl -s https://ifconfig.me || echo "YOUR_VPS_IP")

echo -e "${GREEN}[SUCCESS] Setup complete! Preparing Deployment Summary...${RESET}\n"

# -------------------------------------------------------------------------
# Ultimate Premium Installation Summary Output
# -------------------------------------------------------------------------
echo -e "${GREEN}=========================================================================${RESET}"
echo -e "${GREEN}${BOLD}        🎉 CONGRATULATIONS! GPLINKS BOT SUCCESSFULY INSTALLED 🎉${RESET}"
echo -e "${GREEN}=========================================================================${RESET}"
echo -e " The bot dashboard daemon is now running in the background as a systemd"
echo -e " service, and will launch automatically whenever this server reboots."
echo
echo -e " ${BOLD}🌐 Web Dashboard URL:${RESET}  ${CYAN}http://$PUBLIC_IP:8000${RESET}"
echo -e " ${BOLD}🔑 Secure Password:${RESET}    ${PURPLE}$GEN_PASSWORD${RESET}"
echo
echo -e " ${BOLD}💡 Useful Service Commands:${RESET}"
echo -e "   • Check bot log output:     ${YELLOW}sudo journalctl -u gplinks-bot -f -n 50${RESET}"
echo -e "   • Check service status:     ${YELLOW}sudo systemctl status gplinks-bot${RESET}"
echo -e "   • Restart the service:      ${YELLOW}sudo systemctl restart gplinks-bot${RESET}"
echo -e "   • Stop the service:         ${YELLOW}sudo systemctl stop gplinks-bot${RESET}"
echo
echo -e " ${BOLD}⚠️  Oracle Cloud Firewall Note:${RESET}"
echo -e "   Please ensure Port 8000 is open in your Oracle Cloud Security List"
echo -e "   Ingress Rules, and allowed on your OS firewall using:"
echo -e "   ${YELLOW}sudo ufw allow 8000/tcp${RESET}  (Ubuntu) OR"
echo -e "   ${YELLOW}sudo firewall-cmd --permanent --add-port=8000/tcp && sudo firewall-cmd --reload${RESET} (Oracle Linux)"
echo -e "${GREEN}=========================================================================${RESET}"

# Final file ownership correction
chown -R $REAL_USER:$REAL_USER "$DIR"
chmod +x "$DIR/start.sh"
