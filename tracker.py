import os
import time
import hashlib
import requests
import re
import json
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from filters import apply_cisco_filters, apply_cvs_filters
from oracle_hcm_extractor import extract_oracle_hcm_jobs

# Load environment variables from .env file for local development
def load_env_file():
    """Load environment variables from .env file"""
    if os.path.exists('.env'):
        try:
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            print("[+] Loaded environment variables from .env file")
        except Exception as e:
            print(f"[-] Error loading .env file: {e}")

# Load .env file if it exists
load_env_file()

# Try to import webdriver-manager for cloud deployment
try:
    from webdriver_manager.chrome import ChromeDriverManager
    CHROME_DRIVER_AVAILABLE = True
except ImportError:
    CHROME_DRIVER_AVAILABLE = False

# --- Load Configuration ---
def load_config():
    """Load configuration from config.json"""
    config_file = os.getenv('CONFIG_FILE', 'config.json')
    
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file '{config_file}' not found. Please create it.")
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Override with environment variables if available
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN') or config.get('telegram', {}).get('bot_token')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID') or config.get('telegram', {}).get('chat_id')
        
        if not telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment or config.json")
        if not telegram_chat_id:
            raise ValueError("TELEGRAM_CHAT_ID must be set in environment or config.json")
        
        config['telegram']['bot_token'] = telegram_token
        config['telegram']['chat_id'] = telegram_chat_id
        
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")

CONFIG = load_config()
TELEGRAM_BOT_TOKEN = CONFIG['telegram']['bot_token']
TELEGRAM_CHAT_ID = CONFIG['telegram']['chat_id']
GLOBAL_SETTINGS = CONFIG.get('global_settings', {})
DEFAULT_CHECK_INTERVAL = GLOBAL_SETTINGS.get('default_check_interval', 600)
PAGE_LOAD_WAIT = GLOBAL_SETTINGS.get('page_load_wait', 8)

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
    
    # Try multiple methods to setup Chrome driver
    driver = None
    
    # Method 1: Try using webdriver-manager (with better error handling)
    if CHROME_DRIVER_AVAILABLE:
        try:
            driver_path = ChromeDriverManager().install()
            # Fix: webdriver-manager sometimes returns wrong file, find actual chromedriver
            import os
            if os.path.isdir(driver_path):
                # If it's a directory, look for chromedriver inside
                for root, dirs, files in os.walk(driver_path):
                    for file in files:
                        if 'chromedriver' in file.lower() and not file.endswith('.txt') and not file.endswith('.md'):
                            driver_path = os.path.join(root, file)
                            if os.access(driver_path, os.X_OK):
                                break
            elif not os.access(driver_path, os.X_OK):
                # If file exists but not executable, try to find chromedriver in same directory
                dir_path = os.path.dirname(driver_path)
                for file in os.listdir(dir_path):
                    if 'chromedriver' in file.lower() and not file.endswith('.txt') and not file.endswith('.md'):
                        potential_path = os.path.join(dir_path, file)
                        if os.path.isfile(potential_path) and os.access(potential_path, os.X_OK):
                            driver_path = potential_path
                            break
            
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print(f"[+] Using ChromeDriver from: {driver_path}")
        except Exception as e:
            print(f"[-] ChromeDriverManager failed: {e}")
            print("[+] Falling back to system ChromeDriver...")
    
    # Method 2: Try system chromedriver (if installed via Homebrew or system)
    if driver is None:
        try:
            import shutil
            chromedriver_path = shutil.which('chromedriver')
            if chromedriver_path:
                service = Service(chromedriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                print(f"[+] Using system ChromeDriver from: {chromedriver_path}")
            else:
                # Method 3: Try without explicit service (let Selenium find it)
                driver = webdriver.Chrome(options=chrome_options)
                print("[+] Using ChromeDriver found by Selenium")
        except Exception as e:
            print(f"[-] System ChromeDriver failed: {e}")
            # Final fallback: try without service
            try:
                driver = webdriver.Chrome(options=chrome_options)
                print("[+] Using ChromeDriver (auto-detected)")
            except Exception as e2:
                raise RuntimeError(f"Failed to setup ChromeDriver. Please install ChromeDriver: {e2}")
    
    return driver

# --- Function: Fetch Rendered Page ---
def get_rendered_content(url, wait_time=None):
    """Fetch rendered page content"""
    if wait_time is None:
        wait_time = PAGE_LOAD_WAIT
    
    driver = setup_chrome_driver()
    try:
        driver.get(url)
        time.sleep(wait_time)  # wait for JavaScript to load content
        content = driver.page_source
        return content
    finally:
        driver.quit()

# --- Function: Extract Job Postings ---
def extract_job_postings(driver, website_name):
    """Extract job postings from job board websites"""
    try:
        print(f"[+] Starting job extraction for {website_name}...")
        
        # Wait for page to load
        time.sleep(PAGE_LOAD_WAIT)
        
        # Get page title
        page_title = driver.title
        print(f"[+] Page title: {page_title}")
        
        # Extract text content
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Initialize job data structure
        job_data = {
            'page_title': page_title,
            'url': driver.current_url,
            'total_jobs': 0,
            'jobs': [],
            'job_count_text': '',
            'timestamp': datetime.now().isoformat()
        }
        
        # Try to extract job count
        try:
            count_patterns = [
                r'(\d+)\s*(?:results?|jobs?|opportunities?|matches?|openings?)',
                r'Showing\s+(\d+)\s+of\s+(\d+)',
                r'(\d+)\s*-\s*(\d+)\s+of\s+(\d+)',
                r'(\d+)\s+results?',
            ]
            
            for pattern in count_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    # Get the largest number (usually total)
                    numbers = []
                    for match in matches:
                        if isinstance(match, tuple):
                            numbers.extend([int(x) for x in match if x.isdigit()])
                        elif match.isdigit():
                            numbers.append(int(match))
                    
                    if numbers:
                        job_data['total_jobs'] = max(numbers)
                        job_data['job_count_text'] = str(matches[0])
                        print(f"[+] Found job count: {job_data['total_jobs']}")
                        break
        except Exception as e:
            print(f"[-] Error extracting job count: {e}")
        
        # Extract job listings - use website-specific patterns
        jobs = []
        
        # Determine website-specific URL patterns
        current_url_lower = driver.current_url.lower()
        current_url_original = driver.current_url  # Keep original for URL construction
        website_url = current_url_lower
        
        # Special handling for Oracle Cloud HCM sites (JPMC, etc.)
        if 'oraclecloud.com' in website_url or 'jpmc' in website_name.lower() or 'jpmorgan' in website_name.lower():
            jobs = extract_oracle_hcm_jobs(driver, website_name, current_url_original, website_url)
        
        # If we already found jobs with specialized method, skip generic extraction
        if jobs:
            # Remove duplicates
            unique_jobs = {}
            for job in jobs:
                identifier = job.get('identifier', job['title'])
                if identifier not in unique_jobs:
                    unique_jobs[identifier] = job
            jobs = list(unique_jobs.values())
            
            # Ensure jobs list is valid
            if not jobs:
                print(f"[-] Warning: jobs list is empty after deduplication!")
            else:
                print(f"[+] Deduplicated to {len(jobs)} unique jobs")
            
            # Update job_data with jobs
            job_data['jobs'] = jobs.copy() if jobs else []  # Use copy to ensure we have a new list
            if job_data['total_jobs'] == 0 and jobs:
                job_data['total_jobs'] = len(jobs)
            
            # Final verification before return
            print(f"[+] Successfully extracted {len(jobs)} unique job postings")
            
            # Double-check that jobs are actually in job_data
            if len(job_data.get('jobs', [])) != len(jobs):
                job_data['jobs'] = jobs.copy()
            
            return job_data
        
        # Define website-specific patterns
        if 'gs.com' in website_url or 'goldman' in website_name.lower():
            # Goldman Sachs uses /roles
            job_patterns = ["a[href*='/roles/']", "a[href*='/roles']"]
            print("[+] Using GS-specific pattern: /roles")
        elif 'apple.com' in website_url or 'apple' in website_name.lower():
            # Apple uses /details
            job_patterns = ["a[href*='/details/']", "a[href*='/details']"]
            print("[+] Using Apple-specific pattern: /details")
        elif 'barclays' in website_url or 'barclays' in website_name.lower():
            # Barclays uses /job
            job_patterns = ["a[href*='/job']", "a[href*='/jobs']"]
            print("[+] Using Barclays-specific pattern: /job")
        elif 'microsoft.com' in website_url or 'microsoft' in website_name.lower():
            # Microsoft uses /job
            job_patterns = ["a[href*='/job']", "a[href*='/jobs']"]
            print("[+] Using Microsoft-specific pattern: /job")
        elif 'paypal' in website_url or 'paypal' in website_name.lower():
            # PayPal uses /job
            job_patterns = ["a[href*='/job']", "a[href*='/jobs']"]
            print("[+] Using PayPal-specific pattern: /job")
        elif 'metacareers.com' in website_url or 'meta' in website_name.lower():
            # Meta uses /job_details
            job_patterns = ["a[href*='/job_details/']", "a[href*='/job_details']"]
            print("[+] Using Meta-specific pattern: /job_details")
        elif 'cvshealth.com' in website_url or 'cvs' in website_name.lower():
            # CVS Health uses /job or /jobs
            job_patterns = ["a[href*='/job']", "a[href*='/jobs']"]
            print("[+] Using CVS Health-specific pattern: /job")
        elif 'cisco.com' in website_url or 'cisco' in website_name.lower():
            # Cisco uses /job or /jobs
            job_patterns = ["a[href*='/job']", "a[href*='/jobs']"]
            print("[+] Using Cisco-specific pattern: /job")
        elif 'oraclecloud.com' in website_url or 'jpmc' in website_name.lower() or 'jpmorgan' in website_name.lower():
            # Oracle Cloud HCM (JPMC, etc.) uses /job/{job_id}/ pattern
            # Use more specific selectors for Oracle Cloud HCM
            job_patterns = [
                "a[href*='/job/']",  # Links with /job/ followed by job ID
                ".job-grid-item a",
                ".job-grid-item_link",
                "[class*='job-grid-item'] a",
                "[aria-labelledby] a",  # Links with aria-labelledby (contains job ID)
            ]
            print("[+] Using Oracle Cloud HCM-specific pattern: /job/{id}/")
        else:
            # Fallback to common patterns
            job_patterns = [
                "a[href*='/job']",
                "a[href*='/roles']",
                "a[href*='/details']",
                "a[href*='/job_details']",
                "a[href*='/career']",
                "a[href*='/position']",
            ]
            print("[+] Using generic job link patterns")
        
        # Add common selectors
        common_selectors = [
            "[data-testid*='job'] a",
            ".job-card a",
            ".job-listing a",
            ".job-title a",
            "[class*='job'] a",
        ]
        
        # Method 1: Look for job links using website-specific patterns
        try:
            all_selectors = job_patterns + common_selectors
            
            for selector in all_selectors:
                try:
                    links = driver.find_elements(By.CSS_SELECTOR, selector)
                    if links:
                        print(f"[+] Found {len(links)} potential job links with selector: {selector}")
                        for link in links[:100]:  # Limit to first 100
                            try:
                                href = link.get_attribute("href")
                                text = link.text.strip()
                                
                                # Filter for actual job links
                                if href and text and len(text) > 5:
                                    # Verify it matches the expected pattern
                                    href_lower = href.lower()
                                    is_job_link = False
                                    
                                    if 'gs.com' in website_url or 'goldman' in website_name.lower():
                                        is_job_link = '/roles' in href_lower
                                    elif 'apple.com' in website_url or 'apple' in website_name.lower():
                                        is_job_link = '/details' in href_lower
                                    elif 'metacareers.com' in website_url or 'meta' in website_name.lower():
                                        is_job_link = '/job_details' in href_lower
                                    elif 'cvshealth.com' in website_url or 'cvs' in website_name.lower():
                                        is_job_link = '/job' in href_lower
                                    elif 'cisco.com' in website_url or 'cisco' in website_name.lower():
                                        is_job_link = '/job' in href_lower
                                    elif 'oraclecloud.com' in website_url or 'jpmc' in website_name.lower() or 'jpmorgan' in website_name.lower():
                                        # Oracle Cloud HCM: must match /job/{numeric_id}/ pattern
                                        # Exclude the search results page itself (/jobs?)
                                        is_job_link = re.search(r'/job/\d+/', href_lower) is not None
                                        if not is_job_link:
                                            # Also check if it's a job link by checking aria-labelledby for numeric ID
                                            try:
                                                aria_id = link.get_attribute("aria-labelledby")
                                                if aria_id and aria_id.isdigit():
                                                    # Construct the job URL from the job ID
                                                    base_url = re.sub(r'/jobs.*$', '', website_url)
                                                    if '/sites/' in base_url:
                                                        # Extract site path
                                                        site_match = re.search(r'(/sites/[^/]+)', base_url)
                                                        if site_match:
                                                            site_path = site_match.group(1)
                                                            # Get query params from original URL
                                                            query_params = ""
                                                            if '?' in website_url:
                                                                query_params = '?' + website_url.split('?', 1)[1]
                                                            href = f"{base_url.split('?')[0].split('/jobs')[0]}{site_path}/job/{aria_id}/{query_params}"
                                                            is_job_link = True
                                                            # Update href to the constructed URL
                                                            link._href = href
                                            except:
                                                pass
                                    elif any(x in website_url for x in ['barclays', 'microsoft', 'paypal']):
                                        is_job_link = '/job' in href_lower
                                    else:
                                        is_job_link = any(pattern in href_lower for pattern in ['/job', '/roles', '/details', '/job_details', '/career', '/position', '/jobs'])
                                    
                                    if is_job_link:
                                        # Skip navigation and non-job links
                                        skip_keywords = ['apply', 'view all', 'see more', 'next', 'previous', 'page', 'search', 'filter']
                                        if not any(skip in text.lower() for skip in skip_keywords):
                                            jobs.append({
                                                'title': text[:200],
                                                'url': href,
                                                'identifier': f"{text[:50]}_{href[-30:]}"  # Create unique identifier
                                            })
                            except:
                                continue
                        
                        if jobs:
                            print(f"[+] Successfully extracted {len(jobs)} jobs with pattern: {selector}")
                            break
                except:
                    continue
        except Exception as e:
            print(f"[-] Error extracting job links: {e}")
        
        # Method 2: Look for job titles in headings
        if not jobs:
            try:
                headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6")
                for heading in headings[:50]:
                    try:
                        text = heading.text.strip()
                        if text and len(text) > 10 and len(text) < 200:
                            # Check if it looks like a job title
                            job_keywords = ['engineer', 'analyst', 'developer', 'manager', 'specialist', 'associate', 'director', 'scientist']
                            if any(keyword in text.lower() for keyword in job_keywords):
                                # Try to find associated link
                                href = None
                                try:
                                    # Try to find link in parent or siblings
                                    parent_link = heading.find_element(By.XPATH, "./ancestor::a[1]")
                                    href = parent_link.get_attribute("href")
                                except:
                                    try:
                                        sibling_link = heading.find_element(By.XPATH, "./following-sibling::a[1] | ./preceding-sibling::a[1]")
                                        href = sibling_link.get_attribute("href")
                                    except:
                                        pass
                                
                                jobs.append({
                                    'title': text,
                                    'url': href or '',
                                    'identifier': text[:50]
                                })
                    except:
                        continue
            except Exception as e:
                print(f"[-] Error extracting job headings: {e}")
        
        # Remove duplicates based on identifier
        unique_jobs = {}
        for job in jobs:
            identifier = job.get('identifier', job['title'])
            if identifier not in unique_jobs:
                unique_jobs[identifier] = job
        
        job_data['jobs'] = list(unique_jobs.values())
        
        # Update total if we found jobs but no count
        if job_data['total_jobs'] == 0 and job_data['jobs']:
            job_data['total_jobs'] = len(job_data['jobs'])
        
        print(f"[+] Successfully extracted {len(job_data['jobs'])} unique job postings")
        return job_data
        
    except Exception as e:
        print(f"[-] Error extracting job postings: {e}")
        return {
            'error': str(e),
            'jobs': [],
            'total_jobs': 0,
            'timestamp': datetime.now().isoformat()
        }

# --- Function: Apply Cisco Filters ---
# --- Function: Get Detailed Page Content ---
def get_detailed_content(url, website_name, website_config=None):
    """Get both raw content and structured job data"""
    driver = setup_chrome_driver()
    try:
        driver.get(url)
        time.sleep(5)  # wait for JavaScript to load content
        
        # Check if this website needs interactive filtering
        if website_config and website_config.get('interactive') and website_config.get('filters'):
            # Determine which filter function to use based on website
            website_url = url.lower()
            if 'cisco.com' in website_url or 'cisco' in website_name.lower():
                apply_cisco_filters(driver, website_config['filters'])
            elif 'cvshealth.com' in website_url or 'cvs' in website_name.lower():
                apply_cvs_filters(driver, website_config['filters'])
            else:
                # Generic filter application
                apply_cvs_filters(driver, website_config['filters'])
        
        # Get raw content for hash (after filters applied)
        raw_content = driver.page_source
        
        # Extract job postings
        job_data = extract_job_postings(driver, website_name)
        
        # Ensure job_data is a proper dict with all required fields
        if not isinstance(job_data, dict):
            job_data = {
                'page_title': driver.title,
                'url': driver.current_url,
                'total_jobs': 0,
                'jobs': [],
                'job_count_text': '',
                'timestamp': datetime.now().isoformat()
            }
        
        # Ensure jobs is a list
        if 'jobs' not in job_data or not isinstance(job_data['jobs'], list):
            job_data['jobs'] = []
        
        return raw_content, job_data
    finally:
        driver.quit()

# --- Function: Send Telegram Alert ---
def send_telegram_alert(message, is_error=False):
    """Send Telegram alert message"""
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

# --- Function: Get File Paths for Website ---
def get_file_paths(website_name):
    """Get hash and data file paths for a website"""
    # Sanitize website name for filename
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', website_name)
    return {
        'hash_file': f"data/{safe_name}_hash.txt",
        'data_file': f"data/{safe_name}_data.json"
    }

# --- Function: Load Previous Data ---
def load_previous_data(website_name):
    """Load previous hash and content data for a website"""
    paths = get_file_paths(website_name)
    
    # Load hash
    hash_value = None
    if os.path.exists(paths['hash_file']):
        try:
            with open(paths['hash_file'], 'r') as f:
                hash_value = f.read().strip()
        except:
            pass
    
    # Load content data
    content_data = None
    if os.path.exists(paths['data_file']):
        try:
            with open(paths['data_file'], 'r') as f:
                content_data = json.load(f)
        except:
            pass
    
    return hash_value, content_data

# --- Function: Save Data ---
def save_data(website_name, hash_value, content_data):
    """Save hash and content data for a website"""
    paths = get_file_paths(website_name)
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Save hash
    try:
        with open(paths['hash_file'], 'w') as f:
            f.write(hash_value)
    except Exception as e:
        print(f"[-] Error saving hash: {e}")
    
    # Save content data
    try:
        # Ensure content_data has the required structure
        if not isinstance(content_data, dict):
            content_data = {'error': 'Invalid data structure', 'jobs': [], 'total_jobs': 0}
        
        # Ensure jobs is a list
        if 'jobs' not in content_data:
            content_data['jobs'] = []
        if not isinstance(content_data['jobs'], list):
            content_data['jobs'] = list(content_data['jobs']) if content_data['jobs'] else []
        
        # Verify we can serialize
        try:
            json.dumps(content_data)
        except Exception as e:
            print(f"[-] Error: Cannot serialize content_data: {e}")
            # Try to clean the data
            content_data['jobs'] = [
                {
                    'title': str(job.get('title', 'Unknown'))[:200],
                    'url': str(job.get('url', '')),
                    'identifier': str(job.get('identifier', ''))
                }
                for job in content_data.get('jobs', [])
            ]
        
        with open(paths['data_file'], 'w') as f:
            json.dump(content_data, f, indent=2)
        print(f"[+] Successfully saved data to {paths['data_file']}")
    except Exception as e:
        print(f"[-] Error saving data: {e}")
        import traceback
        traceback.print_exc()

# --- Function: Compare Content Data ---
def compare_job_postings(old_data, new_data, website_name):
    """Compare old and new job postings to identify new jobs"""
    if not old_data or not new_data:
        return None  # First run, don't alert
    
    changes = []
    
    # Get job lists
    old_jobs = {job.get('identifier', job.get('title', '')): job for job in old_data.get('jobs', [])}
    new_jobs = {job.get('identifier', job.get('title', '')): job for job in new_data.get('jobs', [])}
    
    # Find new jobs
    new_job_identifiers = set(new_jobs.keys()) - set(old_jobs.keys())
    removed_job_identifiers = set(old_jobs.keys()) - set(new_jobs.keys())
    
    # Compare total job counts
    old_total = old_data.get('total_jobs', len(old_jobs))
    new_total = new_data.get('total_jobs', len(new_jobs))
    
    # Only alert if there are new jobs
    if new_job_identifiers:
        new_jobs_list = [new_jobs[identifier] for identifier in new_job_identifiers]
        
        changes.append(f"🆕 <b>New Jobs Found: {len(new_jobs_list)}</b>")
        
        # Show new job titles (limit to 10)
        for i, job in enumerate(new_jobs_list[:10], 1):
            title = job.get('title', 'Unknown Position')
            url = job.get('url', '')
            if url:
                changes.append(f"{i}. <a href='{url}'>{title}</a>")
            else:
                changes.append(f"{i}. {title}")
        
        if len(new_jobs_list) > 10:
            changes.append(f"... and {len(new_jobs_list) - 10} more new jobs")
        
        # Add count change info
        if old_total != new_total:
            changes.append(f"\n📊 <b>Total Jobs:</b> {old_total} → {new_total}")
    
    # Only alert about removed jobs if significant (> 5 removed)
    if removed_job_identifiers and len(removed_job_identifiers) > 5:
        changes.append(f"\n🗑️ <b>Jobs Removed:</b> {len(removed_job_identifiers)} positions no longer listed")
    
    # If no new jobs found, return None (don't send alert)
    if not changes:
        return None
    
    return "\n".join(changes)

# --- Main Monitoring Function ---
def clean_content_for_hash(content):
    """Clean HTML content to remove dynamic elements before hashing"""
    import re
    
    # Remove script tags (JavaScript can be dynamic)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove style tags
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove comments
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
    # Remove common dynamic attributes (timestamps, IDs, etc.)
    content = re.sub(r'\s+(?:data-[^=]*|id|class|data-timestamp|data-time|timestamp|sessionid|csrf-token)="[^"]*"', '', content)
    
    # Remove timestamps in various formats
    content = re.sub(r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}[.\d]*[Z+-]?\d*', '', content)
    content = re.sub(r'\d{1,2}/\d{1,2}/\d{4}', '', content)
    
    # Remove random IDs and tokens
    content = re.sub(r'[a-f0-9]{32,}', '', content)  # Remove long hex strings (likely tokens)
    
    # Extract only text content and links
    # Get all text nodes
    text_content = re.sub(r'<[^>]+>', ' ', content)  # Remove HTML tags
    text_content = re.sub(r'\s+', ' ', text_content)  # Normalize whitespace
    text_content = text_content.strip()
    
    return text_content

def get_hash(content):
    """Generate hash for content (using cleaned version)"""
    cleaned = clean_content_for_hash(content)
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

def check_website(website_config):
    """Check a single website for changes"""
    website_name = website_config['name']
    url = website_config['url']
    check_interval = website_config.get('check_interval', DEFAULT_CHECK_INTERVAL)
    description = website_config.get('description', '')
    
    try:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking {website_name}...")
        print(f"🔗 URL: {url}")
        
        # Get current content (pass website_config for interactive filtering)
        content, content_data = get_detailed_content(url, website_name, website_config)
        
        # Verify content_data structure
        if not isinstance(content_data, dict):
            raise ValueError(f"content_data must be a dict, got {type(content_data)}")
        
        jobs_count = len(content_data.get('jobs', []))
        current_hash = get_hash(content)
        
        # Load previous data
        last_hash, previous_data = load_previous_data(website_name)
        
        if last_hash is None:
            print(f"[!] First run for {website_name} - saving initial data.")
            save_data(website_name, current_hash, content_data)
            send_telegram_alert(
                f"🔄 <b>Website Tracker Started</b>\n\n"
                f"📌 <b>{website_name}</b>\n"
                f"🔗 {url}\n\n"
                f"Initial data saved. Monitoring for changes..."
            )
            return
        
        # Check if we have jobs extracted
        jobs_count = len(content_data.get('jobs', []))
        previous_jobs_count = len(previous_data.get('jobs', [])) if previous_data else 0
        
        if last_hash != current_hash:
            print(f"[!] Hash changed for {website_name} - checking for new job postings...")
            
            # Compare job postings to find new jobs
            change_description = compare_job_postings(previous_data, content_data, website_name)
            
            # Only send alert if there are new jobs
            if change_description:
                print(f"[!] New job postings detected in {website_name}!")
                
                # Create detailed message
                message = f"<b>🆕 New Jobs: {website_name}</b>\n\n"
                if description:
                    message += f"📝 {description}\n\n"
                message += f"🔗 <a href='{url}'>View All Jobs</a>\n\n"
                message += f"📊 <b>Current Status:</b>\n"
                message += f"• Total Jobs: {content_data.get('total_jobs', len(content_data.get('jobs', [])))}\n"
                message += f"• Jobs Tracked: {len(content_data.get('jobs', []))}\n\n"
                message += f"📝 <b>New Job Postings:</b>\n{change_description}"
                
                send_telegram_alert(message)
            else:
                print(f"[=] Hash changed but no new job postings detected (likely page updates or dynamic content)")
            
            # Always save the new hash and data (even if no alert sent)
            save_data(website_name, current_hash, content_data)
        elif jobs_count > 0 and (previous_jobs_count == 0 or jobs_count != previous_jobs_count):
            # Hash is the same but we have jobs and the count changed, or we didn't have jobs before
            # This can happen if the page structure changed but content hash is similar
            print(f"[!] Hash unchanged but job count changed ({previous_jobs_count} -> {jobs_count}) - updating data.")
            save_data(website_name, current_hash, content_data)
        elif jobs_count > 0 and previous_jobs_count == 0:
            # We have jobs now but didn't before - save it
            print(f"[!] Jobs found for first time ({jobs_count} jobs) - saving data.")
            save_data(website_name, current_hash, content_data)
        else:
            print(f"[=] No change detected for {website_name}.")
            # Even if hash is same, if we have jobs and previous data was empty, save it
            if jobs_count > 0 and (not previous_data or not previous_data.get('jobs')):
                print(f"[!] Previous data was empty but we have {jobs_count} jobs now - saving data.")
                save_data(website_name, current_hash, content_data)
            elif jobs_count > 0:
                # If we have jobs but hash is same, still update the data file to ensure it's current
                # This handles cases where jobs were extracted but hash didn't change (e.g., same page structure)
                print(f"[!] Hash unchanged but we have {jobs_count} jobs - ensuring data file is up to date.")
                save_data(website_name, current_hash, content_data)
            
    except Exception as e:
        error_msg = (
            f"<b>Website Tracker Error</b>\n\n"
            f"❌ Error checking <b>{website_name}</b>:\n"
            f"🔗 {url}\n\n"
            f"Error: {str(e)}"
        )
        send_telegram_alert(error_msg, is_error=True)
        print(f"[-] Error checking {website_name}: {e}")

def monitor_website(website_config):
    """Monitor a single website in a loop"""
    website_name = website_config['name']
    check_interval = website_config.get('check_interval', DEFAULT_CHECK_INTERVAL)
    
    print(f"🚀 Starting monitor for {website_name} (interval: {check_interval}s)")
    
    while True:
        check_website(website_config)
        time.sleep(check_interval)

# --- Run Loop ---
if __name__ == "__main__":
    print("🚀 Starting Generic Website Tracker...")
    print(f"📡 Telegram Bot: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"⏱️  Default Check Interval: {DEFAULT_CHECK_INTERVAL} seconds")
    print(f"🌍 Environment: {'Production' if os.getenv('RENDER') else 'Development'}")
    print("-" * 50)
    
    # Get enabled websites
    websites = [w for w in CONFIG.get('websites', []) if w.get('enabled', True)]
    
    if not websites:
        print("❌ No enabled websites found in configuration!")
        exit(1)
    
    print(f"\n📋 Monitoring {len(websites)} website(s):")
    for website in websites:
        print(f"  • {website['name']} - {website['url']}")
    
    # Send startup message
    website_list = "\n".join([f"• {w['name']}" for w in websites])
    send_telegram_alert(
        f"🚀 <b>Website Tracker Started</b>\n\n"
        f"📊 Monitoring {len(websites)} website(s):\n{website_list}\n\n"
        f"Monitoring for changes with detailed detection..."
    )
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Monitor all websites
    if len(websites) == 1:
        # Single website - simple loop
        monitor_website(websites[0])
    else:
        # Multiple websites - use threads
        threads = []
        for website in websites:
            thread = threading.Thread(target=monitor_website, args=(website,), daemon=True)
            thread.start()
            threads.append(thread)
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n[!] Stopping tracker...")
