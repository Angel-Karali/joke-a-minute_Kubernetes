#!/bin/sh

# Configuration
DOMAIN="devops-sk-10.lrk.si"
EMAIL="admin@devops-sk-10.lrk.si"  
STAGING="--staging"  # Remove this line for production certs

# Check if certificate already exists
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo "Certificate for $DOMAIN already exists. Skipping generation."
    exit 0
fi

echo "Certificate not found. Generating new certificate for $DOMAIN..."

# Wait for Nginx to be ready
echo "Waiting for Nginx to be ready..."
sleep 15 

# Request certificate
certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    $STAGING \
    -d "$DOMAIN" \
    --non-interactive

if [ $? -eq 0 ]; then
    echo "Certificate successfully generated for $DOMAIN"
else
    echo "Failed to generate certificate for $DOMAIN"
    exit 1
fi