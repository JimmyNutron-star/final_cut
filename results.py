import os
import time
import threading
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

def get_chrome_options():
    """Get Chrome options configured for Render"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # Important for Render: Set Chrome binary location
    if os.path.exists('/opt/render/project/.render/chrome/opt/google/chrome/google-chrome'):
        chrome_options.binary_location = '/opt/render/project/.render/chrome/opt/google/chrome/google-chrome'
    
    return chrome_options

def setup_results_folder():
    """
    Creates a timestamped folder for storing results
    Returns the folder path and timestamp
    """
    # Create main results directory if it doesn't exist
    main_results_dir = "odileague_results"
    if not os.path.exists(main_results_dir):
        os.makedirs(main_results_dir)
        print(f"Created main results directory: {main_results_dir}")
    
    # Create timestamp for this scraping session
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_folder = os.path.join(main_results_dir, f"scrape_{timestamp}")
    
    # Create session folder
    os.makedirs(session_folder)
    print(f"Created session folder: {session_folder}")
    
    return session_folder, timestamp

def save_results_to_files(all_results, session_folder, timestamp):
    """
    Saves results data to JSON, CSV, and summary files only
    """
    saved_files = []
    
    # Save full results as JSON
    json_filename = os.path.join(session_folder, f"results_{timestamp}.json")
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    saved_files.append(json_filename)
    print(f"✓ JSON results saved: {json_filename}")
    
    # Save CSV format
    csv_filename = os.path.join(session_folder, f"results_{timestamp}.csv")
    with open(csv_filename, 'w', encoding='utf-8') as f:
        f.write("Week,Match Time,Home Team,Home Score,Away Score,Away Team,Result\n")
        for week_data in all_results:
            week_name = week_data['tournament']
            match_time = week_data['time']
            for match in week_data['matches']:
                f.write(f"\"{week_name}\",{match_time},{match['home_team']},{match['home_score']},{match['away_score']},{match['away_team']},{match['result']}\n")
    saved_files.append(csv_filename)
    print(f"✓ CSV results saved: {csv_filename}")
    
    # Save summary file
    summary_filename = os.path.join(session_folder, "summary.txt")
    with open(summary_filename, 'w', encoding='utf-8') as f:
        f.write(f"ODIBETS ODILEAGUE - SCRAPE SUMMARY\n")
        f.write("=" * 50 + "\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Session ID: {timestamp}\n")
        f.write("-" * 50 + "\n")
        f.write(f"Weeks Found: {len(all_results)}\n")
        f.write(f"Total Matches: {sum(len(week['matches']) for week in all_results)}\n")
        f.write("-" * 50 + "\n")
        f.write("\nWEEKS BREAKDOWN:\n")
        for i, week in enumerate(all_results, 1):
            f.write(f"{i:2}. {week['tournament']} - {len(week['matches']):2} matches\n")
        f.write("-" * 50 + "\n")
        f.write(f"Files Generated:\n")
        f.write(f"  - {os.path.basename(json_filename)}\n")
        f.write(f"  - {os.path.basename(csv_filename)}\n")
        f.write(f"  - {os.path.basename(summary_filename)}\n")
        f.write("=" * 50 + "\n")
    print(f"✓ Summary saved: {summary_filename}")
    
    return saved_files

def save_debug_info(driver, session_folder, timestamp):
    """
    Saves debug information only when there's an error
    """
    # Save screenshot
    screenshot_path = os.path.join(session_folder, f"error_{timestamp}.png")
    driver.save_screenshot(screenshot_path)
    print(f"✓ Error screenshot saved: {screenshot_path}")
    
    # Save page source
    html_path = os.path.join(session_folder, f"error_{timestamp}.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print(f"✓ Error page source saved: {html_path}")
    
    return screenshot_path, html_path

def append_to_master_log(all_results, session_folder, timestamp):
    """
    Appends this session's info to a master log file
    """
    master_log_path = os.path.join("odileague_results", "master_log.json")
    
    # Create or load existing master log
    if os.path.exists(master_log_path):
        with open(master_log_path, 'r', encoding='utf-8') as f:
            master_log = json.load(f)
    else:
        master_log = {"scraping_sessions": []}
    
    # Add this session
    session_info = {
        "timestamp": timestamp,
        "folder": session_folder,
        "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "weeks_found": len(all_results),
        "total_matches": sum(len(week['matches']) for week in all_results),
        "files": ["results_{}.json".format(timestamp), "results_{}.csv".format(timestamp), "summary.txt"]
    }
    
    master_log["scraping_sessions"].append(session_info)
    
    # Save updated master log
    with open(master_log_path, 'w', encoding='utf-8') as f:
        json.dump(master_log, f, indent=2)
    
    print(f"✓ Master log updated: {master_log_path}")

def delayed_browser_close(driver, delay_seconds=5):
    """
    Closes the browser after a specified delay
    """
    def close_driver():
        time.sleep(delay_seconds)
        try:
            driver.quit()
            print(f"\n✓ Browser closed automatically after {delay_seconds} seconds")
        except:
            pass
    
    # Start the delayed close in a separate thread
    close_thread = threading.Thread(target=close_driver)
    close_thread.daemon = True
    close_thread.start()
    return close_thread

def scrape_odileague_all_results():
    """
    Scrapes all results from the Odibets Odileague page based on the updated HTML structure
    """
    # Setup results folder first
    session_folder, timestamp = setup_results_folder()
    
    # Setup Chrome options using the configured function
    chrome_options = get_chrome_options()
    
    # Auto-download and setup ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        print("\n" + "=" * 70)
        print(f"SCRAPING SESSION: {timestamp}")
        print("=" * 70)
        
        print("\nNavigating to Odibets Odileague page...")
        driver.get("https://odibets.com/odileague")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 20)
        time.sleep(5)
        
        # Handle popup if it appears
        try:
            print("Looking for popup...")
            close_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".roadblock-close button"))
            )
            close_button.click()
            print("✓ Closed popup")
            time.sleep(2)
        except TimeoutException:
            print("ℹ No popup found or couldn't close it")
        
        # Print page title
        print(f"Page title: {driver.title}")
        
        # Click on Results tab using the selector from the HTML
        print("\nLooking for Results tab...")
        try:
            # Using the exact structure from the HTML: ul.tbs li with text "Results"
            results_tab = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//ul[@class='tbs']/li[text()='Results']"))
            )
            results_tab.click()
            print("✓ Clicked Results tab")
            time.sleep(3)
        except TimeoutException:
            try:
                # Alternative: using the data-v attribute
                results_tab = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'Results')]"))
                )
                results_tab.click()
                print("✓ Clicked Results tab (alternative method)")
                time.sleep(3)
            except TimeoutException:
                print("⚠ Could not click Results tab - will try to find results anyway")
        
        # Find the main results container
        print("\nLooking for results container...")
        try:
            # The HTML shows results are in div with class "virtual-rs"
            results_container = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.virtual-rs"))
            )
            print("✓ Found results container (virtual-rs)")
        except TimeoutException:
            try:
                results_container = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-v-22efc919].virtual-rs"))
                )
                print("✓ Found results container with data attribute")
            except TimeoutException:
                print("❌ Could not find results container")
                save_debug_info(driver, session_folder, timestamp)
                delayed_browser_close(driver, 5)
                return None
        
        # Find all week results (multiple .rs divs inside virtual-rs)
        week_containers = results_container.find_elements(By.CSS_SELECTOR, "div.rs")
        print(f"\nFound {len(week_containers)} weeks of results")
        
        if not week_containers:
            print("⚠ No week containers found. Trying alternative selector...")
            week_containers = results_container.find_elements(By.CSS_SELECTOR, ".rs")
            print(f"Found {len(week_containers)} weeks with alternative selector")
        
        all_results = []
        
        # Process each week
        for week_index, week in enumerate(week_containers, 1):
            try:
                print(f"\n{'='*50}")
                print(f"Processing Week {week_index}/{len(week_containers)}")
                print(f"{'='*50}")
                
                # Get week title and time
                try:
                    week_title_elem = week.find_element(By.CSS_SELECTOR, ".rs-t .t")
                    week_time_elem = week.find_element(By.CSS_SELECTOR, ".rs-t .b")
                    
                    week_title = week_title_elem.text
                    week_time = week_time_elem.text
                    
                    print(f"Week: {week_title}")
                    print(f"Time: {week_time}")
                except NoSuchElementException:
                    week_title = f"Week {week_index} (Unknown)"
                    week_time = "Unknown"
                    print(f"Could not find week title/time for week {week_index}")
                
                # Find all matches in this week
                matches = week.find_elements(By.CSS_SELECTOR, ".rs-g")
                print(f"Matches in this week: {len(matches)}")
                
                week_data = {
                    'tournament': week_title,
                    'time': week_time,
                    'matches': []
                }
                
                # Process each match
                for match in matches:
                    try:
                        # Get team names
                        team_elements = match.find_elements(By.CSS_SELECTOR, ".g-t")
                        if len(team_elements) >= 2:
                            home_team = team_elements[0].text
                            away_team = team_elements[1].text
                        else:
                            continue
                        
                        # Get scores
                        score_elements = match.find_elements(By.CSS_SELECTOR, ".g-s span")
                        if len(score_elements) >= 2:
                            home_score = score_elements[0].text
                            away_score = score_elements[1].text
                        else:
                            continue
                        
                        match_data = {
                            'home_team': home_team,
                            'away_team': away_team,
                            'home_score': home_score,
                            'away_score': away_score,
                            'result': f"{home_score}-{away_score}"
                        }
                        
                        week_data['matches'].append(match_data)
                        
                    except Exception as e:
                        print(f"Error parsing match: {e}")
                        continue
                
                if week_data['matches']:
                    all_results.append(week_data)
                    print(f"✓ Added {len(week_data['matches'])} matches from {week_title}")
                else:
                    print(f"⚠ No matches found for {week_title}")
                    
            except Exception as e:
                print(f"Error processing week {week_index}: {e}")
                continue
        
        print("\n" + "=" * 70)
        print(f"SCRAPING COMPLETE")
        print("=" * 70)
        print(f"Total weeks found: {len(all_results)}")
        total_matches = sum(len(week['matches']) for week in all_results)
        print(f"Total matches: {total_matches}")
        
        # Display summary of all weeks
        print("\n" + "-" * 70)
        print("WEEKS SUMMARY")
        print("-" * 70)
        for i, week in enumerate(all_results, 1):
            print(f"{i:2}. {week['tournament']} - {len(week['matches']):2} matches")
        
        # Save results to files (JSON, CSV, Summary only)
        print("\n" + "=" * 70)
        print("SAVING RESULTS")
        print("=" * 70)
        
        saved_files = save_results_to_files(all_results, session_folder, timestamp)
        
        # Update master log
        append_to_master_log(all_results, session_folder, timestamp)
        
        print("\n" + "=" * 70)
        print("✓ SCRAPING COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"\nAll files saved in: {session_folder}")
        print(f"Files created:")
        for file in saved_files:
            print(f"  - {os.path.basename(file)}")
        
        # Schedule browser close
        print("\nScheduling browser close in 5 seconds...")
        delayed_browser_close(driver, 5)
        
        return all_results
        
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        save_debug_info(driver, session_folder, timestamp)
        
        print("\nScheduling browser close in 5 seconds...")
        delayed_browser_close(driver, 5)
        return None

def main():
    """
    Main function - automatically starts a new scraping session
    """
    print("=" * 70)
    print("ODIBETS ODILEAGUE - AUTOMATIC RESULTS SCRAPER")
    print("Scrapes all weeks and matches from the Results tab")
    print("Generates: JSON, CSV, and Summary files only")
    print("=" * 70)
    print("\nBrowser will close automatically 5 seconds after completion")
    print("Results will be stored in timestamped folders")
    print("=" * 70)
    
    # Automatically start a new scraping session
    print("\n" + "=" * 70)
    print("STARTING NEW SCRAPING SESSION")
    print("This will scrape ALL available weeks from the Results tab")
    print("=" * 70)
    
    results = scrape_odileague_all_results()
    
    if results:
        total_weeks = len(results)
        total_matches = sum(len(week['matches']) for week in results)
        print(f"\n✓ Session completed successfully!")
        print(f"  - Weeks scraped: {total_weeks}")
        print(f"  - Total matches: {total_matches}")
    else:
        print("\n❌ Session failed. Check the error messages above.")
    
    # Keep the program alive long enough for browser to close
    print("\n" + "=" * 70)
    print("Program will exit automatically after browser closes")
    print("=" * 70)
    time.sleep(6)  # Wait for browser to close

if __name__ == "__main__":
    main()
