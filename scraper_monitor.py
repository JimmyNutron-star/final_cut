import os
import json
import time
from datetime import datetime
import logging

class ScraperMonitor:
    def __init__(self):
        self.history_file = 'scraping_history.json'
        self.load_history()
    
    def load_history(self):
        """Load scraping history from file"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                self.history = json.load(f)
        else:
            self.history = {'runs': []}
    
    def save_history(self):
        """Save scraping history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def record_run(self, run_data):
        """Record a scraping run"""
        run_data['timestamp'] = datetime.now().isoformat()
        self.history['runs'].insert(0, run_data)
        
        # Keep only last 100 runs
        if len(self.history['runs']) > 100:
            self.history['runs'] = self.history['runs'][:100]
        
        self.save_history()
    
    def get_latest_run(self):
        """Get the latest scraping run"""
        if self.history['runs']:
            return self.history['runs'][0]
        return None
    
    def get_run_stats(self, days=7):
        """Get statistics for the last N days"""
        from datetime import datetime, timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        recent_runs = []
        
        for run in self.history['runs']:
            run_time = datetime.fromisoformat(run['timestamp'])
            if run_time > cutoff:
                recent_runs.append(run)
        
        if not recent_runs:
            return {
                'total_runs': 0,
                'success_rate': 0,
                'avg_matches': 0,
                'avg_duration': 0
            }
        
        successful = [r for r in recent_runs if r.get('status') == 'success']
        
        return {
            'total_runs': len(recent_runs),
            'successful_runs': len(successful),
            'success_rate': (len(successful) / len(recent_runs)) * 100,
            'avg_matches': sum(r.get('matches', 0) for r in recent_runs) / len(recent_runs),
            'avg_duration': sum(r.get('duration', 0) for r in recent_runs) / len(recent_runs)
        }
