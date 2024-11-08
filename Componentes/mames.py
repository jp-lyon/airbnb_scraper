from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set up the WebDriver (you can use Chrome, Firefox, etc.)
driver = webdriver.Chrome()

# Airbnb listing URL (you can replace this with any valid listing URL)
listing_url = input("Enter the Airbnb listing URL: ")

# Open the listing page
driver.get(listing_url)

# Wait for the page elements to load
wait = WebDriverWait(driver, 10)

try:
    # Extract the title
    title = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'h1'))).text

    # Extract the price per night
    price = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, 'span[class*="Text__"]')
    )).text

    # Extract the description
    description = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, 'div[data-section-id="DESCRIPTION_DEFAULT"]')
    )).text

    # Print the extracted data
    print("Title:", title)
    print("Price:", price)
    print("Description:", description)

except Exception as e:
    print("An error occurred while extracting data:", e)

finally:
    # Close the WebDriver
    driver.quit()
