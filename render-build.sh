#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Starting build process..."

# Install system dependencies
echo "Installing system dependencies..."
apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    wget \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for Selenium
STORAGE_DIR=/opt/render/project/.render

if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "Downloading Chrome..."
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  
  # Download and extract Chrome
  wget -q -O chrome.zip "https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.122/linux64/chrome-linux64.zip"
  unzip -q chrome.zip
  rm chrome.zip
  
  # Download ChromeDriver
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

# CRITICAL: Upgrade pip and force wheel usage
echo "Upgrading pip and installing build tools..."
python -m pip install --upgrade pip setuptools wheel

# Install numpy first (pandas dependency) - force binary only
echo "Installing numpy..."
pip install --only-binary=:all: numpy==1.24.3

# Install pandas - force binary only
echo "Installing pandas..."
pip install --only-binary=:all: pandas==1.5.3

# Install remaining requirements
echo "Installing remaining dependencies..."
pip install -r requirements.txt

echo "Build completed successfully!"
