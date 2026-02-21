import os
import time
import logging
import json
import re
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OdileagueStandingsScraper:
    def __init__(self, headless=True):
        """
        Initialize the scraper with Chrome options
        """
        self.driver = None
        self.headless = headless
        self.base_dir = "standings"
        self.create_base_directory()
        self.setup_driver()
    
    def create_base_directory(self):
        """Create the base standings folder if it doesn't exist"""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            logger.info(f"Created base directory: {self.base_dir}")
        else:
            logger.info(f"Base directory already exists: {self.base_dir}")
    
    def create_run_directory(self):
        """Create a timestamped directory for this scrape run"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_dir = os.path.join(self.base_dir, timestamp)
        os.makedirs(run_dir, exist_ok=True)
        logger.info(f"Created run directory: {run_dir}")
        return run_dir, timestamp
    
    def get_chrome_options(self):
        """Get Chrome options configured for Render"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Add user agent
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Important for Render: Set Chrome binary location if it exists
        render_chrome_path = '/opt/render/project/.render/chrome/opt/google/chrome/google-chrome'
        if os.path.exists(render_chrome_path):
            chrome_options.binary_location = render_chrome_path
            logger.info(f"Using Chrome binary at: {render_chrome_path}")
        
        return chrome_options
    
    def setup_driver(self):
        """Configure and initialize the Chrome driver"""
        try:
            chrome_options = self.get_chrome_options()
            
            # For Render, we don't use webdriver-manager, just use default service
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("Chrome driver initialized successfully")
            
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {str(e)}")
            # Fallback to webdriver-manager for local development
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service
                
                logger.info("Falling back to webdriver-manager...")
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=self.get_chrome_options())
                self.wait = WebDriverWait(self.driver, 10)
                logger.info("Chrome driver initialized with webdriver-manager")
            except Exception as e2:
                logger.error(f"Fallback also failed: {str(e2)}")
                raise
    
    def close_popup(self):
        """Close the initial popup if it appears"""
        try:
            close_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".roadblock-close button"))
            )
            close_button.click()
            logger.info("Popup closed successfully")
            time.sleep(1)
        except TimeoutException:
            logger.info("No popup appeared or couldn't close it")
        except Exception as e:
            logger.error(f"Error closing popup: {str(e)}")
    
    def navigate_to_standings(self):
        """Navigate to the standings tab"""
        try:
            # Click on Standings tab
            standings_tab = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'Standings')]"))
            )
            standings_tab.click()
            logger.info("Navigated to Standings tab")
            time.sleep(2)  # Wait for standings to load
        except TimeoutException:
            logger.error("Could not find or click Standings tab")
            raise
        except Exception as e:
            logger.error(f"Error navigating to standings: {str(e)}")
            raise
    
    def extract_form_states(self, form_cell):
        """
        Extract the last 5 match states from the form cell
        Based on the HTML structure: <td><div class="w">W</div></td> etc.
        """
        try:
            # Method 1: Look for all form indicators (div.w, div.d, div.l)
            form_indicators = form_cell.find_elements(By.CSS_SELECTOR, "div.w, div.d, div.l")
            
            if form_indicators:
                # Extract all form states
                all_form_states = [indicator.text.strip() for indicator in form_indicators]
                
                # Get the last 5 (or all if less than 5)
                if len(all_form_states) >= 5:
                    form_states = all_form_states[-5:]
                else:
                    form_states = all_form_states
                
                full_form = ''.join(all_form_states)
                
                logger.debug(f"Found {len(all_form_states)} form indicators: {all_form_states}")
                return form_states, full_form
            
            # Method 2: If no indicators found, try looking for any divs that might contain form data
            all_divs = form_cell.find_elements(By.TAG_NAME, "div")
            if all_divs:
                form_states = []
                for div in all_divs:
                    text = div.text.strip()
                    if text in ['W', 'D', 'L']:
                        form_states.append(text)
                    else:
                        # Check class name for form indicators
                        class_name = div.get_attribute('class')
                        if 'w' in class_name:
                            form_states.append('W')
                        elif 'd' in class_name:
                            form_states.append('D')
                        elif 'l' in class_name:
                            form_states.append('L')
                
                if form_states:
                    if len(form_states) >= 5:
                        form_states = form_states[-5:]
                    full_form = ''.join(form_states)
                    return form_states, full_form
            
            # Method 3: Try to get from HTML content using regex
            cell_html = form_cell.get_attribute('innerHTML')
            # Look for patterns like >W<, >D<, >L<
            form_matches = re.findall(r'>([WDL])<', cell_html)
            
            if form_matches:
                if len(form_matches) >= 5:
                    form_states = form_matches[-5:]
                else:
                    form_states = form_matches
                full_form = ''.join(form_matches)
                return form_states, full_form
            
            # If all methods fail, return empty
            logger.warning(f"Could not extract form states from cell")
            return [], ""
            
        except Exception as e:
            logger.debug(f"Error extracting form states: {str(e)}")
            return [], ""
    
    def scrape_standings_data(self):
        """
        Scrape the standings table data with accurate last 5 matches form
        """
        standings_data = []
        
        try:
            # Wait for standings container to load
            standings_container = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "virtual-standings"))
            )
            
            # Get season title
            try:
                season_title = standings_container.find_element(By.CLASS_NAME, "title").text
                logger.info(f"Season: {season_title}")
            except NoSuchElementException:
                season_title = "Unknown Season"
                logger.warning("Could not find season title")
            
            # Find the table
            table = standings_container.find_element(By.TAG_NAME, "table")
            
            # Get table body
            tbody = table.find_element(By.TAG_NAME, "tbody")
            rows = tbody.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                
                if len(cells) >= 4:
                    # Get form cell (4th column)
                    form_cell = cells[3]
                    
                    # Extract detailed form states
                    last_5_form, full_form = self.extract_form_states(form_cell)
                    
                    # Get the primary form indicator (for backward compatibility)
                    try:
                        # Try to find the last form indicator
                        form_indicators = form_cell.find_elements(By.CSS_SELECTOR, "div.w, div.d, div.l")
                        if form_indicators:
                            last_indicator = form_indicators[-1]
                            form_class = last_indicator.get_attribute("class")
                            primary_form_letter = last_indicator.text
                        else:
                            form_class = ""
                            primary_form_letter = last_5_form[-1] if last_5_form else "?"
                    except:
                        form_class = ""
                        primary_form_letter = last_5_form[-1] if last_5_form else "?"
                    
                    # Extract team name and clean it
                    team_name = cells[1].text.strip()
                    
                    # Convert points to int if possible
                    try:
                        points_int = int(cells[2].text)
                    except:
                        points_int = 0
                    
                    row_data = {
                        'season': season_title,
                        'position': cells[0].text,
                        'team': team_name,
                        'points': cells[2].text,
                        'points_int': points_int,
                        'form_last_match': primary_form_letter,
                        'form_class': form_class,
                        'form_last_5': last_5_form,
                        'form_last_5_string': ''.join(last_5_form),
                        'form_full': full_form,
                        'wins_last_5': last_5_form.count('W'),
                        'draws_last_5': last_5_form.count('D'),
                        'losses_last_5': last_5_form.count('L'),
                        'form_description': self.get_form_description(last_5_form)
                    }
                    standings_data.append(row_data)
            
            logger.info(f"Scraped {len(standings_data)} teams from standings")
            
            # Verify form data was extracted
            teams_with_form = sum(1 for t in standings_data if t['form_last_5'])
            logger.info(f"Teams with form data: {teams_with_form}/{len(standings_data)}")
            
        except TimeoutException:
            logger.error("Timed out waiting for standings to load")
        except Exception as e:
            logger.error(f"Error scraping standings: {str(e)}")
            logger.debug(traceback.format_exc())
        
        return standings_data
    
    def get_form_description(self, form_states):
        """Generate a description of the form"""
        if not form_states:
            return "Unknown"
        
        form_str = ''.join(form_states)
        
        if form_str == 'WWWWW':
            return "Excellent (5 wins)"
        elif form_str.count('W') >= 4:
            return "Very Good (4+ wins)"
        elif form_str.count('W') >= 3:
            return "Good (3 wins)"
        elif form_str.count('L') >= 4:
            return "Poor (4+ losses)"
        elif form_str.count('L') >= 3:
            return "Below Average (3 losses)"
        elif 'WWW' in form_str:
            return "Good run"
        elif 'LLL' in form_str:
            return "Bad run"
        elif form_str == 'DDDDD':
            return "Consistent draws"
        else:
            return "Mixed form"
    
    def scrape_all_standings(self):
        """
        Main method to scrape all standings data
        """
        try:
            logger.info("Navigating to odileague page...")
            self.driver.get("https://odibets.com/odileague")
            time.sleep(3)
            
            self.close_popup()
            self.navigate_to_standings()
            standings = self.scrape_standings_data()
            
            return standings
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            logger.debug(traceback.format_exc())
            return []
    
    def save_standings(self, data):
        """
        Save standings data to both CSV and JSON in a timestamped folder
        """
        if not data:
            logger.warning("No data to save")
            return None, None
        
        run_dir, timestamp = self.create_run_directory()
        
        csv_filename = f"standings_{timestamp}.csv"
        json_filename = f"standings_{timestamp}.json"
        
        csv_path = os.path.join(run_dir, csv_filename)
        json_path = os.path.join(run_dir, json_filename)
        
        # Prepare data for CSV (flatten the last_5 list)
        csv_data = []
        for team in data:
            team_copy = team.copy()
            # Convert last_5 list to separate columns for CSV
            for i, form in enumerate(team.get('form_last_5', [])):
                team_copy[f'match_{i+1}_form'] = form
            # Remove the list from CSV data
            team_copy.pop('form_last_5', None)
            csv_data.append(team_copy)
        
        # Save as CSV
        df_csv = pd.DataFrame(csv_data)
        df_csv.to_csv(csv_path, index=False)
        logger.info(f"CSV saved to: {csv_path}")
        
        # Save as JSON (keep original structure)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"JSON saved to: {json_path}")
        
        self.save_metadata(run_dir, data, timestamp)
        
        return csv_path, json_path
    
    def save_metadata(self, run_dir, data, timestamp):
        """Save metadata about the scrape"""
        # Calculate form statistics
        all_forms = []
        for team in data:
            all_forms.extend(team.get('form_last_5', []))
        
        form_counts = {
            'W': all_forms.count('W'),
            'D': all_forms.count('D'),
            'L': all_forms.count('L')
        }
        
        total_matches = len(all_forms)
        
        metadata = {
            'scrape_timestamp': timestamp,
            'scrape_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_teams': len(data),
            'teams_with_form_data': sum(1 for t in data if t['form_last_5']),
            'season': data[0]['season'] if data else 'Unknown',
            'file_format': 'CSV and JSON',
            'form_statistics': {
                'total_form_entries': total_matches,
                'wins': form_counts['W'],
                'draws': form_counts['D'],
                'losses': form_counts['L'],
                'win_percentage': round((form_counts['W'] / total_matches * 100), 2) if total_matches > 0 else 0,
                'draw_percentage': round((form_counts['D'] / total_matches * 100), 2) if total_matches > 0 else 0,
                'loss_percentage': round((form_counts['L'] / total_matches * 100), 2) if total_matches > 0 else 0
            },
            'teams_summary': [
                {
                    'position': t['position'],
                    'team': t['team'],
                    'points': t['points'],
                    'form_last_5': t['form_last_5_string'],
                    'form_description': t['form_description']
                }
                for t in data
            ]
        }
        
        metadata_path = os.path.join(run_dir, f"metadata_{timestamp}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Metadata saved to: {metadata_path}")
    
    def print_standings(self, data):
        """Print standings in a formatted way with last 5 matches"""
        if not data:
            print("No standings data available")
            return
        
        print("\n" + "="*100)
        print(f"ODILEAGUE STANDINGS - {data[0]['season']}")
        print("="*100)
        print(f"{'Pos':<4} {'Team':<20} {'Pts':<6} {'Last 5 Form':<20} {'W':<4} {'D':<4} {'L':<4} {'Description'}")
        print("-"*100)
        
        for team in data:
            last_5_display = ' '.join(team['form_last_5']) if team['form_last_5'] else 'No data'
            print(f"{team['position']:<4} {team['team']:<20} {team['points']:<6} {last_5_display:<20} {team['wins_last_5']:<4} {team['draws_last_5']:<4} {team['losses_last_5']:<4} {team['form_description']}")
        
        print("="*100)
        print(f"Total teams: {len(data)}")
        
        # Print form summary
        wins = sum(t['wins_last_5'] for t in data)
        draws = sum(t['draws_last_5'] for t in data)
        losses = sum(t['losses_last_5'] for t in data)
        total = wins + draws + losses
        
        if total > 0:
            print(f"\n📊 Last 5 Matches Summary (across all teams):")
            print(f"   Wins: {wins} ({wins/total*100:.1f}%)")
            print(f"   Draws: {draws} ({draws/total*100:.1f}%)")
            print(f"   Losses: {losses} ({losses/total*100:.1f}%)")
    
    def close(self):
        """Close the driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing driver: {str(e)}")


class EnhancedOdileagueScraper(OdileagueStandingsScraper):
    """
    Enhanced scraper with additional form analysis
    """
    
    def __init__(self, headless=True):
        """Initialize the enhanced scraper"""
        super().__init__(headless)
        logger.info("EnhancedOdileagueScraper initialized")
    
    def analyze_team_form(self, standings):
        """Analyze team form patterns"""
        form_analysis = []
        
        for team in standings:
            form_str = team['form_last_5_string']
            
            if not form_str:
                form_analysis.append({
                    'team': team['team'],
                    'position': team['position'],
                    'points': team['points'],
                    'form_string': 'No data',
                    'max_streak': 0,
                    'streak_type': 'No data',
                    'trend': 'Unknown',
                    'form_score': 0
                })
                continue
            
            # Find streaks
            current_streak = 1
            max_streak = 1
            streak_type = form_str[0] if form_str else '?'
            
            for i in range(1, len(form_str)):
                if form_str[i] == form_str[i-1]:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1
            
            # Determine trend
            if len(form_str) >= 3:
                last_3 = form_str[-3:]
                if last_3.count('W') >= 2:
                    trend = "📈 Rising"
                elif last_3.count('L') >= 2:
                    trend = "📉 Falling"
                else:
                    trend = "➡️ Stable"
            else:
                trend = "➡️ Stable"
            
            team_analysis = {
                'team': team['team'],
                'position': team['position'],
                'points': team['points'],
                'form_string': form_str,
                'max_streak': max_streak,
                'streak_type': streak_type if max_streak > 1 else 'No streak',
                'trend': trend,
                'form_score': (team['wins_last_5'] * 3) + (team['draws_last_5'] * 1)
            }
            
            form_analysis.append(team_analysis)
        
        return form_analysis
    
    def print_form_analysis(self, form_analysis):
        """Print detailed form analysis"""
        if not form_analysis:
            return
        
        print("\n" + "="*100)
        print("📊 TEAM FORM ANALYSIS (Last 5 Matches)")
        print("="*100)
        print(f"{'Team':<20} {'Pos':<4} {'Pts':<6} {'Form':<12} {'Streak':<15} {'Trend':<12} {'Score'}")
        print("-"*100)
        
        # Sort by form score
        sorted_analysis = sorted(form_analysis, key=lambda x: x['form_score'], reverse=True)
        
        for team in sorted_analysis:
            streak_display = f"{team['max_streak']}x {team['streak_type']}" if team['max_streak'] > 1 else "None"
            print(f"{team['team']:<20} {team['position']:<4} {team['points']:<6} {team['form_string']:<12} {streak_display:<15} {team['trend']:<12} {team['form_score']}")
        
        print("="*100)
    
    def scrape_and_save(self):
        """
        Complete workflow: scrape, display, analyze, and save
        """
        standings = self.scrape_all_standings()
        
        if standings:
            # Print basic standings
            self.print_standings(standings)
            
            # Perform form analysis
            form_analysis = self.analyze_team_form(standings)
            self.print_form_analysis(form_analysis)
            
            # Save data
            csv_path, json_path = self.save_standings(standings)
            
            if csv_path and json_path:
                print(f"\n✅ Data successfully saved!")
                print(f"📁 Folder: {os.path.dirname(csv_path)}")
                
                # Save analysis separately
                self.save_form_analysis(form_analysis, os.path.dirname(csv_path))
            
            return standings
        else:
            print("❌ No standings data retrieved")
            return None
    
    def save_form_analysis(self, form_analysis, run_dir):
        """Save form analysis to a separate file"""
        if not form_analysis:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        analysis_path = os.path.join(run_dir, f"form_analysis_{timestamp}.json")
        
        with open(analysis_path, 'w') as f:
            json.dump(form_analysis, f, indent=2)
        
        logger.info(f"Form analysis saved to: {analysis_path}")
    
    def close(self):
        """Close the driver with enhanced cleanup"""
        logger.info("Closing EnhancedOdileagueScraper...")
        super().close()


def list_previous_scrapes():
    """List all previous scrape runs"""
    base_dir = "standings"
    
    if not os.path.exists(base_dir):
        print("No standings directory found")
        return
    
    runs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    runs.sort(reverse=True)
    
    if not runs:
        print("No previous scrape runs found")
        return
    
    print("\n📁 Previous Scrape Runs:")
    print("-" * 50)
    for i, run in enumerate(runs[:10], 1):
        run_path = os.path.join(base_dir, run)
        files = os.listdir(run_path)
        csv_files = [f for f in files if f.endswith('.csv')]
        json_files = [f for f in files if f.endswith('.json')]
        
        # Try to read metadata for summary
        metadata_files = [f for f in files if f.startswith('metadata_')]
        teams_count = "?"
        form_data = "?"
        
        if metadata_files:
            try:
                with open(os.path.join(run_path, metadata_files[0]), 'r') as f:
                    metadata = json.load(f)
                    teams_count = metadata.get('total_teams', '?')
                    form_data = metadata.get('teams_with_form_data', '?')
            except:
                pass
        
        print(f"{i}. {run}")
        print(f"   📄 {len(csv_files)} CSV, {len(json_files)} JSON - {teams_count} teams ({form_data} with form data)")
    
    print("-" * 50)


def main():
    """Main function to run the scraper"""
    scraper = None
    try:
        # Check if running on Render
        is_render = os.path.exists('/opt/render/project/.render')
        logger.info(f"Running on Render: {is_render}")
        
        scraper = EnhancedOdileagueScraper(headless=True)  # Always headless on Render
        standings = scraper.scrape_and_save()
        
        if standings:
            # Additional statistics
            df = pd.DataFrame(standings)
            print("\n📈 League Statistics:")
            print(f"   Average points: {df['points'].astype(float).mean():.2f}")
            
            # Show sample of form data
            print("\n📋 Sample Form Data (first 5 teams):")
            for i, team in enumerate(standings[:5]):
                print(f"   {i+1}. {team['team']}: {team['form_last_5_string'] or 'No data'}")
            
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        print(f"\n❌ An error occurred: {str(e)}")
        traceback.print_exc()
    finally:
        if scraper:
            scraper.close()
            logger.info("Scraper closed successfully")
            print("\n🔒 Scraper closed successfully")


def scrape_headless():
    """Scrape standings in headless mode"""
    scraper = None
    try:
        scraper = EnhancedOdileagueScraper(headless=True)
        standings = scraper.scrape_and_save()
        
        if standings:
            print(f"\n✅ Successfully scraped {len(standings)} teams in headless mode")
            print(f"📁 Check the 'standings' folder for the latest timestamped directory")
            
            # Show form data stats
            teams_with_form = sum(1 for t in standings if t['form_last_5'])
            print(f"📊 Teams with form data: {teams_with_form}/{len(standings)}")
        else:
            print("❌ No data scraped")
    
    except Exception as e:
        logger.error(f"Error in headless mode: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            list_previous_scrapes()
        elif sys.argv[1] == "--headless":
            scrape_headless()
        elif sys.argv[1] == "--help":
            print("Usage: python standings.py [option]")
            print("  --list     : List previous scrape runs")
            print("  --headless : Run in headless mode (no browser window)")
            print("  --help     : Show this help message")
            print("  (no args)  : Run with visible browser (will use headless on Render)")
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
    else:
        main()
