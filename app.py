from flask import Flask
import threading
import time
import logging
import os
import sys

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def run_scrapers():
    """Run your scrapers periodically"""
    while True:
        try:
            logging.info("Starting scrapers...")
            
            # Import the class directly, not the quick_scrape function
            try:
                from primary_markets import OdileagueScraper as PrimaryScraper
                logging.info("Running primary markets scraper...")
                scraper = PrimaryScraper(headless=True, auto_close_delay=0)
                scraper.run()  # Call the run method directly
            except Exception as e:
                logging.error(f"Primary markets error: {e}")
                import traceback
                traceback.print_exc()
            
            try:
                from results import scrape_odileague_all_results
                logging.info("Running results scraper...")
                scrape_odileague_all_results()
            except Exception as e:
                logging.error(f"Results scraper error: {e}")
                traceback.print_exc()
            
            try:
                from standings import EnhancedOdileagueScraper
                logging.info("Running standings scraper...")
                scraper = EnhancedOdileagueScraper(headless=True)
                scraper.scrape_and_save()
                scraper.close()
            except Exception as e:
                logging.error(f"Standings scraper error: {e}")
                traceback.print_exc()
            
            logging.info("Scrapers completed. Waiting 6 hours...")
            time.sleep(6 * 60 * 60)  # Run every 6 hours
            
        except Exception as e:
            logging.error(f"Error in scrapers: {e}")
            traceback.print_exc()
            time.sleep(60 * 60)  # Wait 1 hour on error

@app.route('/')
def home():
    return "Odileague Scraper is running!"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/debug')
def debug():
    """Debug endpoint to check environment and imports"""
    info = {
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "files": os.listdir('.')[:10],
        "imports": {}
    }
    
    # Test imports
    try:
        import primary_markets
        info["imports"]["primary_markets"] = "✅ OK"
        # Check if quick_scrape exists
        info["imports"]["has_quick_scrape"] = str(hasattr(primary_markets, 'quick_scrape'))
    except Exception as e:
        info["imports"]["primary_markets"] = f"❌ {str(e)}"
    
    try:
        import results
        info["imports"]["results"] = "✅ OK"
    except Exception as e:
        info["imports"]["results"] = f"❌ {str(e)}"
    
    try:
        import standings
        info["imports"]["standings"] = "✅ OK"
    except Exception as e:
        info["imports"]["standings"] = f"❌ {str(e)}"
    
    return info

if __name__ == '__main__':
    # Start scraper in background thread
    scraper_thread = threading.Thread(target=run_scrapers, daemon=True)
    scraper_thread.start()
    
    # Run Flask app
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
