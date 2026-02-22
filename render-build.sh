#!/usr/bin/env bash
set -o errexit

echo "Starting build process..."

# Install system dependencies
apt-get update && apt-get install -y wget curl unzip build-essential python3-dev
rm -rf /var/lib/apt/lists/*

# Install Chrome
STORAGE_DIR=/opt/render/project/.render
if [[ ! -d $STORAGE_DIR/chrome ]]; then
  mkdir -p $STORAGE_DIR/chrome && cd $STORAGE_DIR/chrome
  wget -q -O chrome.zip "https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.122/linux64/chrome-linux64.zip"
  wget -q -O chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.122/linux64/chromedriver-linux64.zip"
  unzip -q chrome.zip && unzip -q chromedriver.zip
  rm *.zip && cd $HOME/project
fi

# Set Chrome paths
export PATH="$STORAGE_DIR/chrome/chrome-linux64:$STORAGE_DIR/chrome/chromedriver-linux64:$PATH"

# Upgrade pip
python -m pip install --upgrade pip setuptools wheel

# Install all packages directly
echo "Installing packages..."
pip install \
    numpy==1.26.4 \
    pandas==2.2.3 \
    selenium==4.27.1 \
    webdriver-manager==4.0.2 \
    flask==3.1.0 \
    gunicorn==23.0.0 \
    requests==2.32.3 \
    python-dotenv==1.0.1 \
    lxml==5.3.0 \
    beautifulsoup4==4.12.3

echo "✅ Build completed!"
