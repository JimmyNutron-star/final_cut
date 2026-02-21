import time
import json
import os
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import pandas as pd
from datetime import datetime
import logging
from collections import OrderedDict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('odileague_scraper.log'),
        logging.StreamHandler()
    ]
)

class OdileagueScraper:
    def __init__(self, headless=False, auto_close_delay=5):
        """
        Initialize the Odileague scraper
        
        Args:
            headless (bool): Run browser in headless mode
            auto_close_delay (int): Seconds to wait before auto-closing browser
        """
        self.driver = None
        self.wait = None
        self.headless = headless
        self.auto_close_delay = auto_close_delay
        self.url = "https://odibets.com/odileague"
        self.timestamp_value = None
        self.base_output_dir = None
        
        # Market mappings for consistent naming and ordering
        self.market_mappings = OrderedDict([
            ('1X2', '01_1x2'),
            ('GG/NG', '02_gg_ng'),
            ('Double Chance', '03_double_chance'),
            ('OV/UN 1.5', '04_over_under_1_5'),
            ('OV/UN 2.5', '05_over_under_2_5'),
            ('OV/UN 3.5', '06_over_under_3_5')
        ])
        
    def setup_driver(self):
        """Configure and initialize the Chrome driver"""
        options = webdriver.ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless')
        
        # Additional options to avoid detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # User agent to mimic real browser
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 15)
        
        # Execute script to prevent detection
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def close_popup(self):
        """Close the initial popup/roadblock if it appears"""
        try:
            # Wait for popup and close it
            close_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".roadblock-close button"))
            )
            close_button.click()
            logging.info("Popup closed successfully")
            time.sleep(1)
        except TimeoutException:
            logging.info("No popup found or already closed")
        except Exception as e:
            logging.warning(f"Error handling popup: {e}")
    
    def get_third_timestamp(self):
        """
        Extract the third timestamp from the virtual timer
        
        Returns:
            dict: Third timestamp data with element
        """
        try:
            timestamp_elements = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".virtual-timer .ss"))
            )
            
            third_timestamp = None
            count = 0
            
            for element in timestamp_elements:
                timestamp_text = element.text.strip()
                if timestamp_text:
                    count += 1
                    if count == 3:  # Get the third timestamp
                        third_timestamp = {
                            'value': timestamp_text,
                            'is_active': 'active' in element.get_attribute('class'),
                            'element': element
                        }
                        break
            
            if third_timestamp:
                self.timestamp_value = third_timestamp['value'].replace(':', '_')
                logging.info(f"Third timestamp found: {third_timestamp['value']}")
            else:
                logging.error("Could not find third timestamp")
            
            return third_timestamp
            
        except TimeoutException:
            logging.error("Could not find timestamp elements")
            return None
        except Exception as e:
            logging.error(f"Error extracting third timestamp: {e}")
            return None
    
    def select_over_under_3_5_from_dropdown(self):
        """
        Select OV/UN 3.5 from the dropdown menu
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Find and click the dropdown to open it
            dropdown = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".games-filter-d select"))
            )
            
            # Create Select object and choose option
            select = Select(dropdown)
            
            # Try to select by visible text first, then by value
            try:
                select.select_by_visible_text("OV/UN 3.5")
            except:
                try:
                    select.select_by_value("TG35")  # Value from the HTML
                except:
                    logging.error("Could not find OV/UN 3.5 in dropdown")
                    return False
            
            logging.info("Selected OV/UN 3.5 from dropdown")
            time.sleep(2)  # Wait for odds to load
            return True
            
        except TimeoutException:
            logging.error("Could not find dropdown element")
            return False
        except Exception as e:
            logging.error(f"Error selecting OV/UN 3.5 from dropdown: {e}")
            return False
    
    def get_target_markets(self):
        """
        Get the target markets (first 5 visible buttons + OV/UN 3.5 from dropdown)
        
        Returns:
            list: List of market data dictionaries
        """
        markets = []
        
        try:
            # Get visible market buttons
            market_buttons = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".games-filter-d button"))
            )
            
            # Filter out the select element and get only buttons
            buttons = [btn for btn in market_buttons if btn.tag_name == 'button']
            
            # Take first 5 visible buttons
            for i, button in enumerate(buttons[:5]):  # Take first 5
                market_name = button.text.strip()
                if market_name and market_name in self.market_mappings:
                    markets.append({
                        'name': market_name,
                        'key': self.market_mappings[market_name],
                        'element': button,
                        'position': i + 1,
                        'is_active': 'active' in button.get_attribute('class'),
                        'source': 'visible'
                    })
            
            # Add OV/UN 3.5 (will be selected from dropdown separately)
            markets.append({
                'name': 'OV/UN 3.5',
                'key': self.market_mappings['OV/UN 3.5'],
                'element': None,  # Will be handled by dropdown
                'position': 6,
                'is_active': False,
                'source': 'dropdown'
            })
            
            logging.info(f"Target markets: {[m['name'] for m in markets]}")
            
        except Exception as e:
            logging.error(f"Error getting target markets: {e}")
        
        return markets
    
    def click_market(self, market_element, market_name):
        """
        Click on a specific market button
        
        Args:
            market_element: The web element to click
            market_name: Name of the market for logging
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", market_element)
            time.sleep(0.5)
            
            # Click the element
            market_element.click()
            logging.info(f"Clicked market: {market_name}")
            
            # Wait for odds to load/update
            time.sleep(2)
            return True
            
        except ElementClickInterceptedException:
            logging.warning(f"Click intercepted for {market_name}, trying JavaScript click")
            try:
                self.driver.execute_script("arguments[0].click();", market_element)
                time.sleep(2)
                return True
            except Exception as e:
                logging.error(f"JavaScript click failed for {market_name}: {e}")
                return False
        except Exception as e:
            logging.error(f"Error clicking market {market_name}: {e}")
            return False
    
    def click_timestamp(self, timestamp_element):
        """
        Click on the third timestamp
        
        Args:
            timestamp_element: The web element to click
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", timestamp_element)
            time.sleep(0.5)
            
            # Click the element
            timestamp_element.click()
            
            # Get timestamp value for logging
            timestamp_value = timestamp_element.text.strip()
            logging.info(f"Clicked timestamp: {timestamp_value}")
            
            # Wait for odds to load
            time.sleep(2)
            return True
            
        except Exception as e:
            logging.error(f"Error clicking timestamp: {e}")
            return False
    
    def extract_match_odds_by_market(self, market_name):
        """
        Extract match odds based on the current market
        
        Args:
            market_name (str): Name of the current market
        
        Returns:
            list: List of match odds dictionaries
        """
        matches_data = []
        
        try:
            # Wait for matches to load
            match_elements = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".game.e"))
            )
            
            for match in match_elements:
                try:
                    # Extract team names (common for all markets)
                    team_elements = match.find_elements(By.CSS_SELECTOR, ".t .t-l")
                    if len(team_elements) >= 2:
                        home_team = team_elements[0].text.strip()
                        away_team = team_elements[1].text.strip()
                    else:
                        continue
                    
                    match_dict = OrderedDict([
                        ('home_team', home_team),
                        ('away_team', away_team),
                        ('market', market_name),
                        ('odds', OrderedDict())
                    ])
                    
                    # Extract odds based on market type
                    if market_name == '1X2':
                        odds_buttons = match.find_elements(By.CSS_SELECTOR, ".o.s-1.m3 button")
                        if len(odds_buttons) == 3:
                            match_dict['odds'] = OrderedDict([
                                ('home', odds_buttons[0].find_element(By.CSS_SELECTOR, ".o-2").text.strip()),
                                ('draw', odds_buttons[1].find_element(By.CSS_SELECTOR, ".o-2").text.strip()),
                                ('away', odds_buttons[2].find_element(By.CSS_SELECTOR, ".o-2").text.strip())
                            ])
                    
                    elif market_name == 'GG/NG':
                        odds_buttons = match.find_elements(By.CSS_SELECTOR, ".o.s-2.m2 button")
                        if len(odds_buttons) == 2:
                            match_dict['odds'] = OrderedDict([
                                ('yes', odds_buttons[0].find_element(By.CSS_SELECTOR, ".o-2").text.strip()),
                                ('no', odds_buttons[1].find_element(By.CSS_SELECTOR, ".o-2").text.strip())
                            ])
                    
                    elif market_name == 'Double Chance':
                        odds_buttons = match.find_elements(By.CSS_SELECTOR, ".o button")
                        if len(odds_buttons) >= 3:
                            match_dict['odds'] = OrderedDict([
                                ('home_or_draw', odds_buttons[0].find_element(By.CSS_SELECTOR, ".o-2").text.strip() if len(odds_buttons) > 0 else 'N/A'),
                                ('home_or_away', odds_buttons[1].find_element(By.CSS_SELECTOR, ".o-2").text.strip() if len(odds_buttons) > 1 else 'N/A'),
                                ('draw_or_away', odds_buttons[2].find_element(By.CSS_SELECTOR, ".o-2").text.strip() if len(odds_buttons) > 2 else 'N/A')
                            ])
                    
                    elif 'OV/UN' in market_name:
                        odds_buttons = match.find_elements(By.CSS_SELECTOR, ".o button")
                        if len(odds_buttons) >= 2:
                            goal_line = market_name.replace('OV/UN ', '')
                            match_dict['odds'] = OrderedDict([
                                ('over', odds_buttons[0].find_element(By.CSS_SELECTOR, ".o-2").text.strip()),
                                ('under', odds_buttons[1].find_element(By.CSS_SELECTOR, ".o-2").text.strip()),
                                ('goal_line', goal_line)
                            ])
                    
                    else:
                        # Generic extraction for other markets
                        odds_buttons = match.find_elements(By.CSS_SELECTOR, ".o button")
                        odds_dict = OrderedDict()
                        for i, button in enumerate(odds_buttons):
                            try:
                                label = button.find_element(By.CSS_SELECTOR, ".o-1").text.strip()
                                value = button.find_element(By.CSS_SELECTOR, ".o-2").text.strip()
                                odds_dict[f'option_{i+1}_{label}'] = value
                            except:
                                try:
                                    value = button.find_element(By.CSS_SELECTOR, ".o-2").text.strip()
                                    odds_dict[f'option_{i+1}'] = value
                                except:
                                    pass
                        match_dict['odds'] = odds_dict
                    
                    matches_data.append(match_dict)
                    
                except Exception as e:
                    logging.warning(f"Error extracting match data: {e}")
                    continue
            
            logging.info(f"Extracted {len(matches_data)} matches for market {market_name}")
            
        except TimeoutException:
            logging.error(f"Timeout waiting for match elements in market {market_name}")
        except Exception as e:
            logging.error(f"Error extracting match odds for market {market_name}: {e}")
        
        return matches_data
    
    def create_market_folder(self, market_key):
        """
        Create a folder for a specific market within the timestamp folder
        
        Args:
            market_key (str): The market key/folder name
        
        Returns:
            str: Path to the created folder
        """
        market_folder = os.path.join(self.base_output_dir, market_key)
        if not os.path.exists(market_folder):
            os.makedirs(market_folder)
        return market_folder
    
    def save_market_data(self, market_data, matches):
        """
        Save market data to its dedicated folder in multiple formats
        
        Args:
            market_data (dict): Market information
            matches (list): List of match odds for this market
        """
        market_key = market_data['key']
        market_name = market_data['name']
        
        # Create market folder
        market_folder = self.create_market_folder(market_key)
        
        # Prepare market info
        market_info = OrderedDict([
            ('market_name', market_name),
            ('market_key', market_key),
            ('timestamp', self.timestamp_value.replace('_', ':')),
            ('position', market_data['position']),
            ('source', market_data.get('source', 'visible')),
            ('was_active', market_data['is_active']),
            ('match_count', len(matches)),
            ('scrape_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ('matches', matches)
        ])
        
        # Save as JSON
        json_file = os.path.join(market_folder, f"{market_key}_data.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(market_info, f, indent=2, ensure_ascii=False)
        
        # Save as CSV (wide format)
        csv_rows = []
        for match in matches:
            row = OrderedDict([
                ('home_team', match['home_team']),
                ('away_team', match['away_team'])
            ])
            for odds_key, odds_value in match['odds'].items():
                row[f'odds_{odds_key}'] = odds_value
            csv_rows.append(row)
        
        if csv_rows:
            csv_file = os.path.join(market_folder, f"{market_key}_odds.csv")
            df = pd.DataFrame(csv_rows)
            df.to_csv(csv_file, index=False)
        
        # Save long format CSV for analysis
        long_rows = []
        for match in matches:
            for odds_key, odds_value in match['odds'].items():
                long_rows.append(OrderedDict([
                    ('home_team', match['home_team']),
                    ('away_team', match['away_team']),
                    ('odds_type', odds_key),
                    ('odds_value', odds_value)
                ]))
        
        if long_rows:
            long_file = os.path.join(market_folder, f"{market_key}_long.csv")
            df_long = pd.DataFrame(long_rows)
            df_long.to_csv(long_file, index=False)
        
        # Create a simple text file with odds summary
        txt_file = os.path.join(market_folder, f"{market_key}_summary.txt")
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"MARKET: {market_name}\n")
            f.write(f"TIMESTAMP: {self.timestamp_value.replace('_', ':')}\n")
            f.write(f"MATCHES: {len(matches)}\n")
            f.write(f"SCRAPE TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*50 + "\n\n")
            
            for i, match in enumerate(matches[:5], 1):  # Show first 5 matches
                f.write(f"{i}. {match['home_team']} vs {match['away_team']}\n")
                for odds_key, odds_value in match['odds'].items():
                    f.write(f"   - {odds_key}: {odds_value}\n")
                f.write("\n")
            
            if len(matches) > 5:
                f.write(f"... and {len(matches) - 5} more matches\n")
        
        logging.info(f"Saved market data for {market_name} to {market_folder}")
        
        return market_folder
    
    def save_timestamp_summary(self, markets_data):
        """
        Save a summary of all markets for this timestamp
        
        Args:
            markets_data (dict): Dictionary with market keys and their data
        """
        summary_file = os.path.join(self.base_output_dir, "00_timestamp_summary.json")
        
        summary = OrderedDict([
            ('timestamp', self.timestamp_value.replace('_', ':')),
            ('scrape_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ('total_markets', len(markets_data)),
            ('markets', [])
        ])
        
        # Sort markets by position
        sorted_markets = sorted(markets_data.items(), key=lambda x: x[1]['position'])
        
        for market_key, market_info in sorted_markets:
            summary['markets'].append(OrderedDict([
                ('name', market_info['name']),
                ('key', market_key),
                ('position', market_info['position']),
                ('match_count', market_info['match_count']),
                ('source', market_info['source']),
                ('folder', market_key)
            ]))
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Also create a simple text summary
        txt_summary = os.path.join(self.base_output_dir, "00_timestamp_summary.txt")
        with open(txt_summary, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write(f"ODILEAGUE SCRAPE SUMMARY\n")
            f.write("="*60 + "\n")
            f.write(f"Timestamp: {self.timestamp_value.replace('_', ':')}\n")
            f.write(f"Scrape Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Markets: {len(markets_data)}\n")
            f.write("-"*60 + "\n\n")
            
            for market_info in summary['markets']:
                f.write(f"{market_info['position']}. {market_info['name']}\n")
                f.write(f"   - Matches: {market_info['match_count']}\n")
                f.write(f"   - Folder: {market_info['folder']}/\n")
                f.write("\n")
        
        logging.info(f"Timestamp summary saved to {summary_file}")
    
    def scrape_third_timestamp_markets(self):
        """
        Scrape all markets for the third timestamp
        
        Returns:
            dict: Scraped data organized by market
        """
        markets_data = {}
        
        # Get third timestamp
        third_timestamp = self.get_third_timestamp()
        
        if not third_timestamp:
            logging.error("Could not find third timestamp")
            return markets_data
        
        # Create base output directory with timestamp name
        self.base_output_dir = f"odileague_{third_timestamp['value'].replace(':', '_')}"
        if not os.path.exists(self.base_output_dir):
            os.makedirs(self.base_output_dir)
        
        # Click the third timestamp
        if not self.click_timestamp(third_timestamp['element']):
            logging.error("Failed to click third timestamp")
            return markets_data
        
        # Get target markets
        markets = self.get_target_markets()
        
        if not markets:
            logging.warning("No markets found")
            return markets_data
        
        # Store initial active market to return to it later
        initial_market = None
        for market in markets:
            if market['is_active']:
                initial_market = market
                break
        
        # Scrape each visible market
        for market in markets:
            if market['source'] == 'dropdown':
                # Handle OV/UN 3.5 from dropdown
                logging.info("Processing market 6/6: OV/UN 3.5 (from dropdown)")
                
                # Select from dropdown
                if self.select_over_under_3_5_from_dropdown():
                    # Extract odds
                    matches = self.extract_match_odds_by_market('OV/UN 3.5')
                    
                    if matches:
                        markets_data[market['key']] = {
                            'name': market['name'],
                            'key': market['key'],
                            'position': market['position'],
                            'source': 'dropdown',
                            'is_active': False,
                            'match_count': len(matches),
                            'matches': matches
                        }
                        
                        # Save to dedicated market folder
                        self.save_market_data(market, matches)
                    
                    # Brief pause
                    time.sleep(1)
            else:
                # Handle visible markets
                market_name = market['name']
                logging.info(f"Processing market {market['position']}/6: {market_name}")
                
                # Click the market
                if self.click_market(market['element'], market_name):
                    # Extract odds for this market
                    matches = self.extract_match_odds_by_market(market_name)
                    
                    if matches:
                        markets_data[market['key']] = {
                            'name': market_name,
                            'key': market['key'],
                            'position': market['position'],
                            'source': 'visible',
                            'is_active': market['is_active'],
                            'match_count': len(matches),
                            'matches': matches
                        }
                        
                        # Save to dedicated market folder
                        self.save_market_data(market, matches)
                    
                    # Brief pause between markets
                    time.sleep(1)
        
        # Save timestamp summary
        if markets_data:
            self.save_timestamp_summary(markets_data)
        
        # Return to initial market if needed
        if initial_market:
            logging.info(f"Returning to initial market: {initial_market['name']}")
            self.click_market(initial_market['element'], initial_market['name'])
        
        return markets_data
    
    def print_summary(self, markets_data):
        """
        Print a summary of scraped data
        
        Args:
            markets_data (dict): Scraped data organized by market
        """
        print("\n" + "="*70)
        print(f"ODILEAGUE SCRAPE SUMMARY - TIMESTAMP {self.timestamp_value.replace('_', ':')}")
        print("="*70)
        print(f"Scrape Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Output Directory: {self.base_output_dir}/")
        print("-"*70)
        
        total_matches = 0
        
        # Sort markets by position
        sorted_markets = sorted(markets_data.items(), key=lambda x: x[1]['position'])
        
        for market_key, market_data in sorted_markets:
            print(f"\n{market_data['position']}. {market_data['name']}")
            print(f"   - Key: {market_key}")
            print(f"   - Source: {market_data['source']}")
            print(f"   - Matches: {market_data['match_count']}")
            print(f"   - Folder: {market_key}/")
            
            total_matches += market_data['match_count']
            
            # Show first match as sample
            if market_data['matches']:
                first_match = market_data['matches'][0]
                print(f"   - Sample: {first_match['home_team']} vs {first_match['away_team']}")
                odds_sample = list(first_match['odds'].items())[:3]
                odds_str = ", ".join([f"{k}: {v}" for k, v in odds_sample])
                print(f"     Odds: {odds_str}")
        
        print("\n" + "-"*70)
        print(f"TOTAL MATCHES: {total_matches}")
        print(f"TOTAL MARKETS: {len(markets_data)}")
        print("="*70)
        print("\nFolder Structure:")
        print(f"📁 {self.base_output_dir}/")
        for market_key, market_data in sorted(markets_data.items(), key=lambda x: x[1]['position']):
            print(f"   📁 {market_key}/")
            print(f"      📄 {market_key}_data.json")
            print(f"      📄 {market_key}_odds.csv")
            print(f"      📄 {market_key}_long.csv")
            print(f"      📄 {market_key}_summary.txt")
        print(f"   📄 00_timestamp_summary.json")
        print(f"   📄 00_timestamp_summary.txt")
        print("="*70)
    
    def auto_close_browser(self):
        """
        Automatically close the browser after the specified delay
        """
        if self.auto_close_delay > 0:
            logging.info(f"Browser will close automatically in {self.auto_close_delay} seconds...")
            
            # Countdown timer
            for i in range(self.auto_close_delay, 0, -1):
                if i % 5 == 0 or i <= 5:  # Show countdown every 5 seconds and last 5 seconds
                    print(f"⏰ Closing in {i} seconds...", end='\r')
                time.sleep(1)
            
            print("\n" + " " * 30)  # Clear the countdown line
            
        if self.driver:
            self.driver.quit()
            logging.info("Browser closed automatically")
    
    def run(self):
        """Main execution method"""
        try:
            logging.info("Starting Odileague scraper - Third Timestamp Only")
            print("\n" + "="*70)
            print("ODILEAGUE WEB SCRAPER - THIRD TIMESTAMP ONLY")
            print("="*70)
            print("\nThis script will automatically:")
            print("1. Open the Odileague page")
            print("2. Close any popup that appears")
            print("3. Find the third timestamp")
            print("4. Scrape the first 5 visible markets")
            print("5. Select OV/UN 3.5 from dropdown menu")
            print("6. Save each market's data in its own folder")
            print(f"7. Browser will auto-close after {self.auto_close_delay} seconds")
            print("\n" + "="*70)
            
            # Setup driver
            self.setup_driver()
            
            # Navigate to the page
            logging.info(f"Navigating to {self.url}")
            self.driver.get(self.url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Close popup if present
            self.close_popup()
            
            # Scrape third timestamp with all markets
            markets_data = self.scrape_third_timestamp_markets()
            
            # Print summary
            if markets_data:
                self.print_summary(markets_data)
                logging.info(f"Successfully scraped {len(markets_data)} markets for third timestamp")
                
                # Save a master JSON file with all data combined
                master_file = os.path.join(self.base_output_dir, "99_complete_data.json")
                with open(master_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'scrape_info': {
                            'timestamp': self.timestamp_value.replace('_', ':'),
                            'scrape_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'total_markets': len(markets_data),
                            'total_matches': sum(m['match_count'] for m in markets_data.values())
                        },
                        'markets': markets_data
                    }, f, indent=2, ensure_ascii=False)
                
                logging.info(f"Master data saved to {master_file}")
            else:
                logging.warning("No data scraped")
            
            # Auto-close browser
            self.auto_close_browser()
            
        except Exception as e:
            logging.error(f"Error in main execution: {e}")
            # Make sure to close browser even if there's an error
            if self.driver:
                self.driver.quit()
                logging.info("Browser closed due to error")

# Simplified function for quick use
def quick_scrape(headless=False, auto_close_delay=5):
    """
    Quick function to scrape with default settings
    
    Args:
        headless (bool): Run browser in headless mode
        auto_close_delay (int): Seconds to wait before auto-closing
    """
    scraper = OdileagueScraper(headless=headless, auto_close_delay=auto_close_delay)
    scraper.run()

# Main execution
if __name__ == "__main__":
    # You can modify these parameters
    HEADLESS_MODE = False  # Set to True to run in background
    AUTO_CLOSE_DELAY = 5   # Seconds before browser auto-closes
    
    # Run the scraper
    quick_scrape(headless=HEADLESS_MODE, auto_close_delay=AUTO_CLOSE_DELAY)
    
    print("\n" + "="*70)
    print("✅ Scraping complete! Check the timestamp folder for organized results.")
    print("="*70)