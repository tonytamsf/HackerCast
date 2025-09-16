#!/usr/bin/env python

# NOTE: This task is currently blocked. The Selenium script is unable to reliably
# interact with the NotebookLM UI to create a new notebook. Further investigation
# is required, preferably with the ability to inspect the UI directly.

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def add_source_to_notebooklm(text_content):
    """Automates adding a text source to NotebookLM using Selenium."""
    chrome_options = Options()
    # Uncomment the following line to run in headless mode
    # chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get("https://notebooklm.google.com/")

        # Wait for the user to log in manually
        print("Please log in to your Google account in the browser window...")
        time.sleep(15)  # Adjust this time as needed

        # Wait for the "New Notebook" button to be clickable and then click it
        try:
            wait = WebDriverWait(driver, 10)
            # Try a more generic selector
            new_notebook_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='New notebook']"))
            )
            new_notebook_button.click()
            print("Successfully clicked the 'New Notebook' button.")
        except Exception as e:
            print(f"Could not find or click the 'New Notebook' button: {e}")

        # Further steps to add a source will be implemented in subsequent tasks.
        time.sleep(5) # Keep the browser open for a bit to observe

    finally:
        driver.quit()

if __name__ == "__main__":
    sample_text = "This is some sample text to be added as a source in NotebookLM."
    add_source_to_notebooklm(sample_text)