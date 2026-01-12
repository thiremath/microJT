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
from filters import apply_cisco_filters, apply_cvs_filters, apply_adobe_filters
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

# --- Anti-Detection Script (reusable) ---
ANTI_DETECTION_SCRIPT = '''
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    window.chrome = {
        runtime: {}
    };
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
'''

def _apply_anti_detection(driver):
    """Apply anti-detection measures to Chrome driver"""
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': ANTI_DETECTION_SCRIPT
    })

def _create_chrome_options():
    """Create and configure Chrome options"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    return chrome_options

def _find_chromedriver_in_path(driver_path):
    """Find actual chromedriver executable in given path"""
    if os.path.isdir(driver_path):
        for root, dirs, files in os.walk(driver_path):
            for file in files:
                if 'chromedriver' in file.lower() and not file.endswith(('.txt', '.md')):
                    potential_path = os.path.join(root, file)
                    if os.access(potential_path, os.X_OK):
                        return potential_path
    elif not os.access(driver_path, os.X_OK):
        dir_path = os.path.dirname(driver_path)
        for file in os.listdir(dir_path):
            if 'chromedriver' in file.lower() and not file.endswith(('.txt', '.md')):
                potential_path = os.path.join(dir_path, file)
                if os.path.isfile(potential_path) and os.access(potential_path, os.X_OK):
                    return potential_path
    return driver_path if os.access(driver_path, os.X_OK) else None

# --- Function: Setup Chrome Driver ---
def setup_chrome_driver(website_name=None):
    """Setup Chrome driver for cloud deployment"""
    chrome_options = _create_chrome_options()
    
    # Try multiple methods to setup Chrome driver
    driver = None
    
    # Method 1: Try using webdriver-manager
    if CHROME_DRIVER_AVAILABLE:
        try:
            driver_path = ChromeDriverManager().install()
            driver_path = _find_chromedriver_in_path(driver_path)
            if driver_path:
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                _apply_anti_detection(driver)
                print(f"[+] Using ChromeDriver from: {driver_path}")
        except Exception as e:
            print(f"[-] ChromeDriverManager failed: {e}")
    
    # Method 2: Try system chromedriver
    if driver is None:
        try:
            import shutil
            chromedriver_path = shutil.which('chromedriver')
            if chromedriver_path:
                service = Service(chromedriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                _apply_anti_detection(driver)
                print(f"[+] Using system ChromeDriver from: {chromedriver_path}")
            else:
                # Method 3: Try without explicit service
                driver = webdriver.Chrome(options=chrome_options)
                _apply_anti_detection(driver)
                print("[+] Using ChromeDriver found by Selenium")
        except Exception as e:
            print(f"[-] System ChromeDriver failed: {e}")
            # Final fallback
            try:
                driver = webdriver.Chrome(options=chrome_options)
                _apply_anti_detection(driver)
                print("[+] Using ChromeDriver (auto-detected)")
            except Exception as e2:
                raise RuntimeError(f"Failed to setup ChromeDriver. Please install ChromeDriver: {e2}")
    
    return driver

# --- Function: Fetch Rendered Page ---
def get_rendered_content(url, wait_time=None, website_name=None):
    """Fetch rendered page content"""
    if wait_time is None:
        wait_time = PAGE_LOAD_WAIT
    
    driver = setup_chrome_driver(website_name)
    try:
        driver.get(url)
        time.sleep(wait_time)  # wait for JavaScript to load content
        content = driver.page_source
        return content
    finally:
        driver.quit()

# --- Website-Specific Configuration ---
WEBSITE_PATTERNS = {
    'goldman': {
        'url_keywords': ['gs.com', 'goldman'],
        'job_patterns': ["a[href*='/roles/']", "a[href*='/roles']"],
        'url_pattern': r'/roles',
        'validation': lambda href, text: '/roles' in href.lower()
    },
    'apple': {
        'url_keywords': ['apple.com', 'apple'],
        'job_patterns': ["a[href*='/details/']", "a[href*='/details']"],
        'url_pattern': r'/details',
        'validation': lambda href, text: '/details' in href.lower()
    },
    'barclays': {
        'url_keywords': ['barclays'],
        'job_patterns': ["a[href*='/job']", "a[href*='/jobs']"],
        'url_pattern': r'/job',
        'validation': lambda href, text: '/job' in href.lower()
    },
    'microsoft': {
        'url_keywords': ['microsoft.com', 'microsoft'],
        'job_patterns': ["a[href*='/careers/job/']", "a[href*='/job/']", "a[href*='/job']"],
        'url_pattern': r'(/careers/job/\d+|/job/\d+)',
        'non_job_paths': ['/actioncenter', '/saved', '/profile', '/settings', '/applications'],
        'validation': lambda href, text: (re.search(r'(/careers/job/\d+|/job/\d+)', href.lower()) is not None and
                                         not any(path in href.lower() for path in ['/actioncenter', '/saved', '/profile', '/settings', '/applications']))
    },
    'paypal': {
        'url_keywords': ['paypal'],
        'job_patterns': ["a[href*='/job']", "a[href*='/jobs']"],
        'url_pattern': r'/job',
        'validation': lambda href, text: '/job' in href.lower()
    },
    'meta': {
        'url_keywords': ['metacareers.com', 'meta'],
        'job_patterns': ["a[href*='/job_details/']", "a[href*='/job_details']"],
        'url_pattern': r'/job_details',
        'validation': lambda href, text: '/job_details' in href.lower()
    },
    'cvs': {
        'url_keywords': ['cvshealth.com', 'cvs'],
        'job_patterns': ["a[href*='/job/R']", "a[href*='/job/']", "[data-ph-at-id*='job'] a", ".job-result-item a", "[class*='job'] a"],
        'url_pattern': r'/job/(R\d+|[A-Z0-9]+)',
        'non_job_paths': ['/jointalentcommunity', '/careerareas', '/life', '/who-we-are', '/benefits', '/diversity',
                         '/hiring-process', '/events', '/in-store', '/pharmacy', '/clinical', '/warehouse',
                         '/corporate', '/innovation-and-technology', '/customer-care', '/students', '/international', '/search-results'],
        'validation': lambda href, text: (re.search(r'/job/(R\d+|[A-Z0-9]+)', href.lower()) is not None and
                                         not any(path in href.lower() for path in ['/jointalentcommunity', '/careerareas', '/life', '/who-we-are']))
    },
    'cisco': {
        'url_keywords': ['cisco.com', 'cisco'],
        'job_patterns': ["a[href*='/job/']", "a[href*='/job']"],
        'url_pattern': r'/job/\d+/',
        'non_job_paths': ['/jobcart', '/jobsaved'],
        'validation': lambda href, text: (re.search(r'/job/\d+/', href.lower()) is not None and
                                         '/jobcart' not in href.lower() and '/jobsaved' not in href.lower())
    },
    'cognizant': {
        'url_keywords': ['cognizant.com', 'cognizant'],
        'job_patterns': ["a[href*='/jobs/']", "a[href*='/jobs']"],
        'url_pattern': r'/jobs/\d+/',
        'validation': lambda href, text: (re.search(r'/jobs/\d+/', href.lower()) is not None and
                                         not (href.lower().endswith('/jobs/') or '/jobs?' in href.lower() or href.lower().endswith('/jobs')))
    },
    'servicenow': {
        'url_keywords': ['servicenow.com', 'servicenow'],
        'job_patterns': ["a[href*='/jobs/']", "a[href*='/jobs']"],
        'url_pattern': r'/jobs/\d+/',
        'non_job_paths': ['/jobs/saved-jobs', '/jobs/applied', '/jobs/recommended', '/jobs/search', '/jobs/?', '/jobs#'],
        'validation': lambda href, text: (re.search(r'/jobs/\d+/', href.lower()) is not None and
                                         not any(path in href.lower() for path in ['/jobs/saved-jobs', '/jobs/applied', '/jobs/recommended']))
    },
    'oracle': {
        'url_keywords': ['oraclecloud.com', 'jpmc', 'jpmorgan'],
        'job_patterns': ["a[href*='/job/']", ".job-grid-item a", ".job-grid-item_link", "[class*='job-grid-item'] a", "[aria-labelledby] a"],
        'url_pattern': r'/job/\d+/',
        'validation': lambda href, text: re.search(r'/job/\d+/', href.lower()) is not None
    },
    'micron': {
        'url_keywords': ['careers.micron.com', 'micron.com', 'micron'],
        'job_patterns': [
            "a[href*='/job/']", 
            "a[href*='/careers/job/']",
            ".position-title a",
            ".job-card a",
            "[class*='position'] a",
            "[class*='job-card'] a",
            "[data-testid*='job'] a",
            "[data-testid*='position'] a"
        ],
        'url_pattern': r'(/careers/job/|/job/)[^/?]+',
        'validation': lambda href, text: (re.search(r'(/careers/job/|/job/)[^/?]+', href.lower()) is not None and 
                                         not any(path in href.lower() for path in ['/dashboard', '/profile', '/settings', '/applications', '/saved']))
    },
    'salesforce': {
        'url_keywords': ['careers.salesforce.com', 'salesforce.com', 'salesforce'],
        'job_patterns': ["a[href*='/jobs/']", "a[href*='/jobs']", "[data-testid*='job'] a", ".job-card a", ".position-title a"],
        'url_pattern': r'/jobs/[^/]+',
        'validation': lambda href, text: (re.search(r'/jobs/[^/]+', href.lower()) is not None and 
                                         not any(path in href.lower() for path in ['/jobs/?', '/jobs#', '/jobs/search', '/jobs/saved']))
    },
    'adobe': {
        'url_keywords': ['careers.adobe.com', 'adobe.com', 'adobe'],
        'job_patterns': [
            "a[href*='/job/']", 
            "a[href*='/us/en/job/']",
            ".job-card a", 
            ".position-title a",
            "[class*='job'] a",
            "[class*='position'] a",
            "[data-testid*='job'] a"
        ],
        'url_pattern': r'/job/[^/?]+',
        'validation': lambda href, text: (re.search(r'/job/[^/?]+', href.lower()) is not None and 
                                         not any(path in href.lower() for path in ['/search-results', '/jobs?', '/jobs#']))
    }
}

def _get_website_config(website_url, website_name):
    """Get website-specific configuration"""
    url_lower = website_url.lower()
    name_lower = website_name.lower()
    
    for key, config in WEBSITE_PATTERNS.items():
        if any(kw in url_lower or kw in name_lower for kw in config['url_keywords']):
            return config
    return None

def _extract_job_count(page_text):
    """Extract job count from page text"""
    count_patterns = [
        r'(\d+)\s*(?:results?|jobs?|opportunities?|matches?|openings?)',
        r'Showing\s+(\d+)\s+of\s+(\d+)',
        r'(\d+)\s*-\s*(\d+)\s+of\s+(\d+)',
        r'(\d+)\s+results?',
    ]
    
    for pattern in count_patterns:
        matches = re.findall(pattern, page_text, re.IGNORECASE)
        if matches:
            numbers = []
            for match in matches:
                if isinstance(match, tuple):
                    numbers.extend([int(x) for x in match if x.isdigit()])
                elif match.isdigit():
                    numbers.append(int(match))
            
            if numbers:
                return max(numbers), str(matches[0])
    return 0, ''

# Pre-compile skip keywords as set for O(1) lookup
_SKIP_KEYWORDS = frozenset(['apply', 'view all', 'see more', 'next', 'previous', 'page', 'search', 
                            'filter', 'saved jobs', 'applied jobs', 'recommended', 'latest vacancies', 
                            'vacancies', 'saved job', 'jobcart', 'navigating here', 'action center'])

# Pre-compile regex patterns for job ID extraction
_RE_JOB_ID = re.compile(r'/job/([^/?]+)')
_RE_JOB_ID_ALPHANUMERIC = re.compile(r'[A-Z0-9]')
_RE_CVS_JOB_ID = re.compile(r'/job/R\d+/')
_RE_ADOBE_MICRON_JOB = re.compile(r'(?:/careers)?/job/([^/?]+)')

def _extract_jobs_from_links(driver, website_config, website_url, website_name, max_links=100):
    """Extract jobs from links using website-specific patterns, preserving DOM order"""
    jobs = []
    url_lower = website_url.lower()
    name_lower = website_name.lower()
    
    if not website_config:
        # Generic fallback patterns
        job_patterns = ["a[href*='/job']", "a[href*='/roles']", "a[href*='/details']",
                       "a[href*='/job_details']", "a[href*='/career']", "a[href*='/position']"]
    else:
        job_patterns = website_config['job_patterns']
    
    common_selectors = [
        "[data-testid*='job'] a",
        ".job-card a",
        ".job-listing a",
        ".job-title a",
        "[class*='job'] a",
    ]
    
    all_selectors = job_patterns + common_selectors
    validation_func = website_config.get('validation') if website_config else None
    
    # For PayPal and similar sites, try to use a single comprehensive selector first
    # to preserve DOM order better
    is_paypal = 'paypal' in name_lower or 'paypal' in url_lower
    if is_paypal and job_patterns:
        # Try using XPath to get all job links in document order
        try:
            # Build XPath from job patterns
            xpath_parts = []
            for pattern in job_patterns:
                if '/job' in pattern:
                    xpath_parts.append("contains(@href, '/job')")
                elif '/jobs' in pattern:
                    xpath_parts.append("contains(@href, '/jobs')")
            
            if xpath_parts:
                xpath = f"//a[{' or '.join(xpath_parts)}]"
                links = driver.find_elements(By.XPATH, xpath)
                if links:
                    print(f"[+] Found {len(links)} potential job links using XPath (DOM order preserved)")
                    seen_urls = set()
                    for link in links[:max_links]:
                        try:
                            href = link.get_attribute("href")
                            if not href or not href.strip():
                                try:
                                    href = driver.execute_script("return arguments[0].href;", link)
                                except:
                                    continue
                            
                            if not href or not href.strip() or href in seen_urls:
                                continue
                            seen_urls.add(href)
                            
                            text = link.text.strip()
                            if not text or len(text) <= 5:
                                continue
                            
                            href_lower = href.lower()
                            text_lower = text.lower()
                            
                            # Validate link
                            if validation_func:
                                is_job_link = validation_func(href, text)
                            else:
                                is_job_link = any(pattern in href_lower for pattern in 
                                                 ['/job', '/roles', '/details', '/job_details', '/career', '/position', '/jobs'])
                            
                            if is_job_link and not any(skip in text_lower for skip in _SKIP_KEYWORDS):
                                jobs.append({
                                    'title': text[:200],
                                    'url': href,
                                    'identifier': f"{text[:50]}_{href[-30:]}"
                                })
                        except:
                            continue
                    
                    if jobs:
                        print(f"[+] Successfully extracted {len(jobs)} jobs using XPath")
                        return jobs
        except Exception as e:
            print(f"[!] XPath extraction failed, falling back to CSS selectors: {e}")
    
    # Fallback to original CSS selector approach
    for selector in all_selectors:
        try:
            links = driver.find_elements(By.CSS_SELECTOR, selector)
            if not links:
                continue
                
            print(f"[+] Found {len(links)} potential job links with selector: {selector}")
            
            seen_urls = set()  # Deduplicate by URL while preserving order
            for link in links[:max_links]:
                try:
                    href = link.get_attribute("href")
                    if not href or not href.strip():
                        try:
                            href = driver.execute_script("return arguments[0].href;", link)
                        except:
                            continue
                    
                    if not href or not href.strip() or href in seen_urls:
                        continue
                    seen_urls.add(href)
                    
                    text = link.text.strip()
                    if not text or len(text) <= 5:
                        continue
                    
                    href_lower = href.lower()
                    text_lower = text.lower()
                    
                    # Validate link using website-specific validation
                    if validation_func:
                        is_job_link = validation_func(href, text)
                    else:
                        # Generic validation - use set for faster lookup
                        is_job_link = any(pattern in href_lower for pattern in 
                                         ['/job', '/roles', '/details', '/job_details', '/career', '/position', '/jobs'])
                    
                    # Use set for O(1) lookup instead of list iteration
                    if is_job_link and not any(skip in text_lower for skip in _SKIP_KEYWORDS):
                        jobs.append({
                            'title': text[:200],
                            'url': href,
                            'identifier': f"{text[:50]}_{href[-30:]}"
                        })
                except:
                    continue
            
            if jobs:
                print(f"[+] Successfully extracted {len(jobs)} jobs with pattern: {selector}")
                break
        except:
            continue
    
    return jobs

# Pre-compile job keywords as set for faster lookup
_JOB_KEYWORDS = frozenset(['engineer', 'analyst', 'developer', 'manager', 'specialist', 
                          'associate', 'director', 'scientist'])

def _extract_jobs_from_headings(driver, website_url, website_name, max_headings=50):
    """Extract jobs from headings as fallback method"""
    jobs = []
    url_lower = website_url.lower()
    name_lower = website_name.lower()
    is_cvs = 'cvshealth.com' in url_lower or 'cvs' in name_lower
    
    try:
        headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6")
        
        for heading in headings[:max_headings]:
            try:
                text = heading.text.strip()
                if not text or len(text) <= 10 or len(text) >= 200:
                    continue
                
                text_lower = text.lower()
                # Use set for O(1) lookup instead of list iteration
                if not any(keyword in text_lower for keyword in _JOB_KEYWORDS):
                    continue
                
                # Try to find associated link
                href = None
                try:
                    parent_link = heading.find_element(By.XPATH, "./ancestor::a[1]")
                    href = parent_link.get_attribute("href")
                except:
                    try:
                        sibling_link = heading.find_element(By.XPATH, "./following-sibling::a[1] | ./preceding-sibling::a[1]")
                        href = sibling_link.get_attribute("href")
                    except:
                        pass
                
                if href and href.strip():
                    # Validate URL for CVS Health
                    if is_cvs:
                        if re.search(r'/job/R\d+/', href.lower()):
                            jobs.append({
                                'title': text,
                                'url': href,
                                'identifier': f"{text[:50]}_{href[-30:]}" if href else text[:50]
                            })
                    else:
                        jobs.append({
                            'title': text,
                            'url': href,
                            'identifier': f"{text[:50]}_{href[-30:]}" if href else text[:50]
                        })
            except:
                continue
    except Exception as e:
        print(f"[-] Error extracting job headings: {e}")
    
    return jobs

# --- Function: Extract Job Postings ---
def extract_job_postings(driver, website_name):
    """Extract job postings from job board websites"""
    try:
        print(f"[+] Starting job extraction for {website_name}...")
        time.sleep(PAGE_LOAD_WAIT)
        
        # Cache frequently used values
        page_title = driver.title
        print(f"[+] Page title: {page_title}")
        
        page_text = driver.find_element(By.TAG_NAME, "body").text
        current_url = driver.current_url
        current_url_lower = current_url.lower()
        name_lower = website_name.lower()
        
        # Initialize job data structure
        job_data = {
            'page_title': page_title,
            'url': current_url,
            'total_jobs': 0,
            'jobs': [],
            'job_count_text': '',
            'timestamp': datetime.now().isoformat()
        }
        
        # Extract job count
        total_jobs, job_count_text = _extract_job_count(page_text)
        job_data['total_jobs'] = total_jobs
        job_data['job_count_text'] = job_count_text
        if total_jobs > 0:
            print(f"[+] Found job count: {total_jobs}")
        
        # Get website-specific configuration
        website_config = _get_website_config(current_url_lower, website_name)
        
        # Special handling for Oracle Cloud HCM sites
        if website_config and website_config.get('url_keywords', []):
            url_keywords = website_config['url_keywords']
            if any('oraclecloud' in kw or 'jpmc' in kw or 'jpmorgan' in kw for kw in url_keywords):
                jobs = extract_oracle_hcm_jobs(driver, website_name, current_url, current_url_lower)
            else:
                jobs = []
        else:
            jobs = []
        
        # Extract jobs from links if not already found
        if not jobs:
            jobs = _extract_jobs_from_links(driver, website_config, current_url_lower, website_name)
        
        # Generic lenient fallback for specific websites if strict pattern failed
        if not jobs:
            # Check which site needs lenient extraction (cache checks)
            is_cvs = 'cvshealth.com' in current_url_lower or 'cvs' in name_lower
            is_adobe = 'careers.adobe.com' in current_url_lower or 'adobe' in name_lower
            is_micron = 'careers.micron.com' in current_url_lower or 'micron' in name_lower
            
            if is_cvs:
                print("[+] No jobs found with strict pattern, trying lenient approach for CVS Health...")
                try:
                    all_job_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/job/']")
                    print(f"[+] Found {len(all_job_links)} links with /job/ pattern")
                    non_job_paths = frozenset(['/jointalentcommunity', '/careerareas', '/life', '/who-we-are', 
                                              '/benefits', '/diversity', '/hiring-process', '/events', 
                                              '/in-store', '/pharmacy', '/clinical', '/warehouse', 
                                              '/corporate', '/innovation-and-technology', '/customer-care', 
                                              '/students', '/international', '/search-results'])
                    
                    for link in all_job_links[:100]:
                        try:
                            href = link.get_attribute("href") or driver.execute_script("return arguments[0].href;", link)
                            if not href or not href.strip():
                                continue
                            
                            href_lower = href.lower()
                            text = link.text.strip()
                            
                            if '/job/' in href_lower and text and len(text) > 5:
                                if any(path in href_lower for path in non_job_paths):
                                    continue
                                text_lower = text.lower()
                                if any(skip in text_lower for skip in _SKIP_KEYWORDS):
                                    continue
                                job_id_match = _RE_JOB_ID.search(href_lower)
                                if job_id_match:
                                    job_id = job_id_match.group(1)
                                    if _RE_JOB_ID_ALPHANUMERIC.search(job_id) and len(job_id) > 3:
                                        jobs.append({
                                            'title': text[:200],
                                            'url': href,
                                            'identifier': f"{text[:50]}_{href[-30:]}"
                                        })
                        except:
                            continue
                    
                    if jobs:
                        print(f"[+] Found {len(jobs)} jobs with lenient approach")
                except Exception as e:
                    print(f"[-] Error in lenient CVS Health extraction: {e}")
            
            elif is_adobe or is_micron:
                site_name = 'Adobe' if is_adobe else 'Micron'
                print(f"[+] No jobs found with strict pattern, trying lenient approach for {site_name}...")
                try:
                    # Use a single comprehensive XPath to get all job links in DOM order
                    # This preserves the order as they appear on the page
                    xpath = "//a[contains(@href, '/job/') or contains(@href, '/careers/job/') or contains(@href, '/us/en/job/')]"
                    
                    try:
                        all_links = driver.find_elements(By.XPATH, xpath)
                        print(f"[+] Found {len(all_links)} total links using XPath (DOM order preserved)")
                    except:
                        # Fallback to CSS selectors if XPath fails
                        selectors = ["a[href*='/job/']", "a[href*='/careers/job/']", "a[href*='/us/en/job/']"]
                        all_links = []
                        seen_urls_set = set()
                        for selector in selectors:
                            try:
                                links = driver.find_elements(By.CSS_SELECTOR, selector)
                                for link in links:
                                    try:
                                        href = link.get_attribute("href") or driver.execute_script("return arguments[0].href;", link)
                                        if href and href not in seen_urls_set:
                                            seen_urls_set.add(href)
                                            all_links.append(link)
                                    except:
                                        continue
                            except:
                                continue
                        print(f"[+] Found {len(all_links)} total links using CSS selectors")
                    
                    if all_links:
                        # Use frozensets for O(1) lookup
                        non_job_paths = frozenset(['/search-results', '/careers', '/jobs?', '/dashboard', 
                                                   '/profile', '/settings', '/applications', '/saved'])
                        base_url = 'https://careers.adobe.com' if is_adobe else 'https://careers.micron.com'
                        job_pattern = _RE_ADOBE_MICRON_JOB  # Use pre-compiled pattern
                        invalid_job_ids = frozenset(['search', 'results', 'saved', 'applied'])
                        
                        seen_urls = set()
                        for link in all_links[:200]:
                            try:
                                href = link.get_attribute("href")
                                if not href or not href.strip():
                                    href = driver.execute_script("return arguments[0].href;", link)
                                
                                if not href or not href.strip():
                                    continue
                                
                                if href.startswith('/'):
                                    href = f"{base_url}{href}"
                                
                                if href in seen_urls:
                                    continue
                                seen_urls.add(href)
                                
                                href_lower = href.lower()
                                text = link.text.strip()
                                
                                if '/job/' in href_lower and text and len(text) > 5:
                                    # Use set intersection for faster check
                                    if any(path in href_lower for path in non_job_paths):
                                        continue
                                    text_lower = text.lower()
                                    if any(skip in text_lower for skip in _SKIP_KEYWORDS):
                                        continue
                                    
                                    job_match = job_pattern.search(href_lower)
                                    if job_match:
                                        job_id = job_match.group(1)
                                        if job_id and len(job_id) > 3 and job_id not in invalid_job_ids:
                                            jobs.append({
                                                'title': text[:200],
                                                'url': href,
                                                'identifier': f"{text[:50]}_{href[-30:]}"
                                            })
                            except:
                                continue
                    
                    if jobs:
                        print(f"[+] Found {len(jobs)} jobs with lenient approach for {site_name}")
                except Exception as e:
                    print(f"[-] Error in lenient {site_name} extraction: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Fallback: extract from headings if still no jobs
        if not jobs:
            jobs = _extract_jobs_from_headings(driver, current_url_lower, website_name)
        
        # Remove duplicates while preserving extraction order
        # Python dicts maintain insertion order, so first occurrence is preserved
        unique_jobs = {}
        for job in jobs:
            identifier = job.get('identifier', job.get('title', ''))
            if identifier and identifier not in unique_jobs:
                unique_jobs[identifier] = job
        
        # Convert back to list - order is preserved (first occurrence of each job)
        jobs = list(unique_jobs.values())
        
        # Limit to top 8 jobs for specific websites (cache name_lower check)
        name_lower = website_name.lower()
        is_top8_site = 'cvs' in name_lower or 'cvshealth' in name_lower or 'paypal' in name_lower or 'micron' in name_lower
        
        if is_top8_site:
            total_found = len(unique_jobs)
            jobs = jobs[:8]
            site_name = "CVS Health" if ('cvs' in name_lower) else ("PayPal" if 'paypal' in name_lower else "Micron")
            print(f"[+] Limited {site_name} jobs to top 8 (out of {total_found} total)")
        
        job_data['jobs'] = jobs
        
        # Update total_jobs to match actual extracted jobs
        if jobs:
            extracted_count = len(jobs)
            if job_data['total_jobs'] != extracted_count:
                print(f"[+] Updating total_jobs from {job_data['total_jobs']} to {extracted_count} (actual extracted jobs)")
                job_data['total_jobs'] = extracted_count
        
        print(f"[+] Successfully extracted {len(jobs)} unique job postings")
        return job_data
        
    except Exception as e:
        print(f"[-] Error extracting job postings: {e}")
        import traceback
        traceback.print_exc()
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
    driver = setup_chrome_driver(website_name)
    try:
        driver.get(url)
        time.sleep(5)  # wait for JavaScript to load content
        
        # Check if this website needs interactive filtering
        if website_config and website_config.get('interactive') and website_config.get('filters'):
            # Determine which filter function to use based on website
            website_url = url.lower()
            name_lower = website_name.lower()
            
            if 'cisco.com' in website_url or 'cisco' in name_lower:
                apply_cisco_filters(driver, website_config['filters'])
            elif 'cvshealth.com' in website_url or 'cvs' in name_lower:
                apply_cvs_filters(driver, website_config['filters'])
            elif 'adobe.com' in website_url or 'adobe' in name_lower:
                apply_adobe_filters(driver, website_config['filters'])
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
    # Sanitize website name for filename (using pre-compiled pattern)
    safe_name = _RE_SAFE_NAME.sub('_', website_name)
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
    
    # Cache website name check
    name_lower = website_name.lower()
    is_cvs = 'cvs' in name_lower or 'cvshealth' in name_lower
    is_paypal = 'paypal' in name_lower
    is_micron = 'micron' in name_lower
    is_top8_site = is_cvs or is_paypal or is_micron
    
    old_jobs_list = old_data.get('jobs', [])
    new_jobs_list = new_data.get('jobs', [])
    
    if is_top8_site:
        # Only compare top 8 for these websites
        old_jobs_list = old_jobs_list[:8]
        new_jobs_list = new_jobs_list[:8]
        site_type = "CVS Health" if is_cvs else ("PayPal" if is_paypal else "Micron")
        print(f"[+] Comparing top 8 jobs for {site_type}")
    
    # Get job lists as dictionaries for O(1) lookup (preserve order)
    old_jobs = {}
    for job in old_jobs_list:
        identifier = job.get('identifier') or job.get('title', '')
        if identifier and identifier not in old_jobs:
            old_jobs[identifier] = job
    
    new_jobs = {}
    for job in new_jobs_list:
        identifier = job.get('identifier') or job.get('title', '')
        if identifier and identifier not in new_jobs:
            new_jobs[identifier] = job
    
    # Find new jobs using set operations
    old_keys = set(old_jobs.keys())
    new_keys = set(new_jobs.keys())
    new_job_identifiers = new_keys - old_keys
    
    # Only alert if there are new jobs
    if not new_job_identifiers:
        return None
    
    changes = []
    new_jobs_found = [new_jobs[identifier] for identifier in new_job_identifiers]
    
    changes.append(f"🆕 <b>New Jobs Found: {len(new_jobs_found)}</b>")
    if is_top8_site:
        changes.append(f"(Comparing top 8 jobs only)")
    
    # Show new job titles (limit to 10)
    for i, job in enumerate(new_jobs_found[:10], 1):
        title = job.get('title', 'Unknown Position')
        url = job.get('url', '')
        if url:
            changes.append(f"{i}. <a href='{url}'>{title}</a>")
        else:
            changes.append(f"{i}. {title}")
    
    if len(new_jobs_found) > 10:
        changes.append(f"... and {len(new_jobs_found) - 10} more new jobs")
    
    # Add count change info
    old_total = len(old_jobs)
    new_total = len(new_jobs)
    if old_total != new_total:
        changes.append(f"\n📊 <b>Top Jobs Count:</b> {old_total} → {new_total}")
    
    # Only alert about removed jobs if significant (> 2 removed for top 8 sites, > 5 for others)
    removed_job_identifiers = old_keys - new_keys
    threshold = 2 if is_top8_site else 5
    if removed_job_identifiers and len(removed_job_identifiers) > threshold:
        changes.append(f"\n🗑️ <b>Jobs Removed:</b> {len(removed_job_identifiers)} positions no longer in top list")
    
    return "\n".join(changes)

# --- Main Monitoring Function ---
# Pre-compile regex patterns for better performance
_RE_SCRIPT_TAGS = re.compile(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE)
_RE_STYLE_TAGS = re.compile(r'<style[^>]*>.*?</style>', re.DOTALL | re.IGNORECASE)
_RE_COMMENTS = re.compile(r'<!--.*?-->', re.DOTALL)
_RE_DYNAMIC_ATTRS = re.compile(r'\s+(?:data-[^=]*|id|class|data-timestamp|data-time|timestamp|sessionid|csrf-token|data-ph-at-[^=]*|data-testid|aria-[^=]*|data-analytics|data-tracking|data-gtm|data-ga)="[^"]*"')
_RE_TIMESTAMP_ISO = re.compile(r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}[.\d]*[Z+-]?\d*')
_RE_TIMESTAMP_DATE = re.compile(r'\d{1,2}/\d{1,2}/\d{4}')
_RE_HEX_TOKENS = re.compile(r'[a-f0-9]{32,}')
_RE_SHORT_HEX_TOKENS = re.compile(r'\b[a-f0-9]{16,31}\b')  # Shorter hex tokens (16-31 chars)
_RE_POSTED_AGO = re.compile(r'Posted\s+\d+\s+(?:day|days|week|weeks|month|months|hour|hours|minute|minutes)\s+ago', re.IGNORECASE)
_RE_NUMERIC_IDS = re.compile(r'\b\d{10,}\b')  # Long numeric IDs (likely dynamic)
_RE_ANALYTICS_CODES = re.compile(r'(?:utm_[^=&\s]+|_ga[^=&\s]+|gclid[^=&\s]+|fbclid[^=&\s]+)', re.IGNORECASE)
_RE_HTML_TAGS = re.compile(r'<[^>]+>')
_RE_WHITESPACE = re.compile(r'\s+')
_RE_MULTIPLE_SPACES = re.compile(r'\s{2,}')
_RE_URL_WITH_QUERY = re.compile(r'https?://[^\s]+\?[^\s]+')
_RE_PATH_WITH_QUERY = re.compile(r'/[^\s]+\?[^\s]+')
_RE_CVS_JOB_ID_PATTERN = re.compile(r'R\d{7,}')
_RE_CVS_CATEGORY_ID = re.compile(r'category_phs_[^/\s]+')
_RE_CVS_SUBCATEGORY_ID = re.compile(r'subCategory_phs_[^/\s]+')
_RE_CVS_DATA_ATTR = re.compile(r'data-ph-at-[^=:\s]+')
_RE_SAFE_NAME = re.compile(r'[^a-zA-Z0-9_-]')

def clean_content_for_hash(content, website_name=None):
    """Clean HTML content to remove dynamic elements before hashing"""
    # Remove script tags (JavaScript can be dynamic)
    content = _RE_SCRIPT_TAGS.sub('', content)
    
    # Remove style tags
    content = _RE_STYLE_TAGS.sub('', content)
    
    # Remove comments
    content = _RE_COMMENTS.sub('', content)
    
    # Remove common dynamic attributes (timestamps, IDs, analytics, etc.)
    content = _RE_DYNAMIC_ATTRS.sub('', content)
    
    # Remove analytics codes and tracking codes
    content = _RE_ANALYTICS_CODES.sub('', content)
    
    # Remove timestamps in various formats
    content = _RE_TIMESTAMP_ISO.sub('', content)
    content = _RE_TIMESTAMP_DATE.sub('', content)
    
    # Remove "Posted X days ago" patterns (common in job listings)
    content = _RE_POSTED_AGO.sub('', content)
    
    # Remove random IDs and tokens (long hex strings)
    content = _RE_HEX_TOKENS.sub('', content)
    
    # Remove shorter hex tokens (16-31 chars) - common in dynamic IDs
    content = _RE_SHORT_HEX_TOKENS.sub('', content)
    
    # Remove long numeric IDs (likely dynamic identifiers)
    content = _RE_NUMERIC_IDS.sub('', content)
    
    # Extract only text content and links
    text_content = _RE_HTML_TAGS.sub(' ', content)  # Remove HTML tags
    
    # Remove URLs with query parameters (they often contain dynamic tracking)
    text_content = _RE_URL_WITH_QUERY.sub('', text_content)
    text_content = _RE_PATH_WITH_QUERY.sub('', text_content)
    
    # Normalize whitespace
    text_content = _RE_WHITESPACE.sub(' ', text_content)
    text_content = _RE_MULTIPLE_SPACES.sub(' ', text_content)
    text_content = text_content.strip()
    
    # Website-specific cleaning for CVS Health
    if website_name:
        name_lower = website_name.lower()
        if 'cvs' in name_lower or 'cvshealth' in name_lower:
            # Remove common CVS Health dynamic patterns (using pre-compiled patterns)
            text_content = _RE_CVS_JOB_ID_PATTERN.sub('', text_content)  # Remove CVS job IDs like R0798922
            text_content = _RE_CVS_CATEGORY_ID.sub('', text_content)  # Remove category IDs
            text_content = _RE_CVS_SUBCATEGORY_ID.sub('', text_content)  # Remove subcategory IDs
            text_content = _RE_CVS_DATA_ATTR.sub('', text_content)  # Remove CVS data attributes
            # Normalize again after CVS-specific cleaning
            text_content = _RE_WHITESPACE.sub(' ', text_content)
            text_content = _RE_MULTIPLE_SPACES.sub(' ', text_content)
            text_content = text_content.strip()
    
    return text_content

def get_hash(content, website_name=None):
    """Generate hash for content (using cleaned version)"""
    cleaned = clean_content_for_hash(content, website_name)
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
        
        # Cache jobs count (calculate once)
        jobs_count = len(content_data.get('jobs', []))
        current_hash = get_hash(content, website_name)
        
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
        
        # Check if we have jobs extracted (jobs_count already calculated above)
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
                message += f"• Total Jobs: {content_data.get('total_jobs', jobs_count)}\n"
                message += f"• Jobs Tracked: {jobs_count}\n\n"
                message += f"📝 <b>New Job Postings:</b>\n{change_description}"
                
                send_telegram_alert(message)
            else:
                print(f"[=] Hash changed but no new job postings detected (likely page updates or dynamic content)")
            
            # Always save the new hash and data (even if no alert sent)
            save_data(website_name, current_hash, content_data)
        elif jobs_count > 0:
            # Hash unchanged but we have jobs - check if we need to update
            if previous_jobs_count == 0 or jobs_count != previous_jobs_count:
                print(f"[!] Hash unchanged but job count changed ({previous_jobs_count} -> {jobs_count}) - updating data.")
                save_data(website_name, current_hash, content_data)
            elif not previous_data or not previous_data.get('jobs'):
                print(f"[!] Previous data was empty but we have {jobs_count} jobs now - saving data.")
                save_data(website_name, current_hash, content_data)
            else:
                # Ensure data file is up to date even if hash is same
                print(f"[=] No change detected for {website_name}.")
                save_data(website_name, current_hash, content_data)
        else:
            print(f"[=] No change detected for {website_name}.")
            
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
