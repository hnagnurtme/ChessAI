#!/bin/bash

# Chess Bot System Health Check Script
# Run this on GCP VM to check if everything is working properly
# Usage: ./health-check.sh

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Chess Bot Health Check ===${NC}"
echo ""

# Function to check service
check_service() {
    local service=$1
    local name=$2
    
    if systemctl is-active --quiet "$service"; then
        echo -e "${GREEN}✓${NC} $name is ${GREEN}running${NC}"
        return 0
    else
        echo -e "${RED}✗${NC} $name is ${RED}not running${NC}"
        return 1
    fi
}

# Function to check port
check_port() {
    local port=$1
    local name=$2
    
    if nc -z localhost "$port" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $name (port $port) is ${GREEN}accessible${NC}"
        return 0
    else
        echo -e "${RED}✗${NC} $name (port $port) is ${RED}not accessible${NC}"
        return 1
    fi
}

# Function to check URL
check_url() {
    local url=$1
    local name=$2
    
    if curl -s --max-time 5 "$url" > /dev/null; then
        echo -e "${GREEN}✓${NC} $name is ${GREEN}responding${NC}"
        return 0
    else
        echo -e "${RED}✗${NC} $name is ${RED}not responding${NC}"
        return 1
    fi
}

# 1. System Services
echo -e "${YELLOW}[1] System Services${NC}"
check_service "nginx" "Nginx"
check_service "docker" "Docker"
echo ""

# 2. Network Ports
echo -e "${YELLOW}[2] Network Ports${NC}"
check_port 80 "HTTP"
check_port 443 "HTTPS"
check_port 8000 "Backend API"
check_port 5175 "Frontend"
echo ""

# 3. Docker Containers
echo -e "${YELLOW}[3] Docker Containers${NC}"
if command -v docker &> /dev/null; then
    backend_running=$(docker ps --filter "name=backend" --format "{{.Names}}" | head -1)
    frontend_running=$(docker ps --filter "name=frontend" --format "{{.Names}}" | head -1)
    
    if [ -n "$backend_running" ]; then
        echo -e "${GREEN}✓${NC} Backend container is ${GREEN}running${NC} ($backend_running)"
    else
        echo -e "${RED}✗${NC} Backend container is ${RED}not running${NC}"
    fi
    
    if [ -n "$frontend_running" ]; then
        echo -e "${GREEN}✓${NC} Frontend container is ${GREEN}running${NC} ($frontend_running)"
    else
        echo -e "${RED}✗${NC} Frontend container is ${RED}not running${NC}"
    fi
else
    echo -e "${RED}✗${NC} Docker is not installed"
fi
echo ""

# 4. Application Endpoints
echo -e "${YELLOW}[4] Application Endpoints${NC}"
check_url "http://localhost:8000/health" "Backend Health"
check_url "http://localhost:8000/docs" "Backend API Docs"
check_url "http://localhost:5175" "Frontend"
check_url "http://localhost/" "Nginx Proxy"
echo ""

# 5. SSL Certificate (if exists)
echo -e "${YELLOW}[5] SSL Certificate${NC}"
if command -v certbot &> /dev/null; then
    cert_info=$(sudo certbot certificates 2>/dev/null | grep -A 2 "Certificate Name")
    if [ -n "$cert_info" ]; then
        echo -e "${GREEN}✓${NC} SSL certificate is ${GREEN}installed${NC}"
        
        # Check expiry
        expiry=$(sudo certbot certificates 2>/dev/null | grep "Expiry Date" | head -1)
        if [ -n "$expiry" ]; then
            echo "  $expiry"
        fi
        
        # Check auto-renewal
        if systemctl is-active --quiet certbot.timer; then
            echo -e "${GREEN}✓${NC} Auto-renewal is ${GREEN}enabled${NC}"
        else
            echo -e "${YELLOW}⚠${NC} Auto-renewal is ${YELLOW}not enabled${NC}"
        fi
    else
        echo -e "${YELLOW}⚠${NC} No SSL certificate found"
    fi
else
    echo -e "${YELLOW}⚠${NC} Certbot not installed"
fi
echo ""

# 6. Disk Space
echo -e "${YELLOW}[6] Disk Space${NC}"
disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$disk_usage" -lt 80 ]; then
    echo -e "${GREEN}✓${NC} Disk usage: ${GREEN}${disk_usage}%${NC}"
elif [ "$disk_usage" -lt 90 ]; then
    echo -e "${YELLOW}⚠${NC} Disk usage: ${YELLOW}${disk_usage}%${NC} (warning)"
else
    echo -e "${RED}✗${NC} Disk usage: ${RED}${disk_usage}%${NC} (critical)"
fi
echo ""

# 7. Memory Usage
echo -e "${YELLOW}[7] Memory Usage${NC}"
mem_info=$(free -m | awk 'NR==2 {printf "%.1f%%", $3*100/$2}')
echo -e "${GREEN}✓${NC} Memory usage: $mem_info"
echo ""

# 8. Recent Logs
echo -e "${YELLOW}[8] Recent Error Logs${NC}"
nginx_errors=$(sudo tail -20 /var/log/nginx/chess-ai-error.log 2>/dev/null | grep -i error | wc -l)
if [ "$nginx_errors" -eq 0 ]; then
    echo -e "${GREEN}✓${NC} No recent Nginx errors"
else
    echo -e "${YELLOW}⚠${NC} Found $nginx_errors error(s) in Nginx logs"
    echo "  Run: sudo tail -f /var/log/nginx/chess-ai-error.log"
fi

if [ -n "$backend_running" ]; then
    backend_errors=$(docker logs "$backend_running" --tail 50 2>&1 | grep -i error | wc -l)
    if [ "$backend_errors" -eq 0 ]; then
        echo -e "${GREEN}✓${NC} No recent Backend errors"
    else
        echo -e "${YELLOW}⚠${NC} Found $backend_errors error(s) in Backend logs"
        echo "  Run: docker logs $backend_running"
    fi
fi
echo ""

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
echo ""
echo "Quick commands:"
echo "  ${BLUE}•${NC} View Nginx logs: ${YELLOW}sudo tail -f /var/log/nginx/chess-ai-*.log${NC}"
echo "  ${BLUE}•${NC} View Docker logs: ${YELLOW}docker-compose -f docker-compose.prod.yml logs -f${NC}"
echo "  ${BLUE}•${NC} Restart services: ${YELLOW}docker-compose -f docker-compose.prod.yml restart${NC}"
echo "  ${BLUE}•${NC} Reload Nginx: ${YELLOW}sudo systemctl reload nginx${NC}"
echo "  ${BLUE}•${NC} Check SSL cert: ${YELLOW}sudo certbot certificates${NC}"
echo ""
