import os
import time
import hashlib
import requests
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Try to import webdriver-manager for cloud deployment
try:
    from webdriver_manager.chrome import ChromeDriverManager
    CHROME_DRIVER_AVAILABLE = True
except ImportError:
    CHROME_DRIVER_AVAILABLE = False

# --- CONFIG ---
# Use environment variables if available, otherwise use defaults
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 600))  # 10 minutes
HASH_FILE = "gs_jobs_hash.txt"
JOBS_DATA_FILE = "gs_jobs_data.txt"
URL = "https://higher.gs.com/results?EXPERIENCE_LEVEL=Analyst|Associate&JOB_FUNCTION=Software%20Engineering&LOCATION=Albany|New%20York|Atlanta|Boston|Chicago|Dallas|Houston|Irving|Richardson|Draper|Salt%20Lake%20City|Jersey%20City|Los%20Angeles|Newport%20Beach|San%20Francisco|Miami|West%20Palm%20Beach|Philadelphia|Seattle|Troy|Washington|Wilmington&page=1&sort=POSTED_DATE"

# Telegram configuration - use environment variables if available
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', "7623240757:AAHiPQ8QuwZN8SYRvtCVl4RwvF04nCTwP3E")
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', "1059855653")

# --- Function: Setup Chrome Driver ---
def setup_chrome_driver():
    """Setup Chrome driver for cloud deployment"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # For cloud deployment
    if CHROME_DRIVER_AVAILABLE:
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"[-] ChromeDriverManager failed: {e}")
            driver = webdriver.Chrome(options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
    
    return driver

# --- Function: Fetch Rendered Page ---
def get_rendered_content(url):
    driver = setup_chrome_driver()
    try:
        driver.get(url)
        time.sleep(5)  # wait for JavaScript to load content
        content = driver.page_source
        return content
    finally:
        driver.quit()

# --- Function: Extract Job Information ---
def extract_job_info(driver):
    """Extract meaningful job information from the page"""
    try:
        print("[+] Starting job extraction...")
        
        # Wait for page to load
        time.sleep(8)  # Give more time for JavaScript to load
        
        # Get page title to verify we're on the right page
        page_title = driver.title
        print(f"[+] Page title: {page_title}")
        
        # Look for job count information first
        total_count = 0
        showing_count = 0
        
        try:
            # Method 1: Look for "Showing X of Y matches" text
            count_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Showing') and contains(text(), 'of') and contains(text(), 'matches')]")
            if count_elements:
                count_text = count_elements[0].text
                print(f"[+] Found count text: {count_text}")
                match = re.search(r'Showing (\d+) of (\d+) matches', count_text)
                if match:
                    showing_count = int(match.group(1))
                    total_count = int(match.group(2))
                    print(f"[+] Parsed job count: {showing_count} of {total_count}")
            
            # Method 2: Look for other count patterns
            if total_count == 0:
                count_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'results') or contains(text(), 'jobs') or contains(text(), 'opportunities')]")
                for elem in count_elements:
                    text = elem.text.lower()
                    if 'results' in text or 'jobs' in text or 'opportunities' in text:
                        numbers = re.findall(r'\d+', text)
                        if len(numbers) >= 2:
                            total_count = int(numbers[-1])  # Last number is usually total
                            showing_count = int(numbers[0])  # First number is usually showing
                            print(f"[+] Found job count from text: {showing_count} of {total_count}")
                            break
        except Exception as e:
            print(f"[-] Error extracting job count: {e}")
        
        # Try multiple approaches to find job listings
        jobs = []
        
        # Approach 1: Look for job links (most reliable for GS)
        print("[+] Trying job links approach...")
        try:
            job_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/roles/']")
            print(f"[+] Found {len(job_links)} job links")
            
            for i, link in enumerate(job_links[:20]):  # Limit to first 20
                try:
                    # Get the text content which contains job title
                    job_text = link.text.strip()
                    if not job_text or len(job_text) < 10:
                        continue
                    
                    # Extract job title from the text
                    title = job_text
                    
                    # Try to extract location from the text
                    location = "Unknown Location"
                    if "-" in job_text:
                        parts = job_text.split("-")
                        if len(parts) >= 2:
                            location = parts[1]  # Second part is usually location
                    
                    # Get the job URL
                    job_url = link.get_attribute("href")
                    
                    jobs.append({
                        'title': title,
                        'location': location,
                        'skill': 'Software Engineering',
                        'url': job_url,
                        'raw_text': job_text
                    })
                    
                except Exception as e:
                    print(f"[-] Error processing job link {i}: {e}")
                    continue
                    
        except Exception as e:
            print(f"[-] Error with job links method: {e}")
        
        # Approach 2: Look for elements with job-related text
        if not jobs:
            print("[+] Trying job-related text approach...")
            try:
                # Look for elements containing job-related keywords
                job_keywords = ['Engineer', 'Analyst', 'Associate', 'Software', 'Developer']
                
                for keyword in job_keywords:
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                    print(f"[+] Found {len(elements)} elements with '{keyword}'")
                    
                    for elem in elements:
                        text = elem.text.strip()
                        if text and len(text) > 10 and len(text) < 200:
                            # Check if this looks like a job title
                            if any(word in text for word in ['Engineer', 'Analyst', 'Associate', 'Software']):
                                # Extract location if possible
                                location = "Unknown Location"
                                if "-" in text:
                                    parts = text.split("-")
                                    if len(parts) >= 2:
                                        location = parts[1]
                                
                                jobs.append({
                                    'title': text,
                                    'location': location,
                                    'skill': 'Software Engineering',
                                    'raw_text': text
                                })
                                
                                if len(jobs) >= 20:  # Limit results
                                    break
                    
                    if len(jobs) >= 20:
                        break
                        
            except Exception as e:
                print(f"[-] Error with job-related text method: {e}")
        
        # Approach 3: Look for any clickable elements that might be jobs
        if not jobs:
            print("[+] Trying clickable elements approach...")
            try:
                # Look for any clickable elements that might contain job info
                clickable_elements = driver.find_elements(By.CSS_SELECTOR, "a, button, [role='button']")
                print(f"[+] Found {len(clickable_elements)} clickable elements")
                
                for elem in clickable_elements[:50]:  # Check first 50
                    try:
                        text = elem.text.strip()
                        if text and len(text) > 10 and len(text) < 200:
                            # Check if this looks like a job
                            if any(word in text for word in ['Engineer', 'Analyst', 'Associate', 'Software']):
                                location = "Unknown Location"
                                if "-" in text:
                                    parts = text.split("-")
                                    if len(parts) >= 2:
                                        location = parts[1]
                                
                                jobs.append({
                                    'title': text,
                                    'location': location,
                                    'skill': 'Software Engineering',
                                    'raw_text': text
                                })
                                
                                if len(jobs) >= 10:  # Limit results
                                    break
                    except:
                        continue
                        
            except Exception as e:
                print(f"[-] Error with clickable elements method: {e}")
        
        # Remove duplicates based on title
        unique_jobs = []
        seen_titles = set()
        for job in jobs:
            if job['title'] not in seen_titles:
                unique_jobs.append(job)
                seen_titles.add(job['title'])
        
        print(f"[+] Successfully extracted {len(unique_jobs)} unique jobs")
        
        # Show some examples
        for i, job in enumerate(unique_jobs[:3]):
            print(f"  {i+1}. {job['title']} ({job['location']})")
        
        return {
            'total_count': total_count,
            'showing_count': showing_count,
            'jobs': unique_jobs,
            'timestamp': datetime.now().isoformat(),
            'extraction_method': 'enhanced'
        }
        
    except Exception as e:
        print(f"[-] Error extracting job information: {e}")
        # Return basic info even if extraction fails
        return {
            'total_count': 0,
            'showing_count': 0,
            'jobs': [],
            'timestamp': datetime.now().isoformat(),
            'extraction_method': 'fallback',
            'error': str(e)
        }

# --- Function: Get Detailed Page Content ---
def get_detailed_content(url):
    """Get both raw content and structured job data"""
    driver = setup_chrome_driver()
    try:
        driver.get(url)
        time.sleep(5)  # wait for JavaScript to load content
        
        # Get raw content for hash
        raw_content = driver.page_source
        
        # Extract structured job information
        job_info = extract_job_info(driver)
        
        return raw_content, job_info
    finally:
        driver.quit()

# --- Function: Send Telegram Alert ---
def send_telegram_alert(message, is_error=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Add timestamp to message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = "❌ ERROR" if is_error else "🚨 CHANGE DETECTED"
    
    formatted_message = f"{prefix}\n⏰ {timestamp}\n\n{message}"
    
    data = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": formatted_message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print(f"[Telegram] ✅ Message sent successfully")
        else:
            print(f"[Telegram] ❌ Error {response.status_code}: {response.text}")
    except requests.exceptions.Timeout:
        print("[-] Telegram timeout error")
    except requests.exceptions.RequestException as e:
        print(f"[-] Telegram request error: {e}")
    except Exception as e:
        print(f"[-] Telegram error: {e}")

# --- Function: Load Previous Job Data ---
def load_previous_job_data():
    if not os.path.exists(JOBS_DATA_FILE):
        return None
    try:
        with open(JOBS_DATA_FILE, "r") as f:
            import json
            return json.load(f)
    except:
        return None

# --- Function: Save Job Data ---
def save_job_data(job_data):
    try:
        with open(JOBS_DATA_FILE, "w") as f:
            import json
            json.dump(job_data, f, indent=2)
    except Exception as e:
        print(f"[-] Error saving job data: {e}")

# --- Function: Compare Job Data ---
def compare_job_data(old_data, new_data):
    """Compare old and new job data to identify changes"""
    if not old_data or not new_data:
        return "Initial data collection"
    
    changes = []
    
    # Compare total counts
    if old_data.get('total_count') != new_data.get('total_count'):
        old_count = old_data.get('total_count', 0)
        new_count = new_data.get('total_count', 0)
        if new_count > old_count:
            changes.append(f"📈 <b>New jobs added!</b> Total increased from {old_count} to {new_count}")
        else:
            changes.append(f"📉 <b>Jobs removed!</b> Total decreased from {old_count} to {new_count}")
    
    # Compare individual jobs
    old_jobs = {job['title']: job for job in old_data.get('jobs', [])}
    new_jobs = {job['title']: job for job in new_data.get('jobs', [])}
    
    # Find new jobs
    new_job_titles = set(new_jobs.keys()) - set(old_jobs.keys())
    if new_job_titles:
        changes.append(f"🆕 <b>New positions:</b>")
        for title in list(new_job_titles)[:5]:  # Show first 5
            job = new_jobs[title]
            changes.append(f"• {title} ({job['location']})")
        if len(new_job_titles) > 5:
            changes.append(f"• ... and {len(new_job_titles) - 5} more")
    
    # Find removed jobs
    removed_job_titles = set(old_jobs.keys()) - set(new_jobs.keys())
    if removed_job_titles:
        changes.append(f"🗑️ <b>Removed positions:</b>")
        for title in list(removed_job_titles)[:3]:  # Show first 3
            changes.append(f"• {title}")
        if len(removed_job_titles) > 3:
            changes.append(f"• ... and {len(removed_job_titles) - 3} more")
    
    if not changes:
        changes.append("🔄 <b>Content updated</b> (specific changes not detected)")
    
    return "\n\n".join(changes)

# --- Main Monitoring Function ---
def get_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def load_last_hash():
    if not os.path.exists(HASH_FILE):
        return None
    with open(HASH_FILE, "r") as f:
        return f.read().strip()

def save_hash(h):
    with open(HASH_FILE, "w") as f:
        f.write(h)

def check_for_changes():
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for changes...")
        
        # Get both raw content and structured data
        content, job_data = get_detailed_content(URL)
        current_hash = get_hash(content)
        last_hash = load_last_hash()
        previous_job_data = load_previous_job_data()

        if last_hash is None:
            print("[!] First run - saving initial data.")
            save_hash(current_hash)
            save_job_data(job_data)
            send_telegram_alert("🔄 <b>Website Tracker Started</b>\n\nInitial job data saved. Monitoring for changes...")
            return

        if last_hash != current_hash:
            print("[!] Detected change in GS job listings.")
            
            # Compare job data for meaningful changes
            change_description = compare_job_data(previous_job_data, job_data)
            
            # Create detailed message
            message = f"<b>GS Job Listings Updated!</b>\n\n"
            message += f"🔗 <a href='{URL}'>View Updated Listings</a>\n\n"
            message += f"📊 <b>Current Status:</b>\n"
            message += f"• Total Jobs: {job_data.get('total_count', 'N/A')}\n"
            message += f"• Showing: {job_data.get('showing_count', 'N/A')}\n\n"
            message += f"📝 <b>Changes Detected:</b>\n{change_description}"
            
            send_telegram_alert(message)
            save_hash(current_hash)
            save_job_data(job_data)
        else:
            print("[=] No change detected.")
            
    except Exception as e:
        error_msg = f"<b>Website Tracker Error</b>\n\n❌ Error occurred while checking for changes:\n{str(e)}"
        send_telegram_alert(error_msg, is_error=True)
        print(f"[-] Error in check_for_changes: {e}")

# --- Run Loop ---
if __name__ == "__main__":
    print("🚀 Starting GS Job Listings Tracker...")
    print(f"📡 Telegram Bot: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"🔗 Monitoring: {URL}")
    print(f"⏱️  Check Interval: {CHECK_INTERVAL} seconds")
    print(f"🌍 Environment: {'Production' if os.getenv('RENDER') else 'Development'}")
    print("-" * 50)
    
    # Send startup message
    send_telegram_alert("🚀 <b>GS Job Tracker Started</b>\n\nMonitoring for new job postings with detailed change detection...")
    
    while True:
        check_for_changes()
        time.sleep(CHECK_INTERVAL)