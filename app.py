from flask import Flask
import threading
import time
import logging
from primary_markets import quick_scrape as scrape_markets
from results import scrape_odileague_all_results
from standings import EnhancedOdileagueScraper

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def run_scrapers():
    """Run your scrapers periodically"""
    while True:
        try:
            logging.info("Starting scrapers...")
            
            # Run your scrapers
            scrape_markets(headless=True, auto_close_delay=0)
            scrape_odileague_all_results()
            
            scraper = EnhancedOdileagueScraper(headless=True)
            scraper.scrape_and_save()
            scraper.close()
            
            logging.info("Scrapers completed. Waiting 6 hours...")
            time.sleep(6 * 60 * 60)  # Run every 6 hours
            
        except Exception as e:
            logging.error(f"Error in scrapers: {e}")
            time.sleep(60 * 60)  # Wait 1 hour on error

@app.route('/')
def home():
    return "Odileague Scraper is running!"

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    # Start scraper in background thread
    scraper_thread = threading.Thread(target=run_scrapers, daemon=True)
    scraper_thread.start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=10000)
