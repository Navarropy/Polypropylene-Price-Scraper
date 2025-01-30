from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime, timedelta
import csv
import time
import json

# Initialize WebDriver
driver = webdriver.Chrome()
driver.maximize_window()
driver.get("https://tradingeconomics.com/commodity/polypropylene")

# Set date range (2014-01-01 to Today -3 days)
date_picker = WebDriverWait(driver, 20).until(
    EC.element_to_be_clickable((By.XPATH, '//*[@id="iChartHeader-datePicker-button"]'))
)
date_picker.click()

start_input = WebDriverWait(driver, 20).until(
    EC.presence_of_element_located((By.XPATH, '//*[@id="start"]'))
)
start_input.clear()
start_input.send_keys("2014-01-01")

end_input = driver.find_element(By.XPATH, '//*[@id="end"]')
end_input.clear()
end_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
end_input.send_keys(end_date)

ok_button = driver.find_element(By.XPATH, '//*[@id="btnOK"]')
ok_button.click()

# Wait for chart to load
time.sleep(5)

# Locate the chart container
chart = WebDriverWait(driver, 20).until(
    EC.presence_of_element_located((By.XPATH, '//*[@dir="ltr"]'))
)

# Scroll chart into view
driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", chart)
time.sleep(1)

# Get chart dimensions relative to the page
chart_rect = driver.execute_script("return arguments[0].getBoundingClientRect();", chart)
start_x = chart_rect['left'] + 10  # Start 10px inside chart's left edge
end_x = chart_rect['right'] - 10    # End 10px before chart's right edge
y_position = chart_rect['top'] + (chart_rect['height'] / 2)  # Vertical center

# Configure scanning parameters
step = 1  # Step size in pixels
max_step = 50  # Maximum jump when no data found
current_step = step
data = []
previous_date = None

# Simulate mouse movement
actions = ActionChains(driver)
current_x = start_x

while current_x <= end_x:
    try:
        # Move mouse to current position
        actions.move_by_offset(current_x - driver.execute_script("return window.pageXOffset;"), 
                             y_position - driver.execute_script("return window.pageYOffset;")).pause(0.1).perform()
        
        # Extract tooltip data
        date_element = WebDriverWait(driver, 0.5).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@class="yLabelDrag"]'))
        )
        value_element = WebDriverWait(driver, 0.5).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="iChart-bodyLabels-cnt"]/div[2]/span[2]/span[1]'))
        )
        
        current_date = date_element.text.strip()
        current_value = value_element.text.strip()

        if current_date != previous_date:
            data.append((current_date, current_value))
            previous_date = current_date
            current_step = step  # Reset step size
            print(f"✅ Captured: {current_date} - {current_value}")
        else:
            current_step = min(current_step + 2, max_step)  # Accelerate

    except:
        current_step = min(current_step + 5, max_step)  # Faster scan in empty areas

    finally:
        current_x += current_step
        actions.reset_actions()  # Clear previous move actions

    # Progress tracking
    if current_x % 100 == 0:
        print(f"Progress: {((current_x - start_x)/(end_x - start_x))*100:.1f}%")

# Save data to CSV
print(f"\nTotal records captured: {len(data)}")
with open('polypropylene_prices.json', 'w') as file:
    # Convert tuple data to dictionary format for JSON
    json_data = [{"date": date, "value": value} for date, value in data]
    json.dump(json_data, file, indent=2)

driver.quit()