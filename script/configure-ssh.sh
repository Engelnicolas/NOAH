#!/bin/bash
# SSH configuration script for NOAH deployment
# This script safely configures SSH authentication with proper error handling

set -e

echo "🔧 Configuring SSH authentication..."

# Create SSH directory
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Configure SSH private key
if [ -n "$SSH_PRIVATE_KEY" ]; then
    echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_rsa
    chmod 600 ~/.ssh/id_rsa
    echo "✅ SSH private key configured"
else
    echo "⚠️  Warning: SSH_PRIVATE_KEY environment variable not set"
    echo "   SSH authentication may not work properly"
fi

# Function to add host keys safely
add_host_keys() {
    local hosts="$1"
    local host_type="$2"
    
    if [ -n "$hosts" ]; then
        echo "🔍 Adding $host_type to known_hosts: $hosts"
        # Handle multiple hosts separated by spaces, commas, or newlines
        echo "$hosts" | tr ',' '\n' | tr ' ' '\n' | while read -r host; do
            host=$(echo "$host" | xargs)  # Trim whitespace
            if [ -n "$host" ]; then
                if ssh-keyscan -H "$host" >> ~/.ssh/known_hosts 2>/dev/null; then
                    echo "  ✅ Added $host to known_hosts"
                else
                    echo "  ⚠️  Warning: Could not scan $host_type host: $host"
                fi
            fi
        done
    else
        echo "⚠️  $host_type not specified, skipping host key scan"
    fi
}

# Add master host to known_hosts
add_host_keys "$MASTER_HOST" "master host"

# Add worker hosts to known_hosts
add_host_keys "$WORKER_HOSTS" "worker hosts"

# Set proper permissions
chmod 644 ~/.ssh/known_hosts 2>/dev/null || true

echo "✅ SSH configuration completed"

# Display summary (without revealing sensitive info)
if [ -f ~/.ssh/id_rsa ]; then
    echo "📋 SSH Configuration Summary:"
    echo "   - Private key: ✅ Configured"
else
    echo "📋 SSH Configuration Summary:"
    echo "   - Private key: ❌ Not configured"
fi

if [ -f ~/.ssh/known_hosts ]; then
    host_count=$(wc -l < ~/.ssh/known_hosts 2>/dev/null || echo "0")
    echo "   - Known hosts: $host_count entries"
else
    echo "   - Known hosts: 0 entries"
fi
