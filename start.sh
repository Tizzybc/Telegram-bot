#!/bin/bash

echo "=========================================="
echo "Telegram Bot - Pterodactyl Startup"
echo "=========================================="
echo ""

# Install dependencies if not already installed
echo "Checking dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "✓ Dependencies installed"
echo ""

# Create necessary directories
mkdir -p sessions downloads logs

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  WARNING: .env file not found!"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo ""
    echo "❌ Please configure .env file with your credentials!"
    echo "Edit the .env file in the file manager and restart."
    exit 1
fi

echo "Starting bot..."
echo "=========================================="
python -u main.py
