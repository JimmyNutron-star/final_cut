#!/usr/bin/env bash
set -o errexit

echo "Starting build process..."

# Install system dependencies
apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    wget \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
STORAGE_DIR=/opt/render/project/.render

if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "Downloading Chrome..."
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  
  wget -q -O chrome.zip "https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.122/linux64/chrome-linux64.zip"
  unzip -q chrome.zip
  rm chrome.zip
  
  wget -q -O chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.122/linux64/chromedriver-linux64.zip"
  unzip -q chromedriver.zip
  rm chromedriver.zip
  
  cd $HOME/project
else
  echo "Using Chrome from cache"
fi

# Set Chrome paths
export CHROME_PATH="$STORAGE_DIR/chrome/chrome-linux64/chrome"
export CHROMEDRIVER_PATH="$STORAGE_DIR/chrome/chromedriver-linux64/chromedriver"
export PATH="$STORAGE_DIR/chrome/chrome-linux64:$STORAGE_DIR/chrome/chromedriver-linux64:$PATH"

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip setuptools wheel

# Install all dependencies - let pip resolve versions
echo "Installing dependencies..."

pip install -r requirements.txt
echo "Build completed successfully!"
