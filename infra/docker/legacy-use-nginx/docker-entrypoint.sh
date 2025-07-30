#!/bin/sh
set -e

# Generate .htpasswd file from environment variables
if [ -n "$BASIC_AUTH_USER" ] && [ -n "$BASIC_AUTH_PASS" ]; then
    echo "Generating .htpasswd file..."
    # Use openssl to generate the password hash
    echo -n "$BASIC_AUTH_USER:" > /etc/nginx/.htpasswd
    openssl passwd -apr1 "$BASIC_AUTH_PASS" >> /etc/nginx/.htpasswd
    echo "Basic authentication configured for user: $BASIC_AUTH_USER"
else
    echo "WARNING: BASIC_AUTH_USER or BASIC_AUTH_PASS not set, creating empty .htpasswd"
    # Create empty file to prevent nginx errors
    touch /etc/nginx/.htpasswd
fi

# Execute the original nginx entrypoint
exec nginx -g "daemon off;"