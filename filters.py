"""
Website-specific filter functions for interactive job boards.
This module contains functions to apply filters on websites that require
user interaction before displaying job listings.
"""

import time
import traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


# --- Function: Wait for Cisco Filters to Load ---
def wait_for_cisco_filters(driver, max_wait=15):
    """Wait for Cisco Careers filter elements to be visible"""
    try:
        print("[+] Waiting for Cisco filters to load...")
        wait = WebDriverWait(driver, max_wait)
        
        # Wait for at least one filter checkbox to be visible
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='checkbox']"))
        )
        print("[+] Cisco filters are visible")
        return True
    except Exception as e:
        print(f"[-] Filters did not load within {max_wait} seconds: {e}")
        return False


# --- Function: Apply Cisco Filters ---
def apply_cisco_filters(driver, filters_config):
    """Apply filters for Cisco Careers job search"""
    try:
        print("[+] Applying Cisco filters...")
        time.sleep(5)  # Initial wait for page to load
        
        # Wait for filters to be visible
        if not wait_for_cisco_filters(driver):
            print("[-] Warning: Filters may not be fully loaded")
        
        # Try to expand filter sections if they're collapsed
        try:
            # Look for collapsed filter sections and expand them
            expand_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-expanded, 'false')] | //*[@role='button' and contains(@aria-expanded, 'false')]")
            for btn in expand_buttons[:5]:  # Limit to first 5
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.5)
                    btn.click()
                    time.sleep(1)
                except:
                    continue
        except:
            pass
        
        time.sleep(2)  # Additional wait after expanding sections
        
        # Apply Experience Level filters (select multiple categories)
        if filters_config.get('experience_levels'):
            experience_levels = filters_config['experience_levels']
            print(f"[+] Selecting experience levels: {experience_levels}")
            
            for level in experience_levels:
                try:
                    # Try multiple selectors for experience level checkboxes
                    level_selectors = [
                        # Try by exact label text match
                        f"//label[normalize-space(text())='{level}']",
                        # Try by label containing text
                        f"//label[contains(text(), '{level}')]",
                        # Try finding label, then get input by @for
                        f"//label[contains(text(), '{level}') and @for]",
                        # Try finding input that comes before or after label
                        f"//label[contains(text(), '{level}')]/preceding-sibling::input[@type='checkbox']",
                        f"//label[contains(text(), '{level}')]/following-sibling::input[@type='checkbox']",
                        # Try by span or div containing text
                        f"//*[normalize-space(text())='{level}']/ancestor::*[1]//input[@type='checkbox']",
                        f"//*[contains(text(), '{level}')]/ancestor::li//input[@type='checkbox']",
                        f"//*[contains(text(), '{level}')]/ancestor::div//input[@type='checkbox']",
                        # Try by aria-label
                        f"//input[@type='checkbox' and contains(@aria-label, '{level}')]",
                    ]
                    
                    level_clicked = False
                    for i, selector in enumerate(level_selectors):
                        try:
                            level_elements = driver.find_elements(By.XPATH, selector)
                            if level_elements:
                                print(f"[DEBUG] Experience level selector {i+1} found {len(level_elements)} elements")
                                for level_element in level_elements:
                                    try:
                                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", level_element)
                                        time.sleep(1)
                                        
                                        # If it's an input, check if already selected
                                        if level_element.tag_name == 'input':
                                            if not level_element.is_selected():
                                                driver.execute_script("arguments[0].click();", level_element)
                                                level_clicked = True
                                                print(f"[+] Experience level '{level}' selected (input)")
                                            else:
                                                print(f"[+] Experience level '{level}' already selected")
                                                level_clicked = True
                                        elif level_element.tag_name == 'label':
                                            # It's a label, try to find associated input by @for
                                            for_attr = level_element.get_attribute('for')
                                            if for_attr:
                                                try:
                                                    input_element = driver.find_element(By.ID, for_attr)
                                                    if not input_element.is_selected():
                                                        driver.execute_script("arguments[0].click();", input_element)
                                                        level_clicked = True
                                                        print(f"[+] Experience level '{level}' selected (via label @for)")
                                                    else:
                                                        print(f"[+] Experience level '{level}' already selected")
                                                        level_clicked = True
                                                except:
                                                    # Fallback: click the label itself
                                                    driver.execute_script("arguments[0].click();", level_element)
                                                    level_clicked = True
                                                    print(f"[+] Experience level '{level}' selected (label)")
                                            else:
                                                # No @for attribute, click label
                                                driver.execute_script("arguments[0].click();", level_element)
                                                level_clicked = True
                                                print(f"[+] Experience level '{level}' selected (label)")
                                        else:
                                            # Other element type, try clicking it
                                            driver.execute_script("arguments[0].click();", level_element)
                                            level_clicked = True
                                            print(f"[+] Experience level '{level}' selected (other)")
                                        
                                        if level_clicked:
                                            time.sleep(2)  # Wait for filter to apply
                                            break
                                    except Exception as e:
                                        print(f"[DEBUG] Error clicking element: {e}")
                                        continue
                                
                                if level_clicked:
                                    break
                        except Exception as e:
                            print(f"[DEBUG] Selector {i+1} error: {e}")
                            continue
                    
                    if not level_clicked:
                        print(f"[-] Could not find experience level: {level}")
                        # Debug: Try to find all experience level checkboxes
                        try:
                            all_levels = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
                            print(f"[DEBUG] Found {len(all_levels)} checkboxes total")
                            print(f"[DEBUG] Available experience levels:")
                            for lev in all_levels[:10]:
                                try:
                                    lev_id = lev.get_attribute('id')
                                    lev_label = lev.get_attribute('aria-label')
                                    
                                    # Try to find associated label
                                    label_text = None
                                    if lev_id:
                                        try:
                                            label = driver.find_element(By.XPATH, f"//label[@for='{lev_id}']")
                                            label_text = label.text.strip()
                                        except:
                                            pass
                                    
                                    print(f"[DEBUG]   - id={lev_id}, aria-label={lev_label}, label text={label_text}")
                                except:
                                    pass
                        except Exception as e:
                            print(f"[DEBUG] Error finding experience levels: {e}")
                except Exception as e:
                    print(f"[-] Error applying experience level filter '{level}': {e}")
                    traceback.print_exc()
        
        # Apply Country filter
        if filters_config.get('country'):
            try:
                country_text = filters_config['country']
                print(f"[+] Selecting country: {country_text}")
                time.sleep(2)  # Wait after experience level selection
                
                country_selectors = [
                    # Try by exact label text match
                    f"//label[normalize-space(text())='{country_text}']",
                    # Try by label containing text
                    f"//label[contains(text(), '{country_text}')]",
                    # Try finding label, then get input by @for
                    f"//label[contains(text(), '{country_text}') and @for]",
                    # Try finding input that comes before or after label
                    f"//label[contains(text(), '{country_text}')]/preceding-sibling::input[@type='checkbox']",
                    f"//label[contains(text(), '{country_text}')]/following-sibling::input[@type='checkbox']",
                    # Try by parent container
                    f"//*[normalize-space(text())='{country_text}']/ancestor::*[1]//input[@type='checkbox']",
                    f"//*[contains(text(), '{country_text}')]/ancestor::li//input[@type='checkbox']",
                    f"//*[contains(text(), '{country_text}')]/ancestor::div//input[@type='checkbox']",
                    # Try by aria-label
                    f"//input[@type='checkbox' and contains(@aria-label, '{country_text}')]",
                ]
                
                country_clicked = False
                for i, selector in enumerate(country_selectors):
                    try:
                        country_elements = driver.find_elements(By.XPATH, selector)
                        if country_elements:
                            print(f"[DEBUG] Country selector {i+1} found {len(country_elements)} elements")
                            for country_element in country_elements:
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", country_element)
                                    time.sleep(1)
                                    
                                    # If it's an input, check if already selected
                                    if country_element.tag_name == 'input':
                                        if not country_element.is_selected():
                                            driver.execute_script("arguments[0].click();", country_element)
                                            country_clicked = True
                                            print(f"[+] Country '{country_text}' selected (input)")
                                        else:
                                            print(f"[+] Country '{country_text}' already selected")
                                            country_clicked = True
                                    elif country_element.tag_name == 'label':
                                        # It's a label, try to find associated input by @for
                                        for_attr = country_element.get_attribute('for')
                                        if for_attr:
                                            try:
                                                input_element = driver.find_element(By.ID, for_attr)
                                                if not input_element.is_selected():
                                                    driver.execute_script("arguments[0].click();", input_element)
                                                    country_clicked = True
                                                    print(f"[+] Country '{country_text}' selected (via label @for)")
                                                else:
                                                    print(f"[+] Country '{country_text}' already selected")
                                                    country_clicked = True
                                            except:
                                                # Fallback: click the label itself
                                                driver.execute_script("arguments[0].click();", country_element)
                                                country_clicked = True
                                                print(f"[+] Country '{country_text}' selected (label)")
                                        else:
                                            # No @for attribute, click label
                                            driver.execute_script("arguments[0].click();", country_element)
                                            country_clicked = True
                                            print(f"[+] Country '{country_text}' selected (label)")
                                    else:
                                        # Other element type, try clicking it
                                        driver.execute_script("arguments[0].click();", country_element)
                                        country_clicked = True
                                        print(f"[+] Country '{country_text}' selected (other)")
                                    
                                    if country_clicked:
                                        time.sleep(2)  # Wait for filter to apply
                                        break
                                except Exception as e:
                                    print(f"[DEBUG] Error clicking element: {e}")
                                    continue
                            
                            if country_clicked:
                                break
                    except Exception as e:
                        print(f"[DEBUG] Selector {i+1} error: {e}")
                        continue
                
                if not country_clicked:
                    print(f"[-] Could not find country: {country_text}")
                    # Debug: Try to find all country checkboxes
                    try:
                        all_countries = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
                        print(f"[DEBUG] Found {len(all_countries)} checkboxes total")
                        print(f"[DEBUG] Available countries:")
                        for cntry in all_countries[:10]:
                            try:
                                cntry_id = cntry.get_attribute('id')
                                cntry_label = cntry.get_attribute('aria-label')
                                
                                # Try to find associated label
                                label_text = None
                                if cntry_id:
                                    try:
                                        label = driver.find_element(By.XPATH, f"//label[@for='{cntry_id}']")
                                        label_text = label.text.strip()
                                    except:
                                        pass
                                
                                print(f"[DEBUG]   - id={cntry_id}, aria-label={cntry_label}, label text={label_text}")
                            except:
                                pass
                    except Exception as e:
                        print(f"[DEBUG] Error finding countries: {e}")
            except Exception as e:
                print(f"[-] Error applying country filter: {e}")
                traceback.print_exc()
        
        # Apply Sort by Most Recent
        if filters_config.get('sort_by') == 'Most Recent':
            try:
                print("[+] Sorting by Most Recent...")
                time.sleep(2)  # Wait after country selection
                
                # Try multiple methods to find and click sort
                sort_selectors = [
                    "//select[contains(@class, 'sort')]",
                    "//select[contains(@id, 'sort')]",
                    "//select[contains(@name, 'sort')]",
                    "//select[@aria-label*='sort' or @aria-label*='Sort']",
                    "//*[contains(text(), 'Sort by')]/following-sibling::select",
                    "//*[contains(text(), 'Sort by')]/parent::*/select",
                ]
                
                sort_applied = False
                for selector in sort_selectors:
                    try:
                        sort_elements = driver.find_elements(By.XPATH, selector)
                        if sort_elements:
                            for sort_element in sort_elements:
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sort_element)
                                    time.sleep(1)
                                    
                                    # Try select dropdown
                                    if sort_element.tag_name == 'select':
                                        select = Select(sort_element)
                                        try:
                                            select.select_by_visible_text("Most Recent")
                                            sort_applied = True
                                            print("[+] Sorted by Most Recent (visible text)")
                                        except:
                                            try:
                                                select.select_by_value("most_recent")
                                                sort_applied = True
                                                print("[+] Sorted by Most Recent (value)")
                                            except:
                                                try:
                                                    select.select_by_value("Most Recent")
                                                    sort_applied = True
                                                    print("[+] Sorted by Most Recent (value uppercase)")
                                                except:
                                                    # Try by index (usually Most Recent is option 1 or 2)
                                                    try:
                                                        select.select_by_index(1)  # 0-indexed
                                                        sort_applied = True
                                                        print("[+] Sorted by Most Recent (by index)")
                                                    except:
                                                        pass
                                    
                                    if sort_applied:
                                        time.sleep(3)  # Wait for results to update
                                        break
                                except Exception as e:
                                    print(f"[DEBUG] Error with sort element: {e}")
                                    continue
                            
                            if sort_applied:
                                break
                    except Exception as e:
                        print(f"[DEBUG] Sort selector error: {e}")
                        continue
                
                # If select dropdown didn't work, try button/link approach
                if not sort_applied:
                    try:
                        sort_button_selectors = [
                            "//*[contains(text(), 'Sort by')]",
                            "//*[contains(text(), 'Most Recent')]",
                            "//button[contains(@aria-label, 'sort') or contains(@aria-label, 'Sort')]",
                        ]
                        
                        for selector in sort_button_selectors:
                            try:
                                sort_elements = driver.find_elements(By.XPATH, selector)
                                for sort_element in sort_elements:
                                    try:
                                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sort_element)
                                        time.sleep(1)
                                        
                                        if sort_element.tag_name in ['button', 'a', 'span', 'div']:
                                            driver.execute_script("arguments[0].click();", sort_element)
                                            time.sleep(1)
                                            # Then try to find and click "Most Recent"
                                            try:
                                                most_recent = driver.find_element(By.XPATH, "//*[contains(text(), 'Most Recent')]")
                                                driver.execute_script("arguments[0].click();", most_recent)
                                                sort_applied = True
                                                print("[+] Sorted by Most Recent (button/link)")
                                                time.sleep(3)
                                                break
                                            except:
                                                pass
                                        
                                        if sort_applied:
                                            break
                                    except:
                                        continue
                                
                                if sort_applied:
                                    break
                            except:
                                continue
                    except Exception as e:
                        print(f"[DEBUG] Button/link sort error: {e}")
                
                if not sort_applied:
                    print("[-] Could not apply sort by Most Recent")
                    # Debug: Try to find all select elements
                    try:
                        all_selects = driver.find_elements(By.XPATH, "//select")
                        print(f"[DEBUG] Found {len(all_selects)} select elements")
                        for sel in all_selects[:5]:
                            try:
                                sel_id = sel.get_attribute('id')
                                sel_name = sel.get_attribute('name')
                                sel_class = sel.get_attribute('class')
                                print(f"[DEBUG]   Select: id={sel_id}, name={sel_name}, class={sel_class}")
                            except:
                                pass
                    except:
                        pass
            except Exception as e:
                print(f"[-] Error applying sort: {e}")
                traceback.print_exc()
        
        print("[+] Cisco filters applied, waiting for results to load...")
        time.sleep(5)  # Wait for filtered results to load
        
    except Exception as e:
        print(f"[-] Error applying Cisco filters: {e}")
        traceback.print_exc()


# --- Function: Wait for CVS Filters to Load ---
def wait_for_cvs_filters(driver, max_wait=15):
    """Wait for CVS Health filter elements to be visible"""
    try:
        print("[+] Waiting for CVS filters to load...")
        wait = WebDriverWait(driver, max_wait)
        
        # Wait for at least one filter checkbox to be visible
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='checkbox' and (contains(@id, 'category_phs_') or contains(@id, 'subCategory_phs_'))]"))
        )
        print("[+] CVS filters are visible")
        return True
    except Exception as e:
        print(f"[-] Filters did not load within {max_wait} seconds: {e}")
        return False


# --- Function: Apply CVS Health Filters ---
def apply_cvs_filters(driver, filters_config):
    """Apply filters for CVS Health job search"""
    try:
        print("[+] Applying CVS Health filters...")
        time.sleep(5)  # Initial wait for page to load
        
        # Wait for filters to be visible
        if not wait_for_cvs_filters(driver):
            print("[-] Warning: Filters may not be fully loaded")
        
        # Try to expand filter sections if they're collapsed
        try:
            # Look for collapsed filter sections and expand them
            expand_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-expanded, 'false')] | //*[@role='button' and contains(@aria-expanded, 'false')]")
            for btn in expand_buttons[:5]:  # Limit to first 5
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.5)
                    btn.click()
                    time.sleep(1)
                except:
                    continue
        except:
            pass
        
        time.sleep(2)  # Additional wait after expanding sections
        
        # Apply Category filter
        if filters_config.get('category'):
            try:
                category_text = filters_config['category']
                print(f"[+] Selecting category: {category_text}")
                
                # Wait a bit more for filters to be visible
                time.sleep(2)
                
                # CVS uses specific ID pattern: category_phs_{Category Name}{Number}
                # Try multiple approaches with more specific patterns
                category_selectors = [
                    # Try by exact data attribute match
                    f"//input[@data-ph-at-text='{category_text}' and @type='checkbox']",
                    # Try by aria-label containing the text
                    f"//input[@type='checkbox' and contains(@aria-label, '{category_text}')]",
                    # Try by ID pattern - CVS uses: category_phs_{Category Name}{Number}
                    f"//input[@type='checkbox' and contains(@id, 'category_phs_{category_text}')]",
                    # Try finding label by text, then get input by @for attribute
                    f"//label[normalize-space(text())='{category_text}' and @for]/@for",
                    # Try finding label, then find input with matching id from @for
                    f"//label[contains(text(), '{category_text}') and @for]",
                    # Try finding input that comes before or after label with matching text
                    f"//label[contains(text(), '{category_text}')]/preceding-sibling::input[@type='checkbox']",
                    f"//label[contains(text(), '{category_text}')]/following-sibling::input[@type='checkbox']",
                    # Try finding by parent container
                    f"//*[contains(text(), '{category_text}')]/ancestor::*[1]//input[@type='checkbox']",
                    f"//*[normalize-space(text())='{category_text}']/ancestor::li//input[@type='checkbox']",
                    f"//*[normalize-space(text())='{category_text}']/ancestor::div//input[@type='checkbox']",
                ]
                
                category_clicked = False
                for i, selector in enumerate(category_selectors):
                    try:
                        # Special handling for @for attribute selector
                        if selector.endswith('/@for'):
                            # Get the @for attribute value, then find input with that id
                            labels = driver.find_elements(By.XPATH, selector.replace('/@for', ''))
                            for label in labels:
                                try:
                                    for_attr = label.get_attribute('for')
                                    if for_attr:
                                        input_element = driver.find_element(By.ID, for_attr)
                                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_element)
                                        time.sleep(1)
                                        if not input_element.is_selected():
                                            driver.execute_script("arguments[0].click();", input_element)
                                            category_clicked = True
                                            print(f"[+] Category '{category_text}' selected (via label @for)")
                                            break
                                except:
                                    continue
                            if category_clicked:
                                break
                        else:
                            category_elements = driver.find_elements(By.XPATH, selector)
                            if category_elements:
                                print(f"[DEBUG] Selector {i+1} found {len(category_elements)} elements")
                                for category_element in category_elements:
                                    try:
                                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", category_element)
                                        time.sleep(1)
                                        
                                        # If it's an input, check if already selected
                                        if category_element.tag_name == 'input':
                                            if not category_element.is_selected():
                                                # Use JavaScript click for more reliability
                                                driver.execute_script("arguments[0].click();", category_element)
                                                category_clicked = True
                                                print(f"[+] Category '{category_text}' selected (input)")
                                            else:
                                                print(f"[+] Category '{category_text}' already selected")
                                                category_clicked = True
                                        elif category_element.tag_name == 'label':
                                            # It's a label, try to find associated input by @for
                                            for_attr = category_element.get_attribute('for')
                                            if for_attr:
                                                try:
                                                    input_element = driver.find_element(By.ID, for_attr)
                                                    if not input_element.is_selected():
                                                        driver.execute_script("arguments[0].click();", input_element)
                                                        category_clicked = True
                                                        print(f"[+] Category '{category_text}' selected (via label @for)")
                                                    else:
                                                        print(f"[+] Category '{category_text}' already selected")
                                                        category_clicked = True
                                                except:
                                                    # Fallback: click the label itself
                                                    driver.execute_script("arguments[0].click();", category_element)
                                                    category_clicked = True
                                                    print(f"[+] Category '{category_text}' selected (label)")
                                            else:
                                                # No @for attribute, click label
                                                driver.execute_script("arguments[0].click();", category_element)
                                                category_clicked = True
                                                print(f"[+] Category '{category_text}' selected (label)")
                                        else:
                                            # Other element type, try clicking it
                                            driver.execute_script("arguments[0].click();", category_element)
                                            category_clicked = True
                                            print(f"[+] Category '{category_text}' selected (other)")
                                        
                                        if category_clicked:
                                            time.sleep(3)  # Wait for filter to apply
                                            break
                                    except Exception as e:
                                        print(f"[DEBUG] Error clicking element: {e}")
                                        continue
                                
                                if category_clicked:
                                    break
                    except Exception as e:
                        print(f"[DEBUG] Selector {i+1} error: {e}")
                        continue
                
                if not category_clicked:
                    print(f"[-] Could not find category: {category_text}")
                    # Debug: Try to find all category checkboxes and their labels
                    try:
                        all_categories = driver.find_elements(By.XPATH, "//input[@type='checkbox' and contains(@id, 'category_phs_')]")
                        print(f"[DEBUG] Found {len(all_categories)} category checkboxes total")
                        print(f"[DEBUG] Available categories:")
                        for cat in all_categories[:10]:
                            try:
                                cat_id = cat.get_attribute('id')
                                cat_label = cat.get_attribute('aria-label')
                                cat_data = cat.get_attribute('data-ph-at-text')
                                
                                # Try to find associated label
                                label_text = None
                                try:
                                    label = driver.find_element(By.XPATH, f"//label[@for='{cat_id}']")
                                    label_text = label.text.strip()
                                except:
                                    pass
                                
                                print(f"[DEBUG]   - id={cat_id}")
                                print(f"            aria-label={cat_label}")
                                print(f"            data-ph-at-text={cat_data}")
                                print(f"            label text={label_text}")
                            except Exception as e:
                                print(f"[DEBUG]   Error reading category: {e}")
                        
                        # Also try to find all labels with category text
                        all_labels = driver.find_elements(By.XPATH, "//label[contains(@for, 'category_phs_')]")
                        print(f"[DEBUG] Found {len(all_labels)} category labels")
                        for label in all_labels[:10]:
                            try:
                                label_text = label.text.strip()
                                label_for = label.get_attribute('for')
                                print(f"[DEBUG]   Label: '{label_text}' -> for='{label_for}'")
                            except:
                                pass
                    except Exception as e:
                        print(f"[DEBUG] Error finding categories: {e}")
                        traceback.print_exc()
            except Exception as e:
                print(f"[-] Error applying category filter: {e}")
                traceback.print_exc()
        
        # Apply Sub Category filter
        if filters_config.get('sub_category'):
            try:
                sub_category_text = filters_config['sub_category']
                print(f"[+] Selecting sub-category: {sub_category_text}")
                time.sleep(2)  # Wait after category selection
                
                # CVS uses specific ID pattern: subCategory_phs_{Sub Category Name}{Number}
                sub_category_selectors = [
                    # Try by exact data attribute match
                    f"//input[@data-ph-at-text='{sub_category_text}' and @type='checkbox']",
                    # Try by aria-label containing the text
                    f"//input[@type='checkbox' and contains(@aria-label, '{sub_category_text}')]",
                    # Try by ID pattern
                    f"//input[@type='checkbox' and contains(@id, 'subCategory_phs_{sub_category_text}')]",
                    # Try finding label first, then the associated input
                    f"//label[contains(text(), '{sub_category_text}') and @for]",
                    f"//label[contains(text(), '{sub_category_text}')]/preceding-sibling::input[@type='checkbox']",
                    f"//label[contains(text(), '{sub_category_text}')]/following-sibling::input[@type='checkbox']",
                    # Generic fallback
                    f"//*[contains(text(), '{sub_category_text}')]/ancestor::li//input[@type='checkbox']",
                ]
                
                sub_category_clicked = False
                for i, selector in enumerate(sub_category_selectors):
                    try:
                        sub_category_elements = driver.find_elements(By.XPATH, selector)
                        if sub_category_elements:
                            print(f"[DEBUG] Sub-category selector {i+1} found {len(sub_category_elements)} elements")
                            for sub_category_element in sub_category_elements:
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sub_category_element)
                                    time.sleep(1)
                                    
                                    # If it's an input, check if already selected
                                    if sub_category_element.tag_name == 'input':
                                        if not sub_category_element.is_selected():
                                            driver.execute_script("arguments[0].click();", sub_category_element)
                                            sub_category_clicked = True
                                            print(f"[+] Sub-category '{sub_category_text}' selected (input)")
                                        else:
                                            print(f"[+] Sub-category '{sub_category_text}' already selected")
                                            sub_category_clicked = True
                                    else:
                                        # It's a label, click it
                                        driver.execute_script("arguments[0].click();", sub_category_element)
                                        sub_category_clicked = True
                                        print(f"[+] Sub-category '{sub_category_text}' selected (label)")
                                    
                                    if sub_category_clicked:
                                        time.sleep(3)  # Wait for filter to apply
                                        break
                                except Exception as e:
                                    continue
                            
                            if sub_category_clicked:
                                break
                    except:
                        continue
                
                if not sub_category_clicked:
                    print(f"[-] Could not find sub-category: {sub_category_text}")
                    # Debug: Try to find all sub-category checkboxes
                    try:
                        all_sub_categories = driver.find_elements(By.XPATH, "//input[@type='checkbox' and contains(@id, 'subCategory_phs_')]")
                        print(f"[DEBUG] Found {len(all_sub_categories)} sub-category checkboxes total")
                    except:
                        pass
            except Exception as e:
                print(f"[-] Error applying sub-category filter: {e}")
                traceback.print_exc()
        
        # Apply Sort by Recent
        if filters_config.get('sort_by') == 'Recent':
            try:
                print("[+] Sorting by Recent...")
                # CVS uses select element with id="sortselect"
                sort_selectors = [
                    "//select[@id='sortselect']",
                    "//select[@data-ph-at-id='sortby-drop-down']",
                    "//select[contains(@aria-label, 'Sort by')]",
                ]
                
                sort_applied = False
                for selector in sort_selectors:
                    try:
                        sort_element = driver.find_element(By.XPATH, selector)
                        driver.execute_script("arguments[0].scrollIntoView(true);", sort_element)
                        time.sleep(1)
                        
                        select = Select(sort_element)
                        # Try to select "Recent" - value is "Most recent"
                        try:
                            select.select_by_value("Most recent")
                            sort_applied = True
                            print("[+] Sorted by Recent (Most recent)")
                        except:
                            try:
                                select.select_by_visible_text("Recent")
                                sort_applied = True
                                print("[+] Sorted by Recent")
                            except:
                                # Try by index (usually Recent is option 2)
                                try:
                                    select.select_by_index(1)  # 0-indexed, so 1 is second option
                                    sort_applied = True
                                    print("[+] Sorted by Recent (by index)")
                                except:
                                    pass
                        
                        if sort_applied:
                            time.sleep(3)  # Wait for results to update
                            break
                    except:
                        continue
                
                if not sort_applied:
                    print("[-] Could not apply sort by Recent")
            except Exception as e:
                print(f"[-] Error applying sort: {e}")
        
        print("[+] CVS Health filters applied, waiting for results to load...")
        time.sleep(5)  # Wait for filtered results to load
        
    except Exception as e:
        print(f"[-] Error applying CVS filters: {e}")
        traceback.print_exc()
