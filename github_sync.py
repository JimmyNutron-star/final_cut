import os
import git
import shutil
import logging
from datetime import datetime
import json

class GitHubSync:
    def __init__(self):
        self.repo_url = None
        self.repo_path = '/tmp/data_repo'
        self.branch = 'main'
        self.configured = False
    
    def configure(self, config):
        """Configure GitHub settings"""
        self.repo_url = config.get('repo_url')
        self.branch = config.get('branch', 'main')
        self.username = config.get('username')
        self.token = config.get('token')
        
        if self.repo_url and self.username and self.token:
            # Add authentication to URL
            auth_url = self.repo_url.replace('https://', 
                f'https://{self.username}:{self.token}@')
            self.auth_repo_url = auth_url
            self.configured = True
    
    def clone_or_pull_repo(self):
        """Clone the repository or pull if it exists"""
        try:
            if os.path.exists(self.repo_path):
                # Pull latest changes
                repo = git.Repo(self.repo_path)
                origin = repo.remotes.origin
                origin.pull()
                logging.info("Pulled latest changes from GitHub")
            else:
                # Clone repository
                repo = git.Repo.clone_from(self.auth_repo_url, self.repo_path)
                logging.info(f"Cloned repository from {self.repo_url}")
            
            return True
        except Exception as e:
            logging.error(f"Error cloning/pulling repository: {e}")
            return False
    
    def sync_directory(self, source_dir, dest_dir):
        """Sync a directory to GitHub"""
        if not self.configured:
            logging.warning("GitHub not configured, skipping sync")
            return False
        
        try:
            # Clone/pull repo
            if not self.clone_or_pull_repo():
                return False
            
            # Create timestamp for this sync
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Copy data to repo
            dest_path = os.path.join(self.repo_path, dest_dir, timestamp)
            os.makedirs(dest_path, exist_ok=True)
            
            # Copy all files from source to dest
            for item in os.listdir(source_dir):
                s = os.path.join(source_dir, item)
                d = os.path.join(dest_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            
            logging.info(f"Copied data to {dest_path}")
            
            # Commit and push
            repo = git.Repo(self.repo_path)
            repo.index.add('*')
            
            # Check if there are changes to commit
            if repo.is_dirty(untracked_files=True):
                commit_message = f"Update {dest_dir} data - {timestamp}"
                repo.index.commit(commit_message)
                
                # Push changes
                origin = repo.remotes.origin
                origin.push()
                logging.info(f"Pushed changes to GitHub: {commit_message}")
            else:
                logging.info("No changes to commit")
            
            return True
            
        except Exception as e:
            logging.error(f"Error syncing to GitHub: {e}")
            return False
    
    def sync_all_data(self):
        """Sync all data directories to GitHub"""
        data_dirs = [
            ('odileague_*', 'primary_markets'),
            ('odileague_results', 'results'),
            ('standings', 'standings')
        ]
        
        import glob
        for pattern, dest_dir in data_dirs:
            dirs = glob.glob(pattern)
            if dirs:
                # Get the most recent directory
                latest_dir = max(dirs, key=os.path.getctime)
                self.sync_directory(latest_dir, dest_dir)
    
    def get_data_url(self, file_path):
        """Get the GitHub URL for a file"""
        if not self.repo_url:
            return None
        
        # Convert repo URL to raw content URL
        raw_base = self.repo_url.replace('github.com', 'raw.githubusercontent.com')
        raw_base = raw_base.replace('.git', '')
        
        return f"{raw_base}/{self.branch}/{file_path}"
