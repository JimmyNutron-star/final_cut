from flask import Flask, render_template, jsonify, request, redirect, url_for
import threading
import time
import logging
import os
import sys
import json
from datetime import datetime, timedelta
from scraper_monitor import ScraperMonitor
from github_sync import GitHubSync
from email_notifier import EmailNotifier
import traceback

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize components
scraper_monitor = ScraperMonitor()
github_sync = GitHubSync()
email_notifier = EmailNotifier()

# Global variables for scraper status
scraper_status = {
    'running': False,
    'last_run': None,
    'next_run': None,
    'current_stage': 'Idle',
    'progress': 0,
    'total_stages': 6,
    'stages_completed': [],
    'errors': [],
    'start_time': None,
    'estimated_completion': None,
    'stats': {
        'primary_markets': {'status': 'pending', 'matches': 0, 'time': None},
        'results': {'status': 'pending', 'matches': 0, 'time': None},
        'standings': {'status': 'pending', 'teams': 0, 'time': None}
    }
}

def update_status(stage, status, progress=None, data=None):
    """Update scraper status"""
    scraper_status['current_stage'] = stage
    if progress is not None:
        scraper_status['progress'] = progress
    
    if stage not in scraper_status['stages_completed'] and status == 'completed':
        scraper_status['stages_completed'].append(stage)
    
    if stage in scraper_status['stats']:
        scraper_status['stats'][stage]['status'] = status
        if data:
            if 'matches' in data:
                scraper_status['stats'][stage]['matches'] = data['matches']
            if 'teams' in data:
                scraper_status['stats'][stage]['teams'] = data['teams']
        if status == 'completed':
            scraper_status['stats'][stage]['time'] = datetime.now().isoformat()

def run_scrapers():
    """Run your scrapers periodically with monitoring"""
    global scraper_status
    
    while True:
        try:
            scraper_status['running'] = True
            scraper_status['start_time'] = datetime.now().isoformat()
            scraper_status['errors'] = []
            scraper_status['stages_completed'] = []
            scraper_status['progress'] = 0
            scraper_status['current_stage'] = 'Starting...'
            
            # Reset stats
            for key in scraper_status['stats']:
                scraper_status['stats'][key]['status'] = 'pending'
            
            logging.info("Starting scrapers...")
            update_status('Initializing', 'running', 5)
            
            # Stage 1: Primary Markets
            try:
                update_status('Primary Markets', 'running', 15)
                from primary_markets import OdileagueScraper as PrimaryScraper
                logging.info("Running primary markets scraper...")
                scraper = PrimaryScraper(headless=True, auto_close_delay=0)
                scraper.run()
                
                # Count matches from output directory
                match_count = count_matches_from_directory('odileague_*')
                update_status('Primary Markets', 'completed', 30, 
                            {'matches': match_count})
                
            except Exception as e:
                error_msg = f"Primary markets error: {str(e)}"
                logging.error(error_msg)
                scraper_status['errors'].append(error_msg)
                update_status('Primary Markets', 'failed', 30)
            
            # Stage 2: Results
            try:
                update_status('Results', 'running', 45)
                from results import scrape_odileague_all_results
                logging.info("Running results scraper...")
                results_data = scrape_odileague_all_results()
                
                match_count = len(results_data) if results_data else 0
                update_status('Results', 'completed', 60,
                            {'matches': match_count})
                
            except Exception as e:
                error_msg = f"Results scraper error: {str(e)}"
                logging.error(error_msg)
                scraper_status['errors'].append(error_msg)
                update_status('Results', 'failed', 60)
            
            # Stage 3: Standings
            try:
                update_status('Standings', 'running', 75)
                from standings import EnhancedOdileagueScraper
                logging.info("Running standings scraper...")
                scraper = EnhancedOdileagueScraper(headless=True)
                standings_data = scraper.scrape_and_save()
                scraper.close()
                
                team_count = len(standings_data) if standings_data else 0
                update_status('Standings', 'completed', 90,
                            {'teams': team_count})
                
            except Exception as e:
                error_msg = f"Standings scraper error: {str(e)}"
                logging.error(error_msg)
                scraper_status['errors'].append(error_msg)
                update_status('Standings', 'failed', 90)
            
            # Sync with GitHub
            try:
                update_status('GitHub Sync', 'running', 95)
                github_sync.sync_all_data()
                update_status('GitHub Sync', 'completed', 98)
            except Exception as e:
                error_msg = f"GitHub sync error: {str(e)}"
                logging.error(error_msg)
                scraper_status['errors'].append(error_msg)
            
            # Complete
            scraper_status['last_run'] = datetime.now().isoformat()
            scraper_status['next_run'] = (datetime.now() + timedelta(hours=6)).isoformat()
            scraper_status['progress'] = 100
            scraper_status['current_stage'] = 'Completed'
            
            logging.info("Scrapers completed. Waiting 6 hours...")
            
            # Send email notification
            email_notifier.send_completion_notification(scraper_status)
            
            # Sleep for 6 hours
            for _ in range(6 * 60):  # Check every minute if we should continue
                if not scraper_status['running']:
                    break
                time.sleep(60)
            
        except Exception as e:
            error_msg = f"Error in scrapers: {str(e)}"
            logging.error(error_msg)
            scraper_status['errors'].append(error_msg)
            traceback.print_exc()
            
            # Send error notification
            email_notifier.send_error_notification(error_msg, scraper_status)
            
            time.sleep(60 * 60)  # Wait 1 hour on error
        
        finally:
            scraper_status['running'] = False

def count_matches_from_directory(pattern):
    """Count matches from the most recent directory matching pattern"""
    try:
        import glob
        dirs = glob.glob(pattern)
        if dirs:
            latest_dir = max(dirs, key=os.path.getctime)
            count = 0
            for root, dirs, files in os.walk(latest_dir):
                for file in files:
                    if file.endswith('_data.json') and not file.startswith('00_'):
                        try:
                            with open(os.path.join(root, file), 'r') as f:
                                data = json.load(f)
                                count += data.get('match_count', 0)
                        except:
                            pass
            return count
    except:
        pass
    return 0

@app.route('/')
def home():
    return render_template('index.html', status=scraper_status)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', status=scraper_status)

@app.route('/logs')
def logs():
    return render_template('logs.html')

@app.route('/api/status')
def api_status():
    return jsonify(scraper_status)

@app.route('/api/logs')
def api_logs():
    """Get recent logs"""
    try:
        with open('scraper.log', 'r') as f:
            lines = f.readlines()[-100:]  # Last 100 lines
            return jsonify({'logs': lines})
    except:
        return jsonify({'logs': []})

@app.route('/api/start', methods=['POST'])
def start_scraper():
    """Manually start the scraper"""
    global scraper_status
    if not scraper_status['running']:
        scraper_thread = threading.Thread(target=run_scrapers, daemon=True)
        scraper_thread.start()
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already_running'})

@app.route('/api/stop', methods=['POST'])
def stop_scraper():
    """Stop the scraper"""
    global scraper_status
    scraper_status['running'] = False
    return jsonify({'status': 'stopping'})

@app.route('/api/history')
def api_history():
    """Get scraping history"""
    try:
        with open('scraping_history.json', 'r') as f:
            history = json.load(f)
    except:
        history = {'runs': []}
    return jsonify(history)

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
        "scraper_status": scraper_status,
        "imports": {}
    }
    
    # Test imports
    try:
        import primary_markets
        info["imports"]["primary_markets"] = "✅ OK"
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
    # Load configuration
    try:
        from config import EMAIL_CONFIG, GITHUB_CONFIG
        email_notifier.configure(EMAIL_CONFIG)
        github_sync.configure(GITHUB_CONFIG)
    except:
        logging.warning("Config file not found, using environment variables")
    
    # Start scraper in background thread
    scraper_thread = threading.Thread(target=run_scrapers, daemon=True)
    scraper_thread.start()
    
    # Run Flask app
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
