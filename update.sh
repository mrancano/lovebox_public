#!/bin/bash
# update.sh - Update the Lovebox repo

# Exit immediately if a command fails
set -e

# Define variables
APP_DIR="$HOME/src/lovebox"

echo "=== Updating Lovebox Repo ==="
if [ ! -d "$APP_DIR/.git" ]; then
    echo "Repo not found at $APP_DIR. Run setup.sh first."
    exit 1
fi

cd "$APP_DIR"
git pull

echo "=== Update Complete ==="
