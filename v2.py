from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import csv
from datetime import datetime
import os
import shutil
from pathlib import Path

class OdileagueScraper:
    def __init__(self):
        self.setup_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.markets_to_scrape = [
            "1X2 and OV/UN 1.5",
            "1X2 and OV/UN 2.5", 
            "1X2 and OV/UN 3.5",
            "1X2 and OV/UN 4.5",
            "1X2 and OV/UN 5.5",
            "Correct Score"
        ]
        self.all_markets_data = {}
        self.timestamp_folder = None
        self.base_folder = "odileague_data"
        
    def setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Uncomment the line below to run in headless mode
        # chrome_options.add_argument("--headless")
        
        # Use webdriver-manager to automatically handle ChromeDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
    def create_folder_structure(self):
        """Create timestamp folder and market subfolders"""
        # Create base folder if it doesn't exist
        if not os.path.exists(self.base_folder):
            os.makedirs(self.base_folder)
            print(f"✓ Created base folder: {self.base_folder}")
        
        # Create timestamp folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.timestamp_folder = os.path.join(self.base_folder, f"scrape_{timestamp}")
        os.makedirs(self.timestamp_folder)
        print(f"✓ Created timestamp folder: {self.timestamp_folder}")
        
        # Create market subfolders
        for market in self.markets_to_scrape:
            # Clean market name for folder name
            folder_name = self.clean_folder_name(market)
            market_folder = os.path.join(self.timestamp_folder, folder_name)
            os.makedirs(market_folder)
            print(f"  ✓ Created market folder: {folder_name}")
            
    def clean_folder_name(self, market_name):
        """Clean market name for use as folder name"""
        # Replace special characters and spaces
        clean_name = market_name.lower()
        clean_name = clean_name.replace(" ", "_")
        clean_name = clean_name.replace("/", "_")
        clean_name = clean_name.replace("and", "&")
        clean_name = clean_name.replace("__", "_")
        return clean_name
        
    def handle_popup(self):
        """Close the initial popup if it appears"""
        try:
            popup_close = self.wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "roadblock-close"))
            )
            popup_close.click()
            print("✓ Popup closed")
            time.sleep(2)
        except TimeoutException:
            print("No popup found or already closed")
        except Exception as e:
            print(f"Error handling popup: {str(e)}")
            
    def click_third_timestamp(self):
        """Click the third timestamp in the timer section"""
        try:
            # Wait for timestamps to load
            timestamps = self.wait.until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "ss"))
            )
            
            if len(timestamps) >= 3:
                # Click the third timestamp (index 2)
                third_timestamp = timestamps[2]
                timestamp_text = third_timestamp.text
                
                # Scroll to the timestamp to ensure it's clickable
                self.driver.execute_script("arguments[0].scrollIntoView(true);", third_timestamp)
                time.sleep(1)
                
                # Try to click using JavaScript if normal click fails
                try:
                    third_timestamp.click()
                except:
                    self.driver.execute_script("arguments[0].click();", third_timestamp)
                    
                print(f"✓ Clicked third timestamp: {timestamp_text}")
                time.sleep(3)  # Wait for data to load
                return True
            else:
                print(f"✗ Less than 3 timestamps found. Found: {len(timestamps)}")
                return False
                
        except Exception as e:
            print(f"✗ Error clicking timestamp: {str(e)}")
            return False
            
    def select_market_from_dropdown(self, market_name):
        """Select a specific market from the dropdown"""
        try:
            # Find the dropdown select element
            dropdown = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".games-filter-d select"))
            )
            
            # Click dropdown to open
            self.driver.execute_script("arguments[0].scrollIntoView(true);", dropdown)
            time.sleep(1)
            dropdown.click()
            time.sleep(1)
            
            # Find and click the option with matching text
            options = dropdown.find_elements(By.TAG_NAME, "option")
            for option in options:
                if market_name in option.text:
                    # Click using JavaScript
                    self.driver.execute_script("arguments[0].selected = true; arguments[0].dispatchEvent(new Event('change'))", option)
                    print(f"✓ Selected market: {market_name}")
                    time.sleep(3)  # Wait for odds to update
                    return True
                    
            print(f"✗ Market '{market_name}' not found in dropdown")
            return False
            
        except Exception as e:
            print(f"✗ Error selecting market {market_name}: {str(e)}")
            return False
            
    def scrape_match_odds(self, current_market):
        """Scrape odds for all visible matches based on current market"""
        matches_data = []
        
        try:
            # Find all match containers
            matches = self.driver.find_elements(By.CLASS_NAME, "game")
            print(f"Found {len(matches)} matches")
            
            for match_index, match in enumerate(matches, 1):
                try:
                    # Extract team names
                    team_elements = match.find_elements(By.CLASS_NAME, "t-l")
                    if len(team_elements) >= 2:
                        home_team = team_elements[0].text
                        away_team = team_elements[1].text
                        
                        match_dict = {
                            'match_id': match_index,
                            'home_team': home_team,
                            'away_team': away_team,
                            'odds': {}
                        }
                        
                        # Try to scrape 1X2 odds if present
                        try:
                            x12_buttons = match.find_elements(By.CSS_SELECTOR, ".o.s-1 button")
                            if len(x12_buttons) >= 3:
                                match_dict['odds']['1X2'] = {
                                    'home': x12_buttons[0].find_element(By.CLASS_NAME, "o-2").text,
                                    'draw': x12_buttons[1].find_element(By.CLASS_NAME, "o-2").text,
                                    'away': x12_buttons[2].find_element(By.CLASS_NAME, "o-2").text
                                }
                        except Exception as e:
                            pass
                        
                        # Try to scrape Over/Under odds if present
                        try:
                            ou_buttons = match.find_elements(By.CSS_SELECTOR, ".o.s-2 button")
                            if len(ou_buttons) >= 2:
                                # Determine which over/under market based on selection
                                market_type = current_market.replace("1X2 and ", "") if "1X2" in current_market else current_market
                                match_dict['odds'][market_type] = {
                                    'over': ou_buttons[0].find_element(By.CLASS_NAME, "o-2").text,
                                    'under': ou_buttons[1].find_element(By.CLASS_NAME, "o-2").text
                                }
                        except Exception as e:
                            pass
                        
                        # Try to scrape Correct Score odds if present
                        if "Correct Score" in current_market:
                            try:
                                # Correct score odds may be in different format
                                cs_buttons = match.find_elements(By.CSS_SELECTOR, ".odds button")
                                cs_odds = []
                                for btn in cs_buttons[:15]:  # Get first 15 correct score options
                                    try:
                                        score_text = btn.find_element(By.CLASS_NAME, "o-1").text
                                        odds_value = btn.find_element(By.CLASS_NAME, "o-2").text
                                        cs_odds.append({
                                            'score': score_text,
                                            'odds': odds_value
                                        })
                                    except:
                                        pass
                                
                                if cs_odds:
                                    match_dict['odds']['correct_score'] = cs_odds
                            except Exception as e:
                                pass
                        
                        # Only add match if we have at least one odds
                        if match_dict['odds']:
                            matches_data.append(match_dict)
                            print(f"  ✓ Match {match_index}: {home_team} vs {away_team} - {len(match_dict['odds'])} markets")
                        
                except Exception as e:
                    print(f"  ✗ Error scraping match {match_index}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Error finding matches: {str(e)}")
            
        return matches_data
        
    def save_market_data_json(self, market_name, market_data):
        """Save market data to JSON file in its respective folder"""
        # Clean market name for folder
        folder_name = self.clean_folder_name(market_name)
        market_folder = os.path.join(self.timestamp_folder, folder_name)
        
        # Create filename
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{folder_name}_data_{timestamp}.json"
        filepath = os.path.join(market_folder, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(market_data, jsonfile, indent=2, ensure_ascii=False)
            print(f"  ✓ JSON saved: {filename}")
        except Exception as e:
            print(f"  ✗ Error saving JSON: {str(e)}")
            
    def save_market_data_csv(self, market_name, market_data):
        """Save market data to CSV file in its respective folder"""
        # Clean market name for folder
        folder_name = self.clean_folder_name(market_name)
        market_folder = os.path.join(self.timestamp_folder, folder_name)
        
        # Create filename
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{folder_name}_data_{timestamp}.csv"
        filepath = os.path.join(market_folder, filename)
        
        try:
            # Flatten the data for CSV
            rows = []
            for match in market_data.get('matches', []):
                row = {
                    'match_id': match['match_id'],
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'timestamp_selected': market_data.get('timestamp_selected', '')
                }
                
                # Add odds data
                odds = match.get('odds', {})
                
                # Add 1X2 odds if present
                if '1X2' in odds:
                    row['odds_1X2_home'] = odds['1X2'].get('home', '')
                    row['odds_1X2_draw'] = odds['1X2'].get('draw', '')
                    row['odds_1X2_away'] = odds['1X2'].get('away', '')
                
                # Add Over/Under odds if present
                for key, value in odds.items():
                    if 'OV/UN' in key or 'Over/Under' in key:
                        row['odds_over'] = value.get('over', '')
                        row['odds_under'] = value.get('under', '')
                        row['market_type'] = key
                
                # Add Correct Score odds if present
                if 'correct_score' in odds:
                    cs_odds = odds['correct_score']
                    for i, cs in enumerate(cs_odds[:5]):  # First 5 correct score options
                        row[f'correct_score_{i+1}_score'] = cs.get('score', '')
                        row[f'correct_score_{i+1}_odds'] = cs.get('odds', '')
                
                rows.append(row)
            
            # Write to CSV
            if rows:
                fieldnames = rows[0].keys()
                with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                print(f"  ✓ CSV saved: {filename}")
            else:
                print(f"  ⚠ No data to save for CSV")
                
        except Exception as e:
            print(f"  ✗ Error saving CSV: {str(e)}")
            
    def save_summary_files(self):
        """Save summary files in the timestamp folder"""
        # Save main summary JSON
        summary = {
            'scrape_timestamp': datetime.now().isoformat(),
            'url': 'https://odibets.com/odileague',
            'total_markets': len(self.all_markets_data),
            'market_summary': {}
        }
        
        for market, data in self.all_markets_data.items():
            summary['market_summary'][market] = {
                'total_matches': data['total_matches'],
                'timestamp_selected': data['timestamp_selected'],
                'folder': self.clean_folder_name(market)
            }
        
        # Save main summary
        summary_path = os.path.join(self.timestamp_folder, 'scrape_summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        print(f"✓ Main summary saved: scrape_summary.json")
        
        # Save CSV summary
        csv_summary_path = os.path.join(self.timestamp_folder, 'scrape_summary.csv')
        with open(csv_summary_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['market', 'total_matches', 'timestamp_selected', 'folder']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for market, data in self.all_markets_data.items():
                writer.writerow({
                    'market': market,
                    'total_matches': data['total_matches'],
                    'timestamp_selected': data['timestamp_selected'],
                    'folder': self.clean_folder_name(market)
                })
        print(f"✓ CSV summary saved: scrape_summary.csv")
        
    def scrape_all_markets(self):
        """Main method to scrape all specified markets"""
        try:
            # Create folder structure first
            self.create_folder_structure()
            
            # Navigate to the URL
            print("\nNavigating to Odileague...")
            self.driver.get("https://odibets.com/odileague")
            time.sleep(5)
            
            # Handle popup
            self.handle_popup()
            
            # Click the Live tab if needed
            try:
                live_tab = self.driver.find_element(By.CSS_SELECTOR, ".tbs li.live")
                if not "active" in live_tab.get_attribute("class"):
                    live_tab.click()
                    time.sleep(2)
            except:
                pass
            
            # Click third timestamp
            if not self.click_third_timestamp():
                print("Failed to click third timestamp. Continuing anyway...")
            
            # Scrape each market
            for market in self.markets_to_scrape:
                print(f"\n{'='*50}")
                print(f"Scraping market: {market}")
                print('='*50)
                
                if self.select_market_from_dropdown(market):
                    matches_data = self.scrape_match_odds(market)
                    
                    market_data = {
                        'timestamp_selected': self.get_current_timestamp(),
                        'total_matches': len(matches_data),
                        'matches': matches_data
                    }
                    
                    self.all_markets_data[market] = market_data
                    print(f"✓ Added {len(matches_data)} matches for {market}")
                    
                    # Save market data in both formats
                    self.save_market_data_json(market, market_data)
                    self.save_market_data_csv(market, market_data)
                    
            # Save summary files
            print(f"\n{'='*50}")
            print("Saving summary files...")
            self.save_summary_files()
            
            return self.all_markets_data
            
        except Exception as e:
            print(f"Error in main scraping process: {str(e)}")
            return None
            
    def get_current_timestamp(self):
        """Get current timestamp from the page if available"""
        try:
            active_timestamp = self.driver.find_element(By.CSS_SELECTOR, ".ss.active")
            return active_timestamp.text
        except:
            return datetime.now().strftime("%H:%M")
            
    def auto_close_browser(self):
        """Automatically close browser after 5 seconds"""
        print("\n" + "="*50)
        print("Browser will close automatically in 5 seconds...")
        print("="*50)
        
        for i in range(5, 0, -1):
            print(f"Closing in {i} seconds...")
            time.sleep(1)
            
        try:
            self.driver.quit()
            print("Browser closed automatically.")
        except:
            print("Browser already closed.")
            
    def run(self):
        """Execute the scraper"""
        try:
            print("Starting Odileague Scraper...")
            print(f"Markets to scrape: {len(self.markets_to_scrape)}")
            for i, market in enumerate(self.markets_to_scrape, 1):
                print(f"  {i}. {market}")
            
            data = self.scrape_all_markets()
            
            if data:
                print("\n" + "="*50)
                print("SCRAPING COMPLETED SUCCESSFULLY")
                print("="*50)
                
                total_matches = sum(market_data['total_matches'] for market_data in data.values())
                print(f"Total markets scraped: {len(data)}")
                print(f"Total matches data points: {total_matches}")
                
                print(f"\nData saved in folder: {self.timestamp_folder}")
                print("Folder structure:")
                print(f"  📁 {self.timestamp_folder}/")
                for market in self.markets_to_scrape:
                    folder_name = self.clean_folder_name(market)
                    print(f"    📁 {folder_name}/")
                    print(f"      📄 {folder_name}_data_[time].json")
                    print(f"      📄 {folder_name}_data_[time].csv")
                print(f"    📄 scrape_summary.json")
                print(f"    📄 scrape_summary.csv")
                    
        except KeyboardInterrupt:
            print("\n\nScraping interrupted by user. Saving current data...")
            if self.all_markets_data:
                self.save_summary_files()
                
        except Exception as e:
            print(f"Error during execution: {str(e)}")
            
        finally:
            # Auto close browser after 5 seconds
            self.auto_close_browser()

# Run the scraper
if __name__ == "__main__":
    scraper = OdileagueScraper()
    scraper.run()