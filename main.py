from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, WebDriverException
import pandas as pd
import time
import random
from dotenv import load_dotenv
import os

# URLs
login_url = 'https://atlas.datalogix.ai/auth/login'
target_url = 'https://atlas.datalogix.ai/available-vms'

# Login credentials
load_dotenv()
username = os.getenv('username')
password = os.getenv('password')

# Setup Chrome options
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--proxy-server='direct://'")
chrome_options.add_argument("--proxy-bypass-list=*")
chrome_options.add_argument("--start-maximized")
# chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# Setup the Chrome driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def wait_for_element(by, value, timeout=300):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))

def wait_for_elements(by, value, timeout=300):
    return WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located((by, value)))

def login(max_retries=3):
    for attempt in range(max_retries):
        try:
            print(f'attempt: {attempt}')
            driver.get(login_url)
            username_field = wait_for_element(By.ID, "email")
            username_field.send_keys(username)
            password_field = wait_for_element(By.ID, "password")
            password_field.send_keys(password)
            login_button = wait_for_element(By.XPATH, '//*[@id="root"]/div/div[2]/div[2]/div/div/div/form/button')#"//button[contains(text(), 'Login')]")
            login_button.click()
            time.sleep(random.uniform(3, 5))
            return True
        except (TimeoutException, WebDriverException) as e:
            print(f"Login attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                print("Max login attempts reached. Exiting.")
                return False
            time.sleep(random.uniform(2, 5))

def scrape_data(max_retries=3):
    for attempt in range(max_retries):
        try:
            driver.get(target_url)
            time.sleep(random.uniform(5, 10))
            print('searching for the containers ....')
            gpu_containers = wait_for_elements(By.CLASS_NAME, "single-item")
            print('gpu_containers: ', gpu_containers)
            
            gpu_names, gpu_prices, download_speeds, cpu_details, ram_details, storage_details = [], [], [], [], [], []
            
            for container in gpu_containers:
                print(container)
                price_section = container.find_element(By.CLASS_NAME, "price-section")
                
                gpu_prices.append(price_section.text.strip().split('/')[0].replace('$', '').strip())
                print(f'gpu_prices: {gpu_prices}')

                speed_section = container.find_element(By.CLASS_NAME, 'flex.flex-col.items-center')

                # Extract the text from the span with class 'poppins-medium'
                download_speed_text = speed_section.find_element(By.CLASS_NAME, 'poppins-medium').text
                
                # Clean the text to get just the number
                download_speed = download_speed_text.split()[0]  # This will extract '10000'
                download_speeds.append(download_speed)
                
                print(f'download_speeds: {download_speeds}')
                
                cpu_ram_section = container.find_element(By.CSS_SELECTOR, "div[style='width: 115px;']")
                cpu_ram_text = cpu_ram_section.text.strip().split('\n')
                cpu_details.append(cpu_ram_text[0])
                ram_details.append(cpu_ram_text[1])
                
                print(f'cpu_details: {cpu_details}')
                print(f'ram_details: {ram_details}')
                
                gpu_storage_section = container.find_element(By.CSS_SELECTOR, "div[style='width: 125px;']")
                gpu_storage_text = gpu_storage_section.text.strip().split('\n')
                gpu_names.append(gpu_storage_text[0])
                storage_details.append(gpu_storage_text[1])
                print(f'gpu_names: {gpu_names}')
                print(f'storage_details: {storage_details}')
                
            return pd.DataFrame({
                'GPU Name': gpu_names,
                'Price (per hour)': gpu_prices,
                'Download Speed (Mbps)': download_speeds,
                'CPU Details': cpu_details,
                'RAM': ram_details,
                'Storage': storage_details
            })
        except (TimeoutException, WebDriverException) as e:
            print(f"Scraping attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                print("Max scraping attempts reached. Exiting.")
                return None
            time.sleep(random.uniform(5, 10))

try:
    if login():
        df = scrape_data()
        if df is not None and not df.empty:
            df.to_csv('gpu_pricing_data.csv', index=False)
            print("Data saved to gpu_pricing_data.csv")
        else:
            print("No data was scraped.")
    else:
        print("Login failed. Unable to scrape data.")
except Exception as e:
    print(f"An unexpected error occurred: {str(e)}")
finally:
    driver.quit()