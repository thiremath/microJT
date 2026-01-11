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


# ============================================================================
# Helper Functions
# ============================================================================

def wait_for_filters(driver, xpath_selector, max_wait=15, filter_name="filters"):
    """Generic function to wait for filter elements to be visible"""
    try:
        print(f"[+] Waiting for {filter_name} to load...")
        wait = WebDriverWait(driver, max_wait)
        wait.until(EC.presence_of_element_located((By.XPATH, xpath_selector)))
        print(f"[+] {filter_name.capitalize()} are visible")
        return True
    except Exception as e:
        print(f"[-] {filter_name.capitalize()} did not load within {max_wait} seconds: {e}")
        return False


def expand_collapsed_sections(driver, max_sections=5):
    """Expand collapsed filter sections if they exist"""
    try:
        expand_buttons = driver.find_elements(
            By.XPATH,
            "//button[contains(@aria-expanded, 'false')] | "
            "//*[@role='button' and contains(@aria-expanded, 'false')]"
        )
        for btn in expand_buttons[:max_sections]:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                time.sleep(0.5)
                btn.click()
                time.sleep(1)
            except Exception:
                continue
    except Exception:
        pass


def click_checkbox_element(driver, element, filter_name):
    """Click a checkbox element, handling both input and label types"""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5)
        
        if element.tag_name == 'input':
            if not element.is_selected():
                driver.execute_script("arguments[0].click();", element)
                print(f"[+] {filter_name} selected (input)")
                return True
            else:
                print(f"[+] {filter_name} already selected")
                return True
        elif element.tag_name == 'label':
            for_attr = element.get_attribute('for')
            if for_attr:
                try:
                    input_element = driver.find_element(By.ID, for_attr)
                    if not input_element.is_selected():
                        driver.execute_script("arguments[0].click();", input_element)
                        print(f"[+] {filter_name} selected (via label @for)")
                        return True
                    else:
                        print(f"[+] {filter_name} already selected")
                        return True
                except Exception:
                    driver.execute_script("arguments[0].click();", element)
                    print(f"[+] {filter_name} selected (label)")
                    return True
            else:
                driver.execute_script("arguments[0].click();", element)
                print(f"[+] {filter_name} selected (label)")
                return True
        else:
            driver.execute_script("arguments[0].click();", element)
            print(f"[+] {filter_name} selected (other)")
            return True
    except Exception as e:
        print(f"[DEBUG] Error clicking element: {e}")
        return False


def find_and_click_checkbox(driver, filter_text, selectors, filter_name, debug_info=None):
    """
    Generic function to find and click a checkbox using multiple selector strategies.
    
    Args:
        driver: Selenium WebDriver instance
        filter_text: Text to search for (e.g., "United States", "Entry Level")
        selectors: List of XPath selector strings
        filter_name: Name for logging (e.g., "Country", "Experience Level")
        debug_info: Optional dict with debug function and xpath for finding all checkboxes
    
    Returns:
        bool: True if checkbox was clicked, False otherwise
    """
    for i, selector in enumerate(selectors):
        try:
            # Special handling for @for attribute selector
            if selector.endswith('/@for'):
                labels = driver.find_elements(By.XPATH, selector.replace('/@for', ''))
                for label in labels:
                    try:
                        for_attr = label.get_attribute('for')
                        if for_attr:
                            input_element = driver.find_element(By.ID, for_attr)
                            if click_checkbox_element(driver, input_element, f"{filter_name} '{filter_text}'"):
                                time.sleep(2)
                                return True
                    except Exception:
                        continue
            else:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    for element in elements:
                        if click_checkbox_element(driver, element, f"{filter_name} '{filter_text}'"):
                            time.sleep(2)
                            return True
        except Exception as e:
            print(f"[DEBUG] Selector {i+1} error: {e}")
            continue
    
    # Debug output if checkbox not found
    print(f"[-] Could not find {filter_name.lower()}: {filter_text}")
    if debug_info:
        try:
            all_checkboxes = driver.find_elements(By.XPATH, debug_info['xpath'])
            print(f"[DEBUG] Found {len(all_checkboxes)} checkboxes total")
            print(f"[DEBUG] Available {filter_name.lower()}s:")
            for checkbox in all_checkboxes[:10]:
                try:
                    checkbox_id = checkbox.get_attribute('id')
                    aria_label = checkbox.get_attribute('aria-label')
                    data_attr = checkbox.get_attribute('data-ph-at-text')
                    
                    label_text = None
                    if checkbox_id:
                        try:
                            label = driver.find_element(By.XPATH, f"//label[@for='{checkbox_id}']")
                            label_text = label.text.strip()
                        except Exception:
                            pass
                    
                    debug_info['print_func'](checkbox_id, aria_label, data_attr, label_text)
                except Exception:
                    pass
        except Exception as e:
            print(f"[DEBUG] Error finding {filter_name.lower()}s: {e}")
    
    return False


def apply_sort_filter(driver, sort_value, selectors, button_selectors=None):
    """
    Generic function to apply sorting filters.
    
    Args:
        driver: Selenium WebDriver instance
        sort_value: Value to sort by (e.g., "Most Recent", "Recent")
        selectors: List of XPath selectors for select elements
        button_selectors: Optional list of XPath selectors for button/link sort elements
    
    Returns:
        bool: True if sort was applied, False otherwise
    """
    # Try select dropdown first
    for selector in selectors:
        try:
            sort_elements = driver.find_elements(By.XPATH, selector)
            if sort_elements:
                for sort_element in sort_elements:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sort_element)
                        time.sleep(0.5)
                        
                        if sort_element.tag_name == 'select':
                            select = Select(sort_element)
                            # Try multiple methods to select
                            for method, value in [
                                ('visible_text', sort_value),
                                ('value', sort_value.lower().replace(' ', '_')),
                                ('value', sort_value),
                                ('index', 1)
                            ]:
                                try:
                                    if method == 'visible_text':
                                        select.select_by_visible_text(value)
                                    elif method == 'value':
                                        select.select_by_value(value)
                                    elif method == 'index':
                                        select.select_by_index(value)
                                    print(f"[+] Sorted by {sort_value} ({method})")
                                    time.sleep(2)
                                    return True
                                except Exception:
                                    continue
                    except Exception as e:
                        print(f"[DEBUG] Error with sort element: {e}")
                        continue
        except Exception as e:
            print(f"[DEBUG] Sort selector error: {e}")
            continue
    
    # Try button/link approach if provided
    if button_selectors:
        for selector in button_selectors:
            try:
                sort_elements = driver.find_elements(By.XPATH, selector)
                for sort_element in sort_elements:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sort_element)
                        time.sleep(0.5)
                        
                        if sort_element.tag_name in ['button', 'a', 'span', 'div']:
                            driver.execute_script("arguments[0].click();", sort_element)
                            time.sleep(1)
                            try:
                                most_recent = driver.find_element(
                                    By.XPATH,
                                    f"//*[contains(text(), '{sort_value}')]"
                                )
                                driver.execute_script("arguments[0].click();", most_recent)
                                print(f"[+] Sorted by {sort_value} (button/link)")
                                time.sleep(2)
                                return True
                            except Exception:
                                pass
                    except Exception:
                        continue
            except Exception:
                continue
    
    print(f"[-] Could not apply sort by {sort_value}")
    return False


# ============================================================================
# Cisco-Specific Functions
# ============================================================================

def wait_for_cisco_filters(driver, max_wait=15):
    """Wait for Cisco Careers filter elements to be visible"""
    return wait_for_filters(
        driver,
        "//input[@type='checkbox']",
        max_wait,
        "Cisco filters"
    )


def apply_cisco_filters(driver, filters_config):
    """Apply filters for Cisco Careers job search"""
    try:
        print("[+] Applying Cisco filters...")
        time.sleep(3)  # Initial wait for page to load
        
        if not wait_for_cisco_filters(driver):
            print("[-] Warning: Filters may not be fully loaded")
        
        expand_collapsed_sections(driver)
        time.sleep(1)
        
        # Apply Experience Level filters
        if filters_config.get('experience_levels'):
            experience_levels = filters_config['experience_levels']
            print(f"[+] Selecting experience levels: {experience_levels}")
            
            selectors = [
                f"//label[normalize-space(text())='{{text}}']",
                f"//label[contains(text(), '{{text}}')]",
                f"//label[contains(text(), '{{text}}') and @for]",
                f"//label[contains(text(), '{{text}}')]/preceding-sibling::input[@type='checkbox']",
                f"//label[contains(text(), '{{text}}')]/following-sibling::input[@type='checkbox']",
                f"//*[normalize-space(text())='{{text}}']/ancestor::*[1]//input[@type='checkbox']",
                f"//*[contains(text(), '{{text}}')]/ancestor::li//input[@type='checkbox']",
                f"//*[contains(text(), '{{text}}')]/ancestor::div//input[@type='checkbox']",
                f"//input[@type='checkbox' and contains(@aria-label, '{{text}}')]",
            ]
            
            for level in experience_levels:
                level_selectors = [s.format(text=level) for s in selectors]
                find_and_click_checkbox(
                    driver,
                    level,
                    level_selectors,
                    "Experience level",
                    debug_info={
                        'xpath': "//input[@type='checkbox']",
                        'print_func': lambda id, aria, data, label: print(
                            f"[DEBUG]   - id={id}, aria-label={aria}, label text={label}"
                        )
                    }
                )
        
        # Apply Country filter
        if filters_config.get('country'):
            country_text = filters_config['country']
            print(f"[+] Selecting country: {country_text}")
            time.sleep(1)
            
            selectors = [
                f"//label[normalize-space(text())='{{text}}']",
                f"//label[contains(text(), '{{text}}')]",
                f"//label[contains(text(), '{{text}}') and @for]",
                f"//label[contains(text(), '{{text}}')]/preceding-sibling::input[@type='checkbox']",
                f"//label[contains(text(), '{{text}}')]/following-sibling::input[@type='checkbox']",
                f"//*[normalize-space(text())='{{text}}']/ancestor::*[1]//input[@type='checkbox']",
                f"//*[contains(text(), '{{text}}')]/ancestor::li//input[@type='checkbox']",
                f"//*[contains(text(), '{{text}}')]/ancestor::div//input[@type='checkbox']",
                f"//input[@type='checkbox' and contains(@aria-label, '{{text}}')]",
            ]
            
            country_selectors = [s.format(text=country_text) for s in selectors]
            find_and_click_checkbox(
                driver,
                country_text,
                country_selectors,
                "Country",
                debug_info={
                    'xpath': "//input[@type='checkbox']",
                    'print_func': lambda id, aria, data, label: print(
                        f"[DEBUG]   - id={id}, aria-label={aria}, label text={label}"
                    )
                }
            )
        
        # Apply Sort by Most Recent
        if filters_config.get('sort_by') == 'Most Recent':
            print("[+] Sorting by Most Recent...")
            time.sleep(1)
            
            select_selectors = [
                "//select[contains(@class, 'sort')]",
                "//select[contains(@id, 'sort')]",
                "//select[contains(@name, 'sort')]",
                "//select[@aria-label*='sort' or @aria-label*='Sort']",
                "//*[contains(text(), 'Sort by')]/following-sibling::select",
                "//*[contains(text(), 'Sort by')]/parent::*/select",
            ]
            
            button_selectors = [
                "//*[contains(text(), 'Sort by')]",
                "//*[contains(text(), 'Most Recent')]",
                "//button[contains(@aria-label, 'sort') or contains(@aria-label, 'Sort')]",
            ]
            
            apply_sort_filter(driver, "Most Recent", select_selectors, button_selectors)
        
        print("[+] Cisco filters applied, waiting for results to load...")
        time.sleep(3)
        
    except Exception as e:
        print(f"[-] Error applying Cisco filters: {e}")
        traceback.print_exc()


# ============================================================================
# CVS-Specific Functions
# ============================================================================

def wait_for_cvs_filters(driver, max_wait=15):
    """Wait for CVS Health filter elements to be visible"""
    return wait_for_filters(
        driver,
        "//input[@type='checkbox' and (contains(@id, 'category_phs_') or contains(@id, 'subCategory_phs_'))]",
        max_wait,
        "CVS filters"
    )


def apply_cvs_filters(driver, filters_config):
    """Apply filters for CVS Health job search"""
    try:
        print("[+] Applying CVS Health filters...")
        time.sleep(3)  # Initial wait for page to load
        
        if not wait_for_cvs_filters(driver):
            print("[-] Warning: Filters may not be fully loaded")
        
        expand_collapsed_sections(driver)
        time.sleep(1)
        
        # Apply Category filter
        if filters_config.get('category'):
            category_text = filters_config['category']
            print(f"[+] Selecting category: {category_text}")
            time.sleep(1)
            
            selectors = [
                f"//input[@data-ph-at-text='{{text}}' and @type='checkbox']",
                f"//input[@type='checkbox' and contains(@aria-label, '{{text}}')]",
                f"//input[@type='checkbox' and contains(@id, 'category_phs_{{text}}')]",
                f"//label[normalize-space(text())='{{text}}' and @for]/@for",
                f"//label[contains(text(), '{{text}}') and @for]",
                f"//label[contains(text(), '{{text}}')]/preceding-sibling::input[@type='checkbox']",
                f"//label[contains(text(), '{{text}}')]/following-sibling::input[@type='checkbox']",
                f"//*[contains(text(), '{{text}}')]/ancestor::*[1]//input[@type='checkbox']",
                f"//*[normalize-space(text())='{{text}}']/ancestor::li//input[@type='checkbox']",
                f"//*[normalize-space(text())='{{text}}']/ancestor::div//input[@type='checkbox']",
            ]
            
            category_selectors = [s.format(text=category_text) for s in selectors]
            
            def debug_print(id, aria, data, label):
                print(f"[DEBUG]   - id={id}")
                print(f"            aria-label={aria}")
                print(f"            data-ph-at-text={data}")
                print(f"            label text={label}")
            
            find_and_click_checkbox(
                driver,
                category_text,
                category_selectors,
                "Category",
                debug_info={
                    'xpath': "//input[@type='checkbox' and contains(@id, 'category_phs_')]",
                    'print_func': debug_print
                }
            )
        
        # Apply Sub Category filter
        if filters_config.get('sub_category'):
            sub_category_text = filters_config['sub_category']
            print(f"[+] Selecting sub-category: {sub_category_text}")
            time.sleep(1)
            
            selectors = [
                f"//input[@data-ph-at-text='{{text}}' and @type='checkbox']",
                f"//input[@type='checkbox' and contains(@aria-label, '{{text}}')]",
                f"//input[@type='checkbox' and contains(@id, 'subCategory_phs_{{text}}')]",
                f"//label[contains(text(), '{{text}}') and @for]",
                f"//label[contains(text(), '{{text}}')]/preceding-sibling::input[@type='checkbox']",
                f"//label[contains(text(), '{{text}}')]/following-sibling::input[@type='checkbox']",
                f"//*[contains(text(), '{{text}}')]/ancestor::li//input[@type='checkbox']",
            ]
            
            sub_category_selectors = [s.format(text=sub_category_text) for s in selectors]
            find_and_click_checkbox(
                driver,
                sub_category_text,
                sub_category_selectors,
                "Sub-category",
                debug_info={
                    'xpath': "//input[@type='checkbox' and contains(@id, 'subCategory_phs_')]",
                    'print_func': lambda id, aria, data, label: None
                }
            )
        
        # Apply Sort by Recent
        if filters_config.get('sort_by') == 'Recent':
            print("[+] Sorting by Recent...")
            time.sleep(1)
            
            select_selectors = [
                "//select[@id='sortselect']",
                "//select[@data-ph-at-id='sortby-drop-down']",
                "//select[contains(@aria-label, 'Sort by')]",
            ]
            
            # CVS uses "Most recent" as the value, try that first, then "Recent"
            if not apply_sort_filter(driver, "Most recent", select_selectors):
                apply_sort_filter(driver, "Recent", select_selectors)
        
        print("[+] CVS Health filters applied, waiting for results to load...")
        time.sleep(3)
        
    except Exception as e:
        print(f"[-] Error applying CVS filters: {e}")
        traceback.print_exc()


# ============================================================================
# Adobe-Specific Functions
# ============================================================================

def wait_for_adobe_filters(driver, max_wait=15):
    """Wait for Adobe Careers filter elements to be visible"""
    return wait_for_filters(
        driver,
        "//input[@type='checkbox']",
        max_wait,
        "Adobe filters"
    )


def apply_adobe_filters(driver, filters_config):
    """Apply filters for Adobe Careers job search"""
    try:
        print("[+] Applying Adobe filters...")
        time.sleep(3)  # Initial wait for page to load
        
        if not wait_for_adobe_filters(driver):
            print("[-] Warning: Filters may not be fully loaded")
        
        expand_collapsed_sections(driver)
        time.sleep(1)
        
        # Apply Experience Level filter
        if filters_config.get('experience_level'):
            experience_level = filters_config['experience_level']
            print(f"[+] Selecting experience level: {experience_level}")
            time.sleep(1)
            
            selectors = [
                f"//label[normalize-space(text())='{{text}}']",
                f"//label[contains(text(), '{{text}}')]",
                f"//label[contains(text(), '{{text}}') and @for]",
                f"//label[contains(text(), '{{text}}')]/preceding-sibling::input[@type='checkbox']",
                f"//label[contains(text(), '{{text}}')]/following-sibling::input[@type='checkbox']",
                f"//*[normalize-space(text())='{{text}}']/ancestor::*[1]//input[@type='checkbox']",
                f"//*[contains(text(), '{{text}}')]/ancestor::li//input[@type='checkbox']",
                f"//*[contains(text(), '{{text}}')]/ancestor::div//input[@type='checkbox']",
                f"//input[@type='checkbox' and contains(@aria-label, '{{text}}')]",
            ]
            
            experience_selectors = [s.format(text=experience_level) for s in selectors]
            find_and_click_checkbox(
                driver,
                experience_level,
                experience_selectors,
                "Experience level",
                debug_info={
                    'xpath': "//input[@type='checkbox']",
                    'print_func': lambda id, aria, data, label: print(
                        f"[DEBUG]   - id={id}, aria-label={aria}, label text={label}"
                    )
                }
            )
        
        # Apply Teams filter
        if filters_config.get('teams'):
            teams = filters_config['teams']
            if isinstance(teams, str):
                teams = [teams]
            print(f"[+] Selecting teams: {teams}")
            time.sleep(1)
            
            selectors = [
                f"//label[normalize-space(text())='{{text}}']",
                f"//label[contains(text(), '{{text}}')]",
                f"//label[contains(text(), '{{text}}') and @for]",
                f"//label[contains(text(), '{{text}}')]/preceding-sibling::input[@type='checkbox']",
                f"//label[contains(text(), '{{text}}')]/following-sibling::input[@type='checkbox']",
                f"//*[normalize-space(text())='{{text}}']/ancestor::*[1]//input[@type='checkbox']",
                f"//*[contains(text(), '{{text}}')]/ancestor::li//input[@type='checkbox']",
                f"//*[contains(text(), '{{text}}')]/ancestor::div//input[@type='checkbox']",
                f"//input[@type='checkbox' and contains(@aria-label, '{{text}}')]",
            ]
            
            for team in teams:
                team_selectors = [s.format(text=team) for s in selectors]
                find_and_click_checkbox(
                    driver,
                    team,
                    team_selectors,
                    "Team",
                    debug_info={
                        'xpath': "//input[@type='checkbox']",
                        'print_func': lambda id, aria, data, label: print(
                            f"[DEBUG]   - id={id}, aria-label={aria}, label text={label}"
                        )
                    }
                )
        
        # Apply Sort by Most Recent
        if filters_config.get('sort_by') == 'Most recent':
            print("[+] Sorting by Most recent...")
            time.sleep(1)
            
            select_selectors = [
                "//select[contains(@class, 'sort')]",
                "//select[contains(@id, 'sort')]",
                "//select[contains(@name, 'sort')]",
                "//select[@aria-label*='sort' or @aria-label*='Sort']",
                "//*[contains(text(), 'Sort by')]/following-sibling::select",
                "//*[contains(text(), 'Sort by')]/parent::*/select",
            ]
            
            button_selectors = [
                "//*[contains(text(), 'Sort by')]",
                "//*[contains(text(), 'Most recent')]",
                "//button[contains(@aria-label, 'sort') or contains(@aria-label, 'Sort')]",
            ]
            
            apply_sort_filter(driver, "Most recent", select_selectors, button_selectors)
        
        print("[+] Adobe filters applied, waiting for results to load...")
        time.sleep(3)
        
    except Exception as e:
        print(f"[-] Error applying Adobe filters: {e}")
        traceback.print_exc()
