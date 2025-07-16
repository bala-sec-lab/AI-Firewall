#!/bin/bash

echo "🔧 Installing GhostWall AI dependencies..."

# Update system
sudo apt update

# Install required packages
sudo apt install -y python3 python3-pip net-tools iptables

# Install Python modules
pip3 install -r requirements.txt

# Create logs directory
mkdir -p logs

# Create empty log files if they don't exist
touch logs/blocked.log logs/seen.log

# Set execution permission
chmod +x ghostwall.py

echo "✅ Installation complete!"
echo "🚀 Run the firewall using: sudo python3 ghostwall.py"
