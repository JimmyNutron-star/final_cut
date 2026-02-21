import os
import json
import csv
import time
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class OdileagueScraper:
    def __init__(self, headless=True):
        """Initialize the scraper with Chrome options configured for Render"""
        self.options = self.get_chrome_options()
        self.driver = webdriver.Chrome(options=self.options)
        self.wait = WebDriverWait(self.driver, 10)
        self.base_url = "https://odibets.com/odileague"
        
    def get_chrome_options(self):
        """Get Chrome options configured for Render"""
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        
        # Important for Render: Set Chrome binary location
        if os.path.exists('/opt/render/project/.render/chrome/opt/google/chrome/google-chrome'):
            chrome_options.binary_location = '/opt/render/project/.render/chrome/opt/google/chrome/google-chrome'
        
        return chrome_options
    
    def close_popup(self):
        """Close the roadblock popup if it appears"""
        try:
            close_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".roadblock-close button"))
            )
            close_button.click()
            print("✅ Popup closed")
            time.sleep(1)
        except TimeoutException:
            print("ℹ️ No popup found or already closed")
            
    def click_timestamp(self, index):
        """Click on a specific timestamp by index (0-based)"""
        try:
            timestamps = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".virtual-timer .ss"))
            )
            
            if len(timestamps) > index:
                timestamp_text = timestamps[index].text
                self.driver.execute_script("arguments[0].scrollIntoView(true);", timestamps[index])
                time.sleep(0.5)
                timestamps[index].click()
                print(f"✅ Clicked timestamp {index+1}: {timestamp_text}")
                time.sleep(2)  # Wait for data to load
                return timestamp_text
            else:
                print(f"❌ Timestamp index {index} not found. Only {len(timestamps)} available.")
                return None
        except Exception as e:
            print(f"❌ Error clicking timestamp: {e}")
            return None
    
    def select_market_from_dropdown(self, market_value):
        """Select a specific market from the dropdown"""
        try:
            # Find the select element
            select_element = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".games-filter-d select"))
            )
            
            # Click the dropdown to open it
            self.driver.execute_script("arguments[0].scrollIntoView(true);", select_element)
            time.sleep(0.5)
            select_element.click()
            time.sleep(0.5)
            
            # Select the option by value
            option = self.driver.find_element(By.CSS_SELECTOR, f"select option[value='{market_value}']")
            option.click()
            print(f"✅ Selected market: {market_value}")
            time.sleep(2)  # Wait for odds to update
            return True
        except Exception as e:
            print(f"❌ Error selecting market {market_value}: {e}")
            return False
    
    def extract_1x2ng_market(self):
        """Extract 1X2&NG market odds"""
        try:
            # First select the market from dropdown
            self.select_market_from_dropdown("1X2G")
            
            # Find all game containers
            games = self.driver.find_elements(By.CSS_SELECTOR, ".game.e")
            
            market_data = []
            for game in games:
                try:
                    # Extract team names
                    team_elements = game.find_elements(By.CSS_SELECTOR, ".t .t-l")
                    if len(team_elements) >= 2:
                        home_team = team_elements[0].text
                        away_team = team_elements[1].text
                        
                        # Find odds for this market
                        odds_buttons = game.find_elements(By.CSS_SELECTOR, ".odds button")
                        
                        match_data = {
                            "home_team": home_team,
                            "away_team": away_team,
                            "odds": []
                        }
                        
                        for button in odds_buttons:
                            try:
                                odd_label = button.find_element(By.CSS_SELECTOR, "small").text
                                odd_value = button.find_element(By.CSS_SELECTOR, "span").text
                                match_data["odds"].append({
                                    "label": odd_label,
                                    "value": odd_value
                                })
                            except:
                                pass
                        
                        market_data.append(match_data)
                except Exception as e:
                    print(f"⚠️ Error extracting game data: {e}")
                    continue
            
            return market_data
        except Exception as e:
            print(f"❌ Error extracting 1X2&NG market: {e}")
            return []
    
    def extract_multi_goals_market(self):
        """Extract Multi-Goals market odds"""
        try:
            self.select_market_from_dropdown("MG")
            
            games = self.driver.find_elements(By.CSS_SELECTOR, ".game.e")
            market_data = []
            
            for game in games:
                try:
                    team_elements = game.find_elements(By.CSS_SELECTOR, ".t .t-l")
                    if len(team_elements) >= 2:
                        home_team = team_elements[0].text
                        away_team = team_elements[1].text
                        
                        odds_buttons = game.find_elements(By.CSS_SELECTOR, ".odds button")
                        
                        match_data = {
                            "home_team": home_team,
                            "away_team": away_team,
                            "multi_goals_options": []
                        }
                        
                        for button in odds_buttons:
                            try:
                                goal_range = button.find_element(By.CSS_SELECTOR, "small").text
                                odd_value = button.find_element(By.CSS_SELECTOR, "span").text
                                match_data["multi_goals_options"].append({
                                    "goals": goal_range,
                                    "odds": odd_value
                                })
                            except:
                                pass
                        
                        market_data.append(match_data)
                except:
                    continue
            
            return market_data
        except Exception as e:
            print(f"❌ Error extracting Multi-Goals market: {e}")
            return []
    
    def extract_team1_goal_nogoal_market(self):
        """Extract Team 1 Goal/No Goal market odds"""
        try:
            self.select_market_from_dropdown("T1G")
            
            games = self.driver.find_elements(By.CSS_SELECTOR, ".game.e")
            market_data = []
            
            for game in games:
                try:
                    team_elements = game.find_elements(By.CSS_SELECTOR, ".t .t-l")
                    if len(team_elements) >= 2:
                        home_team = team_elements[0].text
                        away_team = team_elements[1].text
                        
                        odds_buttons = game.find_elements(By.CSS_SELECTOR, ".odds button")
                        
                        match_data = {
                            "home_team": home_team,
                            "away_team": away_team,
                            "team1_goal_options": []
                        }
                        
                        for button in odds_buttons:
                            try:
                                option_type = button.find_element(By.CSS_SELECTOR, "small").text
                                odd_value = button.find_element(By.CSS_SELECTOR, "span").text
                                match_data["team1_goal_options"].append({
                                    "option": option_type,
                                    "odds": odd_value
                                })
                            except:
                                pass
                        
                        market_data.append(match_data)
                except:
                    continue
            
            return market_data
        except Exception as e:
            print(f"❌ Error extracting Team1 Goal/No Goal market: {e}")
            return []
    
    def extract_team1_over_under_15_market(self):
        """Extract Team 1 Over/Under 1.5 market odds"""
        try:
            self.select_market_from_dropdown("T1OU15")
            
            games = self.driver.find_elements(By.CSS_SELECTOR, ".game.e")
            market_data = []
            
            for game in games:
                try:
                    team_elements = game.find_elements(By.CSS_SELECTOR, ".t .t-l")
                    if len(team_elements) >= 2:
                        home_team = team_elements[0].text
                        away_team = team_elements[1].text
                        
                        odds_buttons = game.find_elements(By.CSS_SELECTOR, ".odds button")
                        
                        match_data = {
                            "home_team": home_team,
                            "away_team": away_team,
                            "team1_ou15_options": []
                        }
                        
                        for button in odds_buttons:
                            try:
                                option_type = button.find_element(By.CSS_SELECTOR, "small").text
                                odd_value = button.find_element(By.CSS_SELECTOR, "span").text
                                match_data["team1_ou15_options"].append({
                                    "option": option_type,
                                    "odds": odd_value
                                })
                            except:
                                pass
                        
                        market_data.append(match_data)
                except:
                    continue
            
            return market_data
        except Exception as e:
            print(f"❌ Error extracting Team1 OV/UN 1.5 market: {e}")
            return []
    
    def save_to_json(self, data, filepath):
        """Save data to JSON file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"✅ JSON saved: {filepath}")
        except Exception as e:
            print(f"❌ Error saving JSON: {e}")
    
    def save_to_csv(self, data, filepath, market_type):
        """Save data to CSV file based on market type"""
        try:
            if not data:
                print(f"⚠️ No data to save for {market_type}")
                return
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if market_type == "1x2ng":
                    writer = csv.writer(f)
                    writer.writerow(['Home Team', 'Away Team', 'Odds Label', 'Odds Value'])
                    for match in data:
                        for odd in match['odds']:
                            writer.writerow([match['home_team'], match['away_team'], odd['label'], odd['value']])
                            
                elif market_type == "multi_goals":
                    writer = csv.writer(f)
                    writer.writerow(['Home Team', 'Away Team', 'Goals Range', 'Odds'])
                    for match in data:
                        for option in match['multi_goals_options']:
                            writer.writerow([match['home_team'], match['away_team'], option['goals'], option['odds']])
                            
                elif market_type == "team1_goal_nogoal":
                    writer = csv.writer(f)
                    writer.writerow(['Home Team', 'Away Team', 'Option', 'Odds'])
                    for match in data:
                        for option in match['team1_goal_options']:
                            writer.writerow([match['home_team'], match['away_team'], option['option'], option['odds']])
                            
                elif market_type == "team1_ou15":
                    writer = csv.writer(f)
                    writer.writerow(['Home Team', 'Away Team', 'Option', 'Odds'])
                    for match in data:
                        for option in match['team1_ou15_options']:
                            writer.writerow([match['home_team'], match['away_team'], option['option'], option['odds']])
            
            print(f"✅ CSV saved: {filepath}")
        except Exception as e:
            print(f"❌ Error saving CSV: {e}")
    
    def create_folder_structure(self, timestamp_value):
        """Create folder structure for the timestamp"""
        # Clean timestamp for folder name
        safe_timestamp = timestamp_value.replace(':', '-')
        
        # Create main timestamp folder
        base_path = os.path.join("odileague_data", safe_timestamp)
        os.makedirs(base_path, exist_ok=True)
        
        # Create market subfolders
        markets = [
            "1x2ng",
            "multi_goals", 
            "team1_goal_nogoal",
            "team1_ou15"
        ]
        
        for market in markets:
            market_path = os.path.join(base_path, market)
            os.makedirs(market_path, exist_ok=True)
        
        return base_path
    
    def scrape_all_markets(self, timestamp_index=2):
        """Main scraping function"""
        try:
            print("🚀 Starting Odileague scraper...")
            
            # Navigate to the page
            self.driver.get(self.base_url)
            print(f"✅ Navigated to {self.base_url}")
            time.sleep(3)
            
            # Close popup if present
            self.close_popup()
            
            # Click on the third timestamp (index 2)
            timestamp_value = self.click_timestamp(timestamp_index)
            if not timestamp_value:
                print("❌ Failed to click timestamp. Exiting.")
                return
            
            # Create folder structure
            base_path = self.create_folder_structure(timestamp_value)
            print(f"📁 Created folder structure at: {base_path}")
            
            # Dictionary to store all market data
            all_markets_data = {}
            
            # Scrape 1X2&NG market
            print("\n📊 Scraping 1X2&NG market...")
            data_1x2ng = self.extract_1x2ng_market()
            all_markets_data['1x2ng'] = data_1x2ng
            
            if data_1x2ng:
                json_path = os.path.join(base_path, "1x2ng", "odds.json")
                csv_path = os.path.join(base_path, "1x2ng", "odds.csv")
                self.save_to_json(data_1x2ng, json_path)
                self.save_to_csv(data_1x2ng, csv_path, "1x2ng")
            
            # Scrape Multi-Goals market
            print("\n📊 Scraping Multi-Goals market...")
            data_multi_goals = self.extract_multi_goals_market()
            all_markets_data['multi_goals'] = data_multi_goals
            
            if data_multi_goals:
                json_path = os.path.join(base_path, "multi_goals", "odds.json")
                csv_path = os.path.join(base_path, "multi_goals", "odds.csv")
                self.save_to_json(data_multi_goals, json_path)
                self.save_to_csv(data_multi_goals, csv_path, "multi_goals")
            
            # Scrape Team1 Goal/No Goal market
            print("\n📊 Scraping Team1 Goal/No Goal market...")
            data_team1_goal = self.extract_team1_goal_nogoal_market()
            all_markets_data['team1_goal_nogoal'] = data_team1_goal
            
            if data_team1_goal:
                json_path = os.path.join(base_path, "team1_goal_nogoal", "odds.json")
                csv_path = os.path.join(base_path, "team1_goal_nogoal", "odds.csv")
                self.save_to_json(data_team1_goal, json_path)
                self.save_to_csv(data_team1_goal, csv_path, "team1_goal_nogoal")
            
            # Scrape Team1 Over/Under 1.5 market
            print("\n📊 Scraping Team1 Over/Under 1.5 market...")
            data_team1_ou15 = self.extract_team1_over_under_15_market()
            all_markets_data['team1_ou15'] = data_team1_ou15
            
            if data_team1_ou15:
                json_path = os.path.join(base_path, "team1_ou15", "odds.json")
                csv_path = os.path.join(base_path, "team1_ou15", "odds.csv")
                self.save_to_json(data_team1_ou15, json_path)
                self.save_to_csv(data_team1_ou15, csv_path, "team1_ou15")
            
            # Save summary file with all markets data
            summary_path = os.path.join(base_path, "all_markets_summary.json")
            self.save_to_json(all_markets_data, summary_path)
            
            # Create a metadata file
            metadata = {
                "timestamp": timestamp_value,
                "scrape_time": datetime.datetime.now().isoformat(),
                "markets_scraped": list(all_markets_data.keys()),
                "url": self.base_url
            }
            metadata_path = os.path.join(base_path, "metadata.json")
            self.save_to_json(metadata, metadata_path)
            
            print(f"\n✅ All data saved successfully in: {base_path}")
            print("⏲️ Waiting 5 seconds before closing browser...")
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
        finally:
            self.close()
    
    def close(self):
        """Close the browser"""
        try:
            self.driver.quit()
            print("✅ Browser closed")
        except:
            pass

def main():
    """Main function to run the scraper"""
    print("="*50)
    print("ODILEAGUE WEB SCRAPER")
    print("="*50)
    
    # Create scraper instance with Render-compatible options
    scraper = OdileagueScraper(headless=True)
    
    try:
        # Scrape all markets from the third timestamp (index 2)
        scraper.scrape_all_markets(timestamp_index=2)
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
        scraper.close()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        scraper.close()

if __name__ == "__main__":
    main()
