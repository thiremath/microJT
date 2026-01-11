"""
Oracle Cloud HCM Job Extractor
Specialized extraction logic for Oracle Cloud HCM-based career sites (e.g., JPMorgan Chase)
"""
import re
import time
from selenium.webdriver.common.by import By


def extract_oracle_hcm_jobs(driver, website_name, current_url_original, website_url):
    """
    Extract job listings from Oracle Cloud HCM sites (e.g., JPMorgan Chase)
    
    Args:
        driver: Selenium WebDriver instance
        website_name: Name of the website being scraped
        current_url_original: Original (non-lowercased) URL
        website_url: Lowercased URL for pattern matching
        
    Returns:
        list: List of job dictionaries with 'title', 'url', and 'identifier' keys
    """
    jobs = []
    
    if 'oraclecloud.com' not in website_url and 'jpmc' not in website_name.lower() and 'jpmorgan' not in website_name.lower():
        return jobs
    
    print("[+] Using specialized Oracle Cloud HCM extraction method")
    try:
        # Wait a bit more for dynamic content to load
        time.sleep(3)
        
        # Method 1: Look for job-grid-item elements with aria-labelledby (contains job ID)
        # Try multiple selector strategies
        job_items = []
        selectors_to_try = [
            "[class*='job-grid-item']",
            ".job-grid-item",
            "[class*='job-grid'] [aria-labelledby]",
            "[data-bind*='job']",
            "[aria-labelledby]",
            "a[href*='/job/']",
            "a[data-bind*='getJobUrl']",
        ]
        
        for selector in selectors_to_try:
            try:
                found_items = driver.find_elements(By.CSS_SELECTOR, selector)
                if found_items:
                    print(f"[+] Found {len(found_items)} elements with selector: {selector}")
                    job_items.extend(found_items)
            except:
                continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_job_items = []
        for item in job_items:
            try:
                item_id = id(item)
                if item_id not in seen:
                    seen.add(item_id)
                    unique_job_items.append(item)
            except:
                continue
        
        job_items = unique_job_items
        print(f"[+] Found {len(job_items)} unique job-related elements")
        
        for item in job_items:
            try:
                job_id = None
                href = None
                
                # Strategy 1: Get job ID from aria-labelledby
                job_id = item.get_attribute("aria-labelledby")
                if job_id and not job_id.isdigit():
                    # Sometimes aria-labelledby contains non-numeric values, skip
                    job_id = None
                
                # Strategy 2: Try to find a child element with aria-labelledby
                if not job_id:
                    try:
                        child_with_aria = item.find_element(By.CSS_SELECTOR, "[aria-labelledby]")
                        job_id = child_with_aria.get_attribute("aria-labelledby")
                        if job_id and not job_id.isdigit():
                            job_id = None
                    except:
                        pass
                
                # Strategy 3: Extract from href if available
                try:
                    # Check if item itself is a link
                    tag_name = item.tag_name.lower()
                    if tag_name == 'a':
                        href = item.get_attribute("href")
                    else:
                        # Try to find link element
                        try:
                            link_elem = item.find_element(By.CSS_SELECTOR, "a")
                            href = link_elem.get_attribute("href")
                        except:
                            # Try XPath to find any link
                            try:
                                link_elem = item.find_element(By.XPATH, ".//a")
                                href = link_elem.get_attribute("href")
                            except:
                                pass
                    
                    # Extract job ID from href if it matches pattern
                    if href:
                        job_id_match = re.search(r'/job/(\d+)/', href, re.IGNORECASE)
                        if job_id_match:
                            job_id = job_id_match.group(1)
                except Exception as e:
                    pass
                
                # Strategy 4: Extract from data-bind attribute (Knockout.js)
                if not job_id:
                    try:
                        data_bind = item.get_attribute("data-bind")
                        if data_bind:
                            # Look for job.id in data-bind
                            job_id_match = re.search(r'job\.id[:\s]*(\d+)', data_bind)
                            if not job_id_match:
                                # Try to find numeric ID in data-bind
                                job_id_match = re.search(r'(\d{6,})', data_bind)
                            if job_id_match:
                                job_id = job_id_match.group(1)
                    except:
                        pass
                
                if job_id and job_id.isdigit():
                    # Construct the job URL
                    # Pattern: https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/{job_id}/?...
                    # Use original URL (not lowercased) for construction
                    base_url = current_url_original.split('?')[0]  # Remove query params
                    # Replace /jobs with /job/{job_id}/
                    if '/jobs' in base_url:
                        job_url = base_url.replace('/jobs', f'/job/{job_id}/')
                    else:
                        # Fallback: try to find the base path and construct
                        site_match = re.search(r'(https://[^/]+/hcmUI/CandidateExperience/en/sites/[^/]+)', current_url_original, re.IGNORECASE)
                        if site_match:
                            base_path = site_match.group(1)
                            job_url = f"{base_path}/job/{job_id}/"
                        else:
                            # Use href if available, otherwise construct from base
                            if href and '/job/' in href:
                                job_url = href
                            else:
                                job_url = f"{base_url}/job/{job_id}/"
                    
                    # Add query params if they exist
                    if '?' in current_url_original:
                        query_params = '?' + current_url_original.split('?', 1)[1]
                        if '?' not in job_url:
                            job_url = job_url.rstrip('/') + '/' + query_params
                    
                    # Get job title
                    job_title = ""
                    try:
                        # Try to find title in various places
                        title_elem = item.find_element(By.CSS_SELECTOR, "h1, h2, h3, h4, .job-title, [class*='title']")
                        job_title = title_elem.text.strip()
                    except:
                        try:
                            # Fallback: get text from the item
                            job_title = item.text.strip().split('\n')[0]
                        except:
                            job_title = f"Job {job_id}"
                    
                    if job_title and len(job_title) > 5:
                        jobs.append({
                            'title': job_title[:200],
                            'url': job_url,
                            'identifier': f"jpmc_{job_id}"
                        })
            except Exception as e:
                print(f"[-] Error processing job item: {e}")
                continue
        
        # Method 2: Look for links matching /job/{numeric_id}/ pattern
        if not jobs:
            print("[+] Trying method 2: Direct link pattern matching")
            all_links = driver.find_elements(By.CSS_SELECTOR, "a")
            print(f"[+] Found {len(all_links)} total links on page")
            for link in all_links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    
                    # Must match /job/{numeric_id}/ pattern and not be the search results page
                    href_lower = href.lower()
                    if re.search(r'/job/\d+/', href_lower) and '/jobs?' not in href_lower:
                        # Extract job ID
                        job_id_match = re.search(r'/job/(\d+)/', href_lower)
                        if job_id_match:
                            job_id = job_id_match.group(1)
                            text = link.text.strip()
                            if not text or len(text) < 5:
                                # Try to get text from parent or nearby elements
                                try:
                                    parent = link.find_element(By.XPATH, "./..")
                                    text = parent.text.strip().split('\n')[0]
                                except:
                                    try:
                                        # Try to find text in siblings
                                        sibling = link.find_element(By.XPATH, "./following-sibling::*[1] | ./preceding-sibling::*[1]")
                                        text = sibling.text.strip().split('\n')[0]
                                    except:
                                        text = f"Job {job_id}"
                            
                            if text and len(text) > 5 and text.lower() not in ['apply', 'view', 'see more', 'next', 'previous']:
                                # Ensure URL has query params if original had them
                                if '?' in current_url_original and '?' not in href:
                                    query_params = '?' + current_url_original.split('?', 1)[1]
                                    href = href.rstrip('/') + '/' + query_params
                                
                                jobs.append({
                                    'title': text[:200],
                                    'url': href,
                                    'identifier': f"jpmc_{job_id}"
                                })
                except Exception as e:
                    continue
        
        # Method 3: Use JavaScript to extract job data from the page
        if not jobs:
            print("[+] Trying method 3: JavaScript extraction")
            try:
                # Execute JavaScript to find all elements with job IDs
                job_data_js = driver.execute_script("""
                    var jobs = [];
                    // Find all elements with aria-labelledby containing numeric IDs
                    var elements = document.querySelectorAll('[aria-labelledby]');
                    for (var i = 0; i < elements.length; i++) {
                        var elem = elements[i];
                        var ariaId = elem.getAttribute('aria-labelledby');
                        if (ariaId && /^\\d+$/.test(ariaId)) {
                            var job = {
                                id: ariaId,
                                title: elem.textContent.trim().substring(0, 200) || 'Job ' + ariaId,
                                href: null
                            };
                            // Try to find link
                            var link = elem.querySelector('a') || elem.closest('a');
                            if (link) {
                                job.href = link.href;
                            }
                            jobs.push(job);
                        }
                    }
                    // Also find all links with /job/ pattern
                    var links = document.querySelectorAll('a[href*="/job/"]');
                    for (var i = 0; i < links.length; i++) {
                        var link = links[i];
                        var href = link.href;
                        var match = href.match(/\\/job\\/(\\d+)\\//i);
                        if (match && href.indexOf('/jobs?') === -1) {
                            var jobId = match[1];
                            var exists = jobs.some(function(j) { return j.id === jobId; });
                            if (!exists) {
                                jobs.push({
                                    id: jobId,
                                    title: link.textContent.trim().substring(0, 200) || 'Job ' + jobId,
                                    href: href
                                });
                            }
                        }
                    }
                    return jobs;
                """)
                
                if job_data_js and len(job_data_js) > 0:
                    print(f"[+] JavaScript found {len(job_data_js)} jobs")
                    for job_js in job_data_js:
                        try:
                            # Handle both dict and object access
                            if isinstance(job_js, dict):
                                job_id = str(job_js.get('id', ''))
                                job_title = job_js.get('title', f'Job {job_id}')
                                job_href = job_js.get('href', '')
                            else:
                                job_id = str(getattr(job_js, 'id', ''))
                                job_title = getattr(job_js, 'title', f'Job {job_id}')
                                job_href = getattr(job_js, 'href', '')
                            
                            if job_id and job_id.isdigit():
                                # Construct URL if not available
                                if not job_href or '/job/' not in str(job_href):
                                    base_url = current_url_original.split('?')[0]
                                    if '/jobs' in base_url:
                                        job_url = base_url.replace('/jobs', f'/job/{job_id}/')
                                    else:
                                        site_match = re.search(r'(https://[^/]+/hcmUI/CandidateExperience/en/sites/[^/]+)', current_url_original, re.IGNORECASE)
                                        if site_match:
                                            job_url = f"{site_match.group(1)}/job/{job_id}/"
                                        else:
                                            job_url = f"{base_url}/job/{job_id}/"
                                    
                                    # Add query params if they exist
                                    if '?' in current_url_original:
                                        query_params = '?' + current_url_original.split('?', 1)[1]
                                        job_url = job_url.rstrip('/') + '/' + query_params
                                    job_href = job_url
                                else:
                                    # Add query params if missing
                                    if '?' in current_url_original and '?' not in str(job_href):
                                        query_params = '?' + current_url_original.split('?', 1)[1]
                                        job_href = str(job_href).rstrip('/') + '/' + query_params
                                
                                job_title_str = str(job_title).strip()
                                if job_title_str and len(job_title_str) > 5:
                                    jobs.append({
                                        'title': job_title_str[:200],
                                        'url': str(job_href),
                                        'identifier': f"jpmc_{job_id}"
                                    })
                        except Exception as e:
                            print(f"[-] Error processing JS job data: {e}")
                            continue
            except Exception as e:
                print(f"[-] Error in JavaScript extraction: {e}")
        
        if jobs:
            print(f"[+] Successfully extracted {len(jobs)} jobs using Oracle Cloud HCM method")
    except Exception as e:
        print(f"[-] Error in Oracle Cloud HCM extraction: {e}")
    
    return jobs
