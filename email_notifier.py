import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

class EmailNotifier:
    def __init__(self):
        self.smtp_server = None
        self.smtp_port = 587
        self.username = None
        self.password = None
        self.from_email = None
        self.to_emails = []
        self.configured = False
        self.site_url = "https://odi-league-scraper.onrender.com"
    
    def configure(self, config):
        """Configure email settings"""
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.from_email = config.get('from_email', self.username)
        self.to_emails = config.get('to_emails', [])
        
        if self.username and self.password and self.to_emails:
            self.configured = True
    
    def send_email(self, subject, body_html, body_text=None):
        """Send an email"""
        if not self.configured:
            logging.warning("Email not configured, skipping notification")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # Add text version
            if body_text:
                msg.attach(MIMEText(body_text, 'plain'))
            
            # Add HTML version
            msg.attach(MIMEText(body_html, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logging.info(f"Email sent to {self.to_emails}")
            return True
            
        except Exception as e:
            logging.error(f"Error sending email: {e}")
            return False
    
    def send_completion_notification(self, scraper_status):
        """Send notification when scraper completes"""
        if not self.configured:
            return
        
        subject = f"✅ Odileague Scraper Completed - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Count successes
        stats = scraper_status.get('stats', {})
        primary_status = stats.get('primary_markets', {}).get('status', 'unknown')
        results_status = stats.get('results', {}).get('status', 'unknown')
        standings_status = stats.get('standings', {}).get('status', 'unknown')
        
        primary_matches = stats.get('primary_markets', {}).get('matches', 0)
        results_matches = stats.get('results', {}).get('matches', 0)
        standings_teams = stats.get('standings', {}).get('teams', 0)
        
        # Create HTML body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .stats {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .stat-item {{ margin: 10px 0; }}
                .button {{ background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
                .error {{ color: red; }}
                .success {{ color: green; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Odileague Scraper Status</h1>
            </div>
            <div class="content">
                <h2>Scraping Completed Successfully!</h2>
                
                <div class="stats">
                    <h3>📊 Scraping Statistics</h3>
                    <div class="stat-item"><strong>Primary Markets:</strong> <span class="{'success' if primary_status == 'completed' else 'error'}">{primary_status.upper()}</span> - {primary_matches} matches</div>
                    <div class="stat-item"><strong>Results:</strong> <span class="{'success' if results_status == 'completed' else 'error'}">{results_status.upper()}</span> - {results_matches} matches</div>
                    <div class="stat-item"><strong>Standings:</strong> <span class="{'success' if standings_status == 'completed' else 'error'}">{standings_status.upper()}</span> - {standings_teams} teams</div>
                    <div class="stat-item"><strong>Start Time:</strong> {scraper_status.get('start_time', 'N/A')}</div>
                    <div class="stat-item"><strong>Next Run:</strong> {scraper_status.get('next_run', 'N/A')}</div>
                </div>
                
                <h3>🔗 Quick Links</h3>
                <p>
                    <a href="{self.site_url}" class="button">View Dashboard</a>
                    <a href="{self.site_url}/dashboard" class="button">Detailed Dashboard</a>
                    <a href="{self.site_url}/logs" class="button">View Logs</a>
                </p>
                
                <h3>📁 Data Repositories</h3>
                <p>
                    <a href="https://github.com/JimmyNutron-star/data">GitHub Repository</a>
                </p>
                
                <hr>
                <p><small>This is an automated message from your Odileague Scraper</small></p>
            </div>
        </body>
        </html>
        """
        
        self.send_email(subject, html_body)
    
    def send_error_notification(self, error_message, scraper_status):
        """Send notification when scraper encounters an error"""
        if not self.configured:
            return
        
        subject = f"⚠️ Odileague Scraper Error - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .error-box {{ background-color: #ffebee; padding: 15px; border-left: 4px solid #f44336; margin: 20px 0; }}
                .button {{ background-color: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Odileague Scraper Error</h1>
            </div>
            <div class="content">
                <h2>An error occurred during scraping</h2>
                
                <div class="error-box">
                    <h3>Error Details:</h3>
                    <pre>{error_message}</pre>
                </div>
                
                <div class="stats">
                    <h3>Current Status:</h3>
                    <p><strong>Stage:</strong> {scraper_status.get('current_stage', 'Unknown')}</p>
                    <p><strong>Progress:</strong> {scraper_status.get('progress', 0)}%</p>
                </div>
                
                <h3>🔗 Quick Links</h3>
                <p>
                    <a href="{self.site_url}" class="button">View Dashboard</a>
                    <a href="{self.site_url}/logs" class="button">View Logs</a>
                </p>
                
                <hr>
                <p><small>This is an automated error notification from your Odileague Scraper</small></p>
            </div>
        </body>
        </html>
        """
        
        self.send_email(subject, html_body)
    
    def send_sleep_notification(self):
        """Send notification when the site goes to sleep (Render free tier)"""
        if not self.configured:
            return
        
        subject = f"💤 Odileague Scraper Sleeping - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #FF9800; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .button {{ background-color: #FF9800; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Odileague Scraper Sleeping</h1>
            </div>
            <div class="content">
                <h2>The scraper is going to sleep (Render free tier)</h2>
                
                <p>To wake it up and continue monitoring, click the link below:</p>
                
                <p>
                    <a href="{self.site_url}" class="button">Wake Up Scraper</a>
                </p>
                
                <p>The scraper will automatically wake up when you access the site and continue its schedule.</p>
                
                <hr>
                <p><small>This is an automated message from your Odileague Scraper</small></p>
            </div>
        </body>
        </html>
        """
        
        self.send_email(subject, html_body)
