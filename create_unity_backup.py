#!/usr/bin/env python3
"""
Dell Unity Unisphere Configuration Backup Creator
Creates a new configuration backup and downloads it from Dell Unity systems
Supports Chrome, Edge, and Firefox browsers with WebDriver automation
"""

import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.service import Service as EdgeService
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
except ImportError:
    print("ERROR: Required packages not installed.")
    print("Install with: pip install selenium webdriver-manager")
    sys.exit(1)

class UnityBackup:
    def __init__(self, unity_url: str, username: str, password: str, browser: str = 'chrome'):
        # Ensure URL has correct format with https://
        if not unity_url.startswith('http'):
            unity_url = f'https://{unity_url}'
        self.unity_url = unity_url
        self.username = username
        self.password = password
        self.browser = browser.lower()
        self.driver = None
        self.wait = None
        self.logger = self.setup_logger()
        self.logger.info(f"Initialized with URL: {self.unity_url}")

    def setup_logger(self) -> logging.Logger:
        """Setup logger for the class"""
        logger = logging.getLogger('UnityBackup')
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        return logger

    def start_driver(self) -> None:
        """Start the web driver"""
        try:
            if self.browser == 'chrome':
                options = ChromeOptions()
                # REMOVE headless mode so browser is visible
                # options.add_argument("--headless")  # Run in headless mode
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--ignore-certificate-errors")
                options.add_argument("--allow-insecure-localhost")
                options.add_argument("--ignore-ssl-errors")
                options.accept_insecure_certs = True
                self.driver = webdriver.Chrome(
                    service=ChromeService(ChromeDriverManager().install()),
                    options=options
                )
            elif self.browser == 'edge':
                self.logger.info("Starting Edge WebDriver...")
                options = EdgeOptions()
                # Remove headless mode for debugging
                # options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--ignore-certificate-errors")
                options.add_argument("--allow-insecure-localhost")
                options.add_argument("--ignore-ssl-errors")
                options.use_chromium = True
                options.accept_insecure_certs = True
                
                # Explicitly set the Edge binary path
                edge_binary_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
                if not os.path.exists(edge_binary_path):
                    edge_binary_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
                    if not os.path.exists(edge_binary_path):
                        self.logger.error("❌ Edge browser executable not found!")
                        sys.exit(1)
                
                self.logger.info(f"Using Edge binary: {edge_binary_path}")
                options.binary_location = edge_binary_path
                
                # Get Edge driver path explicitly
                edge_driver_path = EdgeChromiumDriverManager().install()
                self.logger.info(f"Edge driver path: {edge_driver_path}")
                
                # Create service explicitly
                edge_service = EdgeService(edge_driver_path)
                self.logger.info(f"Edge service created with path: {edge_service.path}")
                
                self.driver = webdriver.Edge(
                    service=edge_service,
                    options=options
                )
                self.logger.info("Edge WebDriver initialized successfully")
            else:
                self.logger.error("Unsupported browser! Use 'chrome' or 'edge'.")
                sys.exit(1)
            self.wait = WebDriverWait(self.driver, 10)
            self.logger.info(f"🌐 {self.browser.capitalize()} WebDriver started")
        except WebDriverException as e:
            self.logger.error(f"❌ WebDriver initialization failed: {e}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"❌ Unexpected error starting WebDriver: {str(e)}")
            sys.exit(1)

    def login(self) -> bool:
        """Login to Unity Unisphere"""
        try:
            self.logger.info(f"🔐 Navigating to Unity Unisphere: {self.unity_url}")
            try:
                self.driver.get(self.unity_url)
                self.logger.info("URL navigation initiated")
            except Exception as e:
                self.logger.error(f"❌ Initial navigation error: {e}")
                self.logger.info("Attempting alternative navigation approach...")
                self.driver.execute_script(f"window.location.href = '{self.unity_url}';")
            time.sleep(5)
            self.logger.info(f"Current URL: {self.driver.current_url}")
            self.logger.info(f"Page title: {self.driver.title}")

            # Check for security acceptance page by unique message
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "This system is solely for the use of authorized users for official purposes." in body_text:
                    self.logger.info("Detected security acceptance page. Attempting to click Accept button...")
                    try:
                        accept_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="accept"]')))
                        accept_btn.click()
                        self.logger.info("Clicked Accept button on security page.")
                        time.sleep(3)
                    except Exception as e:
                        self.logger.error(f"Could not click Accept button: {e}")
                        return False
            except Exception as e:
                self.logger.debug(f"No security acceptance message detected: {e}")

            # Multiple selectors for username field
            username_selectors = [
                "//input[@name='username']",
                "//input[@id='username']",
                "//input[@name='user']",
                "//input[@id='user']",
                "//input[contains(@placeholder, 'username')]",
                "//input[contains(@placeholder, 'Username')]",
                "//input[contains(@class, 'username')]"
            ]
            
            username_field = None
            self.logger.info("Searching for username field...")
            for selector in username_selectors:
                try:
                    self.logger.debug(f"Trying selector: {selector}")
                    username_field = self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    self.logger.info(f"✅ Username field found with selector: {selector}")
                    break
                except TimeoutException:
                    self.logger.debug(f"Selector not found: {selector}")
                    continue
                    
            if not username_field:
                self.logger.error("❌ Username field not found")
                # Debug: Save page source and screenshot for troubleshooting
                debug_dir = Path.cwd() / 'unity_backups' / 'debug'
                debug_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                page_path = debug_dir / f'login_page_{ts}.html'
                shot_path = debug_dir / f'login_page_{ts}.png'
                
                try:
                    with open(page_path, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    self.logger.error(f"[DEBUG] Saved login page HTML to: {page_path}")
                    
                    # Log a small part of the page source for immediate debugging
                    page_snippet = self.driver.page_source[:500] + "..." if len(self.driver.page_source) > 500 else self.driver.page_source
                    self.logger.info(f"Page source snippet: {page_snippet}")
                except Exception as e:
                    self.logger.error(f"[DEBUG] Could not save login page HTML: {e}")
                    
                try:
                    self.driver.save_screenshot(str(shot_path))
                    self.logger.error(f"[DEBUG] Saved login page screenshot to: {shot_path}")
                except Exception as e:
                    self.logger.error(f"[DEBUG] Could not save login page screenshot: {e}")
                return False
            
            # Continue with login process
            self.logger.info("Entering username...")
            username_field.clear()
            username_field.send_keys(self.username)
            
            # Find password field
            try:
                password_field = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
                self.logger.info("✅ Password field found")
                password_field.clear()
                password_field.send_keys(self.password)
            except TimeoutException:
                self.logger.error("❌ Password field not found")
                return False
            
            # Find login button and click
            try:
                login_button_selectors = [
                    "//*[@id='submit']",  # Most specific selector first
                    "//button[contains(text(), 'Log')]", 
                    "//button[contains(text(), 'Sign')]",
                    "//input[@type='submit']",
                    "//button[@type='submit']"
                ]
                login_button = None
                for selector in login_button_selectors:
                    try:
                        login_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        self.logger.info(f"✅ Login button found with selector: {selector}")
                        break
                    except TimeoutException:
                        self.logger.debug(f"Login button selector not found: {selector}")
                        continue
                if login_button:
                    login_button.click()
                    self.logger.info("Login button clicked, waiting up to 20 seconds for dashboard...")
                    time.sleep(20)  # Increased wait time for dashboard to load
                    # Debug: Save page source and screenshot after login attempt
                    debug_dir = Path.cwd() / 'unity_backups' / 'debug'
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    page_path = debug_dir / f'post_login_page_{ts}.html'
                    shot_path = debug_dir / f'post_login_page_{ts}.png'
                    try:
                        with open(page_path, 'w', encoding='utf-8') as f:
                            f.write(self.driver.page_source)
                        self.logger.info(f"[DEBUG] Saved post-login page HTML to: {page_path}")
                    except Exception as e:
                        self.logger.error(f"[DEBUG] Could not save post-login page HTML: {e}")
                    try:
                        self.driver.save_screenshot(str(shot_path))
                        self.logger.info(f"[DEBUG] Saved post-login page screenshot to: {shot_path}")
                    except Exception as e:
                        self.logger.error(f"[DEBUG] Could not save post-login page screenshot: {e}")
                    # Always return True after waiting, let backup_workflow handle next steps
                    return True
                else:
                    self.logger.error("❌ Login button not found")
                    return False
            except Exception as e:
                self.logger.error(f"❌ Error clicking login button: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Login failed: {e}")
            return False

    def backup_workflow(self) -> bool:
        """Navigate UI to create and download configuration backup"""
        try:
            self.logger.info("Starting backup workflow...")
            # 1. Navigate directly to the Service Task page
            service_url = self.unity_url.split('/cas/login')[0] + '/index.html#lcn=SERVICE_TASK'
            self.logger.info(f"Navigating directly to Service Task page: {service_url}")
            try:
                self.driver.get(service_url)
                time.sleep(5)
            except Exception as e:
                self.logger.error(f"Failed to navigate to Service Task page: {e}")
                return False
            # 2. Click on Save Configuration
            try:
                self.logger.info("Clicking on Save Configuration...")
                save_config_elem = self.wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div[3]/div[2]/div/div[2]/div/div/div[2]/div/div/div/div/div[1]/div/div/div/div[1]/div/div/div/div/div[2]/div/div/div/div/div/div/div/div/div/div[1]/div/div[2]/div/div[2]/table[2]/tbody/tr/td/div')))
                save_config_elem.click()
                self.logger.info("Clicked Save Configuration.")
                time.sleep(2)
            except Exception as e:
                self.logger.error(f"Failed to click Save Configuration: {e}")
                return False
            # 3. Click Execute button
            try:
                self.logger.info("Clicking Execute button...")
                execute_xpaths = [
                    # User-provided full absolute XPath
                    "/html/body/div[1]/div[3]/div[2]/div/div[2]/div/div/div[2]/div/div/div/div/div[1]/div/div/div/div[1]/div/div/div/div/div[2]/div/div/div/div/div/div/div/div/div/div[3]/div/div/div/div/div[2]/div/div/a/span/span/span[2]",
                    # Previous id-based XPaths as fallback
                    "//span[@id='button-1512-btnEl']",
                    "//span[@id='button-1512-btnWrap']"
                ]
                execute_btn = None
                for xpath in execute_xpaths:
                    try:
                        execute_btn = WebDriverWait(self.driver, 30).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        self.logger.info(f"Found Execute button with XPath: {xpath}")
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", execute_btn)
                        time.sleep(1)
                        execute_btn.click()
                        self.logger.info("Clicked Execute button.")
                        time.sleep(2)
                        break
                    except Exception as e:
                        self.logger.warning(f"Could not click Execute button with XPath {xpath}: {e}")
                        continue
                if not execute_btn:
                    raise Exception("Could not find/click Execute button with any known XPath.")
            except Exception as e:
                self.logger.error(f"Failed to click Execute button: {e}")
                # Save screenshot and HTML for debugging
                debug_dir = Path.cwd() / 'unity_backups' / 'debug'
                debug_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                page_path = debug_dir / f'execute_button_fail_{ts}.html'
                shot_path = debug_dir / f'execute_button_fail_{ts}.png'
                try:
                    with open(page_path, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    self.logger.error(f"[DEBUG] Saved HTML to: {page_path}")
                except Exception as e2:
                    self.logger.error(f"[DEBUG] Could not save HTML: {e2}")
                try:
                    self.driver.save_screenshot(str(shot_path))
                    self.logger.error(f"[DEBUG] Saved screenshot to: {shot_path}")
                except Exception as e2:
                    self.logger.error(f"[DEBUG] Could not save screenshot: {e2}")
                return False
            # 4. Handle popup and click Create New
            try:
                self.logger.info("Waiting for Create New popup...")
                # Try by button id, text, and fallback to XPath
                create_new_selectors = [
                    (By.ID, "button-1339"),
                    (By.XPATH, '//a[span/span/span[contains(text(), "Create New")]]'),
                    (By.XPATH, '//span[contains(text(), "Create New")]'),
                    (By.XPATH, '//a[@id and .//span[contains(text(), "Create New")]]'),
                    (By.XPATH, '//a[contains(@class, "x-btn") and .//span[contains(text(), "Create New")]]'),
                ]
                create_new_btn = None
                for by, selector in create_new_selectors:
                    try:
                        create_new_btn = self.wait.until(EC.element_to_be_clickable((by, selector)))
                        self.logger.info(f"Found Create New button with {by}: {selector}")
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", create_new_btn)
                        time.sleep(1)
                        create_new_btn.click()
                        self.logger.info("Clicked Create New button.")
                        break
                    except Exception as e:
                        self.logger.warning(f"Could not click Create New button with {by} {selector}: {e}")
                        continue
                if not create_new_btn:
                    raise Exception("Could not find/click Create New button with any known selector.")
            except Exception as e:
                self.logger.error(f"Failed to click Create New button: {e}")
                # Save screenshot and HTML for debugging
                debug_dir = Path.cwd() / 'unity_backups' / 'debug'
                debug_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                page_path = debug_dir / f'create_new_button_fail_{ts}.html'
                shot_path = debug_dir / f'create_new_button_fail_{ts}.png'
                try:
                    with open(page_path, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    self.logger.error(f"[DEBUG] Saved HTML to: {page_path}")
                except Exception as e2:
                    self.logger.error(f"[DEBUG] Could not save HTML: {e2}")
                try:
                    self.driver.save_screenshot(str(shot_path))
                    self.logger.error(f"[DEBUG] Saved screenshot to: {shot_path}")
                except Exception as e2:
                    self.logger.error(f"[DEBUG] Could not save screenshot: {e2}")
                return False
            # 5. Wait for download to finish (wait for file in Downloads folder)
            self.logger.info("Waiting for backup file to download...")
            download_dir = str(Path.home() / 'Downloads')
            before_files = set(os.listdir(download_dir))
            timeout = 120  # seconds
            poll_interval = 2
            elapsed = 0
            backup_file = None
            backup_path = None
            while elapsed < timeout:
                after_files = set(os.listdir(download_dir))
                new_files = after_files - before_files
                for f in new_files:
                    if f.lower().endswith('.cfg') or 'backup' in f.lower() or f.lower().endswith('.html'):
                        backup_file = f
                        backup_path = os.path.join(download_dir, backup_file)
                        break
                if backup_file:
                    self.logger.info(f"Backup file downloaded: {backup_file}")
                    # --- Rename and move the backup file ---
                    try:
                        # Extract Unity IP from URL
                        import re
                        ip_match = re.search(r'https?://([\d.]+)', self.unity_url)
                        unity_ip = ip_match.group(1).replace('.', '_') if ip_match else 'unknown_ip'
                        # Get current date and time
                        date_str = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                        # Get file extension
                        ext = os.path.splitext(backup_file)[1]
                        # Compose new filename
                        new_name = f"unity_backup_{date_str}-IP-{unity_ip}{ext}"
                        target_dir = r"E:\\Unity\\Configuration backups"
                        os.makedirs(target_dir, exist_ok=True)
                        target_path = os.path.join(target_dir, new_name)
                        # Move and rename
                        import shutil
                        shutil.move(backup_path, target_path)
                        self.logger.info(f"Backup file moved to: {target_path}")
                    except Exception as move_err:
                        self.logger.error(f"Failed to move/rename backup file: {move_err}")
                        return False
                    return True
                time.sleep(poll_interval)
                elapsed += poll_interval
            self.logger.error("Backup file was not downloaded within timeout.")
            return False
        except Exception as e:
            self.logger.error(f"Backup workflow failed: {e}")
            return False

    def encryption_keystore_backup(self) -> bool:
        """Navigate to settings, Management > Encryption, and download the keystore backup file"""
        self.logger.info("Navigating to Settings...")
        # 1. Click the Settings button
        try:
            settings_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div[1]/div/div/a[2]/span/span/span[1]')))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", settings_btn)
            time.sleep(1)
            settings_btn.click()
            self.logger.info("Clicked Settings button.")
            time.sleep(2)
        except Exception as e:
            self.logger.error(f"Failed to click Settings button: {e}")
            return False        # 2. Click Management in popup        # 2. Click Management in popup
        try:
            # Attempt to close any open popups by sending ESCAPE
            try:
                body = self.driver.find_element(By.TAG_NAME, 'body')
                body.send_keys(Keys.ESCAPE)
                self.logger.info("Sent ESCAPE to body to close any open popups.")
                time.sleep(1)
            except Exception as esc_err:
                self.logger.warning(f"Could not send ESCAPE to body: {esc_err}")
            
            # Multiple selector strategies for Management element
            management_selectors = [
                # Direct XPath for Management text with exact class
                (By.XPATH, '//span[@class="x-tree-node-text " and text()="Management"]'),
                # More specific XPath based on the HTML structure
                (By.XPATH, '//div[contains(@id, "ext-element-")]/span[@class="x-tree-node-text " and text()="Management"]'),
                # CSS selector for the specific element ID from your HTML
                (By.CSS_SELECTOR, '#ext-element-288 > span.x-tree-node-text'),
                # Fallback to any clickable element containing Management text
                (By.XPATH, '//*[contains(text(), "Management") and contains(@class, "x-tree-node-text")]'),
                # Original XPath (updated with correct div number from your HTML)
                (By.XPATH, '/html/body/div[9]/div[2]/div[2]/div/div[2]/div/div[1]/table[3]/tbody/tr/td/div/span[2]'),
                # Generic fallback
                (By.XPATH, '//span[text()="Management"]')
            ]
            
            management_btn = None
            for by_type, selector in management_selectors:
                try:
                    self.logger.info(f"Trying Management selector: {by_type} - {selector}")
                    management_btn = self.wait.until(EC.element_to_be_clickable((by_type, selector)))
                    self.logger.info(f"Found Management element with {by_type}: {selector}")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", management_btn)
                    time.sleep(1)
                    management_btn.click()
                    self.logger.info(f"Successfully clicked Management using {by_type}.")
                    time.sleep(2)
                    break
                except Exception as e:
                    self.logger.warning(f"Management not clickable with {by_type} {selector}: {e}")
                    continue
            
            if not management_btn:
                # Final fallback: search all visible elements and click the one with Management text
                try:
                    self.logger.info("Trying final fallback: searching all visible elements for Management text")
                    candidates = self.driver.find_elements(By.XPATH, '//*[contains(text(), "Management")]')
                    found = False
                    for el in candidates:
                        try:
                            if el.is_displayed() and 'Management' in el.text:
                                self.logger.info(f"Found Management element: {el.tag_name}, text: '{el.text}', class: '{el.get_attribute('class')}'")
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", el)
                                time.sleep(1)
                                el.click()
                                self.logger.info("Successfully clicked Management using text search fallback.")
                                time.sleep(2)
                                found = True
                                break
                        except Exception as click_err:
                            self.logger.warning(f"Could not click Management candidate: {click_err}")
                            continue
                    if not found:
                        self.logger.error("Failed to find/click Management by any method.")
                        # Save debug information
                        debug_dir = Path.cwd() / 'unity_backups' / 'debug'
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                        page_path = debug_dir / f'management_not_found_{ts}.html'
                        shot_path = debug_dir / f'management_not_found_{ts}.png'
                        try:
                            with open(page_path, 'w', encoding='utf-8') as f:
                                f.write(self.driver.page_source)
                            self.logger.error(f"[DEBUG] Saved HTML to: {page_path}")
                        except Exception as e2:
                            self.logger.error(f"[DEBUG] Could not save HTML: {e2}")
                        try:
                            self.driver.save_screenshot(str(shot_path))
                            self.logger.error(f"[DEBUG] Saved screenshot to: {shot_path}")
                        except Exception as e2:
                            self.logger.error(f"[DEBUG] Could not save screenshot: {e2}")
                        return False
                except Exception as e_final:
                    self.logger.error(f"Final fallback failed: {e_final}")
                    return False
        except Exception as e:
            self.logger.error(f"Failed to click Management: {e}")
            return False        # 3. Click Encryption
        try:
            # Multiple selector strategies for Encryption element based on actual HTML structure
            encryption_selectors = [
                # Direct CSS selector for the specific element ID from your HTML
                (By.CSS_SELECTOR, '#ext-element-1024'),
                # Direct XPath for Encryption text with exact class
                (By.XPATH, '//span[@class="x-tree-node-text " and text()="Encryption"]'),
                # More specific XPath based on the HTML structure
                (By.XPATH, '//tr[@id="ext-element-1024"]//span[@class="x-tree-node-text " and text()="Encryption"]'),
                # Table-based selector
                (By.XPATH, '//table[@id and contains(@id, "treeview")]//span[@class="x-tree-node-text " and text()="Encryption"]'),
                # Fallback to any clickable element containing Encryption text
                (By.XPATH, '//*[contains(text(), "Encryption") and contains(@class, "x-tree-node-text")]'),
                # Original XPath (updated with correct div number from your HTML)
                (By.XPATH, '/html/body/div[9]/div[2]/div[2]/div/div[2]/div/div[1]/table[13]/tbody/tr/td/div/span'),
                # Generic fallback
                (By.XPATH, '//span[text()="Encryption"]')
            ]
            
            encryption_btn = None
            for by_type, selector in encryption_selectors:
                try:
                    self.logger.info(f"Trying Encryption selector: {by_type} - {selector}")
                    encryption_btn = self.wait.until(EC.element_to_be_clickable((by_type, selector)))
                    self.logger.info(f"Found Encryption element with {by_type}: {selector}")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", encryption_btn)
                    time.sleep(1)
                    encryption_btn.click()
                    self.logger.info(f"Successfully clicked Encryption using {by_type}.")
                    time.sleep(2)
                    break
                except Exception as e:
                    self.logger.warning(f"Encryption not clickable with {by_type} {selector}: {e}")
                    continue
            
            if not encryption_btn:
                # Final fallback: search all visible elements and click the one with Encryption text
                try:
                    self.logger.info("Trying final fallback: searching all visible elements for Encryption text")
                    candidates = self.driver.find_elements(By.XPATH, '//*[contains(text(), "Encryption")]')
                    found = False
                    for el in candidates:
                        try:
                            if el.is_displayed() and 'Encryption' in el.text:
                                self.logger.info(f"Found Encryption element: {el.tag_name}, text: '{el.text}', class: '{el.get_attribute('class')}'")
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", el)
                                time.sleep(1)
                                el.click()
                                self.logger.info("Successfully clicked Encryption using text search fallback.")
                                time.sleep(2)
                                found = True
                                break
                        except Exception as click_err:
                            self.logger.warning(f"Could not click Encryption candidate: {click_err}")
                            continue
                    if not found:
                        self.logger.error("Failed to find/click Encryption by any method.")
                        # Save debug information
                        debug_dir = Path.cwd() / 'unity_backups' / 'debug'
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                        page_path = debug_dir / f'encryption_not_found_{ts}.html'
                        shot_path = debug_dir / f'encryption_not_found_{ts}.png'
                        try:
                            with open(page_path, 'w', encoding='utf-8') as f:
                                f.write(self.driver.page_source)
                            self.logger.error(f"[DEBUG] Saved HTML to: {page_path}")
                        except Exception as e2:
                            self.logger.error(f"[DEBUG] Could not save HTML: {e2}")
                        try:
                            self.driver.save_screenshot(str(shot_path))
                            self.logger.error(f"[DEBUG] Saved screenshot to: {shot_path}")
                        except Exception as e2:
                            self.logger.error(f"[DEBUG] Could not save screenshot: {e2}")
                        return False
                except Exception as e_final:
                    self.logger.error(f"Final fallback failed: {e_final}")
                    return False
        except Exception as e:
            self.logger.error(f"Failed to click Encryption: {e}")
            return False        # 4. Click Backup Keystore File        # 4. Click Backup Keystore File
        try:
            # Multiple selector strategies for Backup Keystore File based on actual HTML structure
            backup_keystore_selectors = [
                # Direct CSS selector for the specific element ID from your HTML
                (By.CSS_SELECTOR, '#button-2297'),
                # XPath for the button with specific ID
                (By.XPATH, '//a[@id="button-2297"]'),
                # XPath targeting the inner span with the text
                (By.XPATH, '//span[@class="x-btn-inner x-btn-inner-secondary-small" and text()="Backup Keystore File"]'),
                # XPath targeting the button element containing the text
                (By.XPATH, '//a[@role="button"]//span[text()="Backup Keystore File"]'),
                # More generic XPath for any button-like element with the text
                (By.XPATH, '//*[contains(@class, "x-btn") and .//span[text()="Backup Keystore File"]]'),
                # Fallback to any clickable element containing the text
                (By.XPATH, '//*[contains(text(), "Backup Keystore File")]'),
                # Original XPath (updated with correct div number from your HTML)
                (By.XPATH, '/html/body/div[9]/div[2]/div[3]/div/div[1]/div[2]/div/div/a/span/span/span[2]'),
                # Generic text-based fallback
                (By.XPATH, '//a[contains(., "Backup Keystore File")]')
            ]
            
            backup_keystore_btn = None
            for by_type, selector in backup_keystore_selectors:
                try:
                    self.logger.info(f"Trying Backup Keystore File selector: {by_type} - {selector}")
                    backup_keystore_btn = self.wait.until(EC.element_to_be_clickable((by_type, selector)))
                    self.logger.info(f"Found Backup Keystore File element with {by_type}: {selector}")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", backup_keystore_btn)
                    time.sleep(1)
                    backup_keystore_btn.click()
                    self.logger.info(f"Successfully clicked Backup Keystore File using {by_type}.")
                    time.sleep(2)
                    break
                except Exception as e:
                    self.logger.warning(f"Backup Keystore File not clickable with {by_type} {selector}: {e}")
                    continue
            
            if not backup_keystore_btn:
                # Final fallback: search all visible elements and click the one with Backup Keystore File text
                try:
                    self.logger.info("Trying final fallback: searching all visible elements for Backup Keystore File text")
                    candidates = self.driver.find_elements(By.XPATH, '//*[contains(text(), "Backup Keystore File")]')
                    found = False
                    for el in candidates:
                        try:
                            if el.is_displayed() and 'Backup Keystore File' in el.text:
                                self.logger.info(f"Found Backup Keystore File element: {el.tag_name}, text: '{el.text}', class: '{el.get_attribute('class')}'")
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", el)
                                time.sleep(1)
                                el.click()
                                self.logger.info("Successfully clicked Backup Keystore File using text search fallback.")
                                time.sleep(2)
                                found = True
                                break
                        except Exception as click_err:
                            self.logger.warning(f"Could not click Backup Keystore File candidate: {click_err}")
                            continue
                    if not found:
                        self.logger.error("Failed to find/click Backup Keystore File by any method.")
                        # Save debug information
                        debug_dir = Path.cwd() / 'unity_backups' / 'debug'
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                        page_path = debug_dir / f'backup_keystore_not_found_{ts}.html'
                        shot_path = debug_dir / f'backup_keystore_not_found_{ts}.png'
                        try:
                            with open(page_path, 'w', encoding='utf-8') as f:
                                f.write(self.driver.page_source)
                            self.logger.error(f"[DEBUG] Saved HTML to: {page_path}")
                        except Exception as e2:
                            self.logger.error(f"[DEBUG] Could not save HTML: {e2}")
                        try:
                            self.driver.save_screenshot(str(shot_path))
                            self.logger.error(f"[DEBUG] Saved screenshot to: {shot_path}")
                        except Exception as e2:
                            self.logger.error(f"[DEBUG] Could not save screenshot: {e2}")
                        return False
                except Exception as e_final:
                    self.logger.error(f"Final fallback failed: {e_final}")
                    return False
        except Exception as e:
            self.logger.error(f"Failed to click Backup Keystore File: {e}")
            return False
        # 5. Wait for .lbb file download
        self.logger.info("Waiting for keystore backup file to download...")
        download_dir = str(Path.home() / 'Downloads')
        before_files = set(os.listdir(download_dir))
        timeout = 120  # seconds
        poll_interval = 2
        elapsed = 0
        backup_file = None
        backup_path = None
        while elapsed < timeout:
            after_files = set(os.listdir(download_dir))
            new_files = after_files - before_files
            for f in new_files:
                if f.lower().endswith('.lbb'):
                    backup_file = f
                    backup_path = os.path.join(download_dir, backup_file)
                    break
            if backup_file:
                self.logger.info(f"Keystore backup file downloaded: {backup_file}")
                # --- Rename and move the backup file ---
                try:
                    import re
                    ip_match = re.search(r'https?://([\d.]+)', self.unity_url)
                    # Fix inline if/else for unity_ip
                    if ip_match:
                        unity_ip = ip_match.group(1).replace('.', '_')
                    else:
                        unity_ip = 'unknown_ip'
                    # Get current date and time
                    date_str = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                    # Get file extension
                    ext = os.path.splitext(backup_file)[1]                    # Compose new filename - Unity-Encryption-Backup format
                    new_name = f"Unity-Encryption-Backup_{date_str}-IP-{unity_ip}{ext}"
                    target_dir = r"E:\\Unity\\Encryption Key Backups"
                    os.makedirs(target_dir, exist_ok=True)
                    target_path = os.path.join(target_dir, new_name)
                    # Move and rename
                    import shutil
                    shutil.move(backup_path, target_path)
                    self.logger.info(f"Keystore backup file moved to: {target_path}")
                except Exception as move_err:
                    self.logger.error(f"Failed to move/rename keystore backup file: {move_err}")
                    return False
                return True
            time.sleep(poll_interval)
            elapsed += poll_interval
        self.logger.error("Keystore backup file was not downloaded within timeout.")
        return False

    def close(self) -> None:
        """Close the web driver"""
        if self.driver:
            self.logger.info("Closing web driver...")
            try:
                self.driver.quit()
                self.logger.info("Web driver closed")
            except Exception as e:
                self.logger.error(f"Error closing web driver: {e}")
        else:
            self.logger.warning("Web driver not initialized, nothing to close")

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Dell Unity Unisphere Configuration Backup Creator")
    parser.add_argument('unity_url', type=str, help="Unity Unisphere URL (e.g., https://10.0.0.1)")
    parser.add_argument('username', type=str, help="Username for Unity Unisphere")
    password_group = parser.add_mutually_exclusive_group(required=True)
    password_group.add_argument('password', type=str, help="Password for Unity Unisphere", nargs='?')
    password_group.add_argument('--password-file', type=str, help="File containing the password")
    parser.add_argument('--browser', type=str, choices=['chrome', 'edge'], default='edge', help="Browser to use (default: edge)")
    return parser.parse_args()

def main() -> None:
    """Main function"""
    args = parse_arguments()
    
    # Get password from file if specified
    password = args.password
    if args.password_file:
        try:
            with open(args.password_file, 'r') as f:
                password = f.read().strip()
        except Exception as e:
            print(f"Error reading password file: {e}")
            sys.exit(1)
    
    backup_creator = UnityBackup(args.unity_url, args.username, password, args.browser)
    try:
        backup_creator.start_driver()
        if backup_creator.login():
            # Run configuration backup first
            if backup_creator.backup_workflow():
                print("Backup workflow completed!")
                # Go to Dashboard before encryption
                try:
                    dashboard_url = backup_creator.unity_url.split('/cas/login')[0] + '/index.html#lcn=DASHBOARD'
                    backup_creator.logger.info(f"Navigating to Dashboard: {dashboard_url}")
                    backup_creator.driver.get(dashboard_url)
                    time.sleep(5)
                except Exception as dash_err:
                    backup_creator.logger.warning(f"Failed to navigate to Dashboard: {dash_err}")
                # Then run encryption keystore backup
                if backup_creator.encryption_keystore_backup():
                    print("Encryption keystore backup completed!")
                else:
                    print("Encryption keystore backup failed!")
            else:
                print("Backup workflow failed!")
        else:
            backup_creator.logger.error("Login failed, cannot proceed with backup")
    except Exception as e:
        backup_creator.logger.error(f"Unexpected error: {e}")
    finally:
        backup_creator.close()

if __name__ == "__main__":
    main()
