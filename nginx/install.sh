#!/bin/bash

# Chess Bot Nginx Setup Script for GCP VM
# Automatic installation of Nginx with SSL/TLS using Let's Encrypt
# Run this script on your GCP VM to configure everything automatically
# Usage: sudo ./install.sh chess-ai.cloud.hnagnurtme.id.vn your-email@example.com

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Chess Bot Nginx Setup with SSL ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root (sudo)${NC}"
    exit 1
fi

# Variables
DOMAIN=${1:-"chess-ai.cloud.hnagnurtme.id.vn"}
EMAIL=${2:-"admin@hnagnurtme.id.vn"}
NGINX_CONF_DIR="/etc/nginx"
SITES_AVAILABLE="$NGINX_CONF_DIR/sites-available"
SITES_ENABLED="$NGINX_CONF_DIR/sites-enabled"
SNIPPETS_DIR="$NGINX_CONF_DIR/snippets"
CERTBOT_DIR="/var/www/certbot"
LOG_DIR="/var/log/nginx"

echo -e "${GREEN}Configuration:${NC}"
echo "  Domain: $DOMAIN"
echo "  Email: $EMAIL"
echo ""

# Update system packages
echo -e "${YELLOW}[1/10] Updating system packages...${NC}"
apt update -qq

# Install nginx if not installed
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}[2/10] Installing Nginx...${NC}"
    apt install -y nginx
    echo -e "${GREEN}✓ Nginx installed${NC}"
else
    echo -e "${GREEN}[2/10] ✓ Nginx already installed${NC}"
fi

# Install Certbot
if ! command -v certbot &> /dev/null; then
    echo -e "${YELLOW}[3/10] Installing Certbot...${NC}"
    apt install -y certbot python3-certbot-nginx
    echo -e "${GREEN}✓ Certbot installed${NC}"
else
    echo -e "${GREEN}[3/10] ✓ Certbot already installed${NC}"
fi

# Create directories
echo -e "${YELLOW}[4/10] Creating directories...${NC}"
mkdir -p "$SNIPPETS_DIR"
mkdir -p "$CERTBOT_DIR"
mkdir -p "$LOG_DIR"
chown -R www-data:www-data "$CERTBOT_DIR"
echo -e "${GREEN}✓ Directories created${NC}"

# Check if config files exist in current directory
if [ ! -f "ssl-params.conf" ] || [ ! -f "chess-ai.conf" ]; then
    echo -e "${RED}ERROR: Configuration files not found!${NC}"
    echo "Please run this script from the nginx/ directory"
    echo "Expected files: ssl-params.conf, chess-ai.conf"
    exit 1
fi

# Update domain in chess-ai.conf
echo -e "${YELLOW}[5/10] Updating domain in configuration...${NC}"
sed -i "s/chess-ai\.cloud\.hnagnurtme\.id\.vn/$DOMAIN/g" chess-ai.conf
echo -e "${GREEN}✓ Domain updated to $DOMAIN${NC}"

# Copy configuration files
echo -e "${YELLOW}[6/10] Installing configuration files...${NC}"
cp ssl-params.conf "$SNIPPETS_DIR/ssl-params.conf"
cp chess-ai.conf "$SITES_AVAILABLE/chess-ai"
echo -e "${GREEN}✓ Configuration files copied${NC}"

# Enable site
echo -e "${YELLOW}[7/10] Enabling Chess Bot site...${NC}"
ln -sf "$SITES_AVAILABLE/chess-ai" "$SITES_ENABLED/chess-ai"

# Remove default site if exists
if [ -f "$SITES_ENABLED/default" ]; then
    rm -f "$SITES_ENABLED/default"
    echo -e "${GREEN}✓ Default site removed${NC}"
fi

echo -e "${GREEN}✓ Chess Bot site enabled${NC}"

# Test configuration
echo -e "${YELLOW}[8/10] Testing Nginx configuration...${NC}"
if nginx -t 2>&1 | grep -q "syntax is ok"; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}ERROR: Nginx configuration test failed${NC}"
    nginx -t
    exit 1
fi

# Reload nginx
echo -e "${YELLOW}[8/10] Reloading Nginx...${NC}"
systemctl reload nginx
systemctl enable nginx
echo -e "${GREEN}✓ Nginx reloaded and enabled${NC}"

# Wait a moment for nginx to fully start
sleep 2

# Check if SSL certificate already exists
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo -e "${GREEN}[9/10] ✓ SSL certificate already exists for $DOMAIN${NC}"
else
    # Obtain SSL certificate
    echo -e "${YELLOW}[9/10] Obtaining SSL certificate from Let's Encrypt...${NC}"
    echo "This may take a minute..."
    
    certbot certonly --webroot \
        -w "$CERTBOT_DIR" \
        -d "$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --non-interactive \
        --quiet || {
            echo -e "${RED}ERROR: Failed to obtain SSL certificate${NC}"
            echo ""
            echo "Troubleshooting steps:"
            echo "  1. Verify DNS is properly configured:"
            echo "     nslookup $DOMAIN"
            echo ""
            echo "  2. Check if port 80 is accessible:"
            echo "     curl -I http://$DOMAIN/.well-known/acme-challenge/test"
            echo ""
            echo "  3. Verify firewall rules allow HTTP (port 80):"
            echo "     sudo ufw status"
            echo "     gcloud compute firewall-rules list"
            echo ""
            echo "  4. Check Nginx is running:"
            echo "     systemctl status nginx"
            echo ""
            exit 1
        }
    
    echo -e "${GREEN}✓ SSL certificate obtained successfully!${NC}"
    
    # Reload nginx to apply SSL
    nginx -t && systemctl reload nginx
    echo -e "${GREEN}✓ Nginx reloaded with SSL${NC}"
fi

# Setup auto-renewal
echo -e "${YELLOW}[10/10] Setting up SSL auto-renewal...${NC}"
systemctl enable certbot.timer
systemctl start certbot.timer

# Verify certbot timer is active
if systemctl is-active --quiet certbot.timer; then
    echo -e "${GREEN}✓ SSL auto-renewal enabled${NC}"
else
    echo -e "${YELLOW}⚠ Warning: certbot.timer may not be running${NC}"
fi

# Check Docker containers status
echo ""
echo -e "${YELLOW}Checking Docker containers...${NC}"
if command -v docker &> /dev/null; then
    if docker ps | grep -q "chess"; then
        echo -e "${GREEN}✓ Docker containers are running${NC}"
    else
        echo -e "${YELLOW}⚠ Warning: Docker containers not running${NC}"
        echo "  Start containers with: docker-compose -f docker-compose.prod.yml up -d"
    fi
else
    echo -e "${YELLOW}⚠ Docker not installed or not in PATH${NC}"
fi

# Final status check
echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo -e "${GREEN}✓${NC} Nginx installed and configured"
echo -e "${GREEN}✓${NC} SSL certificate obtained for $DOMAIN"
echo -e "${GREEN}✓${NC} Auto-renewal enabled"
echo -e "${GREEN}✓${NC} Site enabled and active"
echo ""
echo -e "${YELLOW}Application URLs:${NC}"
echo "  🌐 Frontend: https://$DOMAIN"
echo "  🔌 API: https://$DOMAIN/api"
echo "  📚 API Docs: https://$DOMAIN/docs"
echo "  ❤️  Health Check: https://$DOMAIN/health"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  # Check Nginx status"
echo "  systemctl status nginx"
echo ""
echo "  # View Nginx logs"
echo "  tail -f /var/log/nginx/chess-ai-access.log"
echo "  tail -f /var/log/nginx/chess-ai-error.log"
echo ""
echo "  # Test SSL certificate"
echo "  certbot certificates"
echo ""
echo "  # Renew SSL certificate (automatic renewal is enabled)"
echo "  certbot renew --dry-run"
echo ""
echo "  # Start Docker containers (if not running)"
echo "  cd /path/to/project && docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo -e "${GREEN}🎉 Chess Bot is ready to serve at https://$DOMAIN${NC}"
echo ""
