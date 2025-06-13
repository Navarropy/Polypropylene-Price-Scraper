#!/usr/bin/env python3
# diagram.py: This script uses Selenium to automate a browser, simulate hover events on a webpage's chart,
# extract tooltip data, and then save the scraped data as a CSV file in the "data/" directory.

from selenium import webdriver  # Web automation: controls a web browser.
from selenium.webdriver.common.by import By  # For locating elements using different strategies (e.g., CSS selectors).
from selenium.webdriver.support.ui import WebDriverWait  # Allows waiting for certain conditions to be met.
from selenium.webdriver.support import expected_conditions as EC  # Conditions used for waiting (e.g., element visibility).
import time  # Provides sleep and timing functions.
import csv  # To write the scraped data to a CSV file.
import os  # For operating system related tasks (e.g., creating directories).
import re  # For regular expressions, used to sanitize filenames.

# ---------------------------------------------------------------------
# Global Variables for the Wavelet Diagram (Not used in this script, but
# included from the original file context)
# ---------------------------------------------------------------------
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

wavelet_name = 'cmor1.5-1.0'   # Wavelet type (complex Morlet wavelet with parameters).
scales = np.arange(1, 128)     # Range of scales used in the Continuous Wavelet Transform (CWT).
sampling_period = 1            # Sampling period (e.g., 1 for daily data).

# ---------------------------------------------------------------------
# Function: sanitize_filename
# ---------------------------------------------------------------------
def sanitize_filename(file_name):
    """
    Replace any forbidden filename characters (\, /, :, *, ?, ", <, >, |)
    with underscores to ensure the filename is valid on Windows.
    
    Parameters:
    file_name (str): The original filename.
    
    Returns:
    str: A sanitized version of the filename.
    """
    return re.sub(r'[\\/:*?"<>|]+', '_', str(file_name))

# ---------------------------------------------------------------------
# Main Script Begins
# ---------------------------------------------------------------------

# Initialize the Chrome WebDriver and maximize the browser window.
driver = webdriver.Chrome()
driver.maximize_window()

def run():
    try:
        # -----------------------------------------------------------------
        # Load the target webpage (PVC Price Index page).
        # -----------------------------------------------------------------
        driver.get("https://businessanalytiq.com/procurementanalytics/index/pvc-price-index/")

        # -----------------------------------------------------------------
        # Wait until the iframe that contains the Data Studio content appears.
        # The iframe is identified by a CSS selector that looks for 'datastudio' in its 'src' attribute.
        # -----------------------------------------------------------------
        data_iframe = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='datastudio']"))
        )
        
        # -----------------------------------------------------------------
        # Get the position and size of the iframe before switching into it.
        # We execute JavaScript to obtain its bounding rectangle.
        # -----------------------------------------------------------------
        iframe_position = driver.execute_script("""
            const rect = arguments[0].getBoundingClientRect();
            return {
                left: rect.left + window.pageXOffset,
                top: rect.top + window.pageYOffset,
                width: rect.width,
                height: rect.height
            };
        """, data_iframe)

        # -----------------------------------------------------------------
        # Switch context to the iframe so that we can interact with its elements.
        # -----------------------------------------------------------------
        driver.switch_to.frame(data_iframe)
        
        # -----------------------------------------------------------------
        # Insert a visual indicator (a red dot) inside the iframe.
        # This indicator (with id 'hoverDot') will be used to show where hover events are being simulated.
        # -----------------------------------------------------------------
        driver.execute_script("""
            const hoverIndicator = document.createElement('div');
            hoverIndicator.id = 'hoverDot';
            hoverIndicator.style = 'position: fixed; width: 8px; height: 8px; background: red;'
                                + 'border-radius: 50%; z-index: 99999; display: none;'
                                + 'box-shadow: 0 0 5px red; pointer-events: none;';
            document.body.appendChild(hoverIndicator);
        """)

        # -----------------------------------------------------------------
        # Wait for the chart element to be visible inside the iframe.
        # The chart is identified by the CSS selector "div.ng2-canvas-container.grid".
        # -----------------------------------------------------------------
        chart_container = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.ng2-canvas-container.grid"))
        )
        # Get the dimensions of the chart container.
        chart_rectangle = driver.execute_script("return arguments[0].getBoundingClientRect();", chart_container)

        # -----------------------------------------------------------------
        # Configure scanning parameters:
        # - SCAN_START_X: Starting x-coordinate (50 pixels from the left edge).
        # - SCAN_END_X: Ending x-coordinate (50 pixels from the right edge of the chart).
        # - SCAN_Y: Fixed y-coordinate set to 30% of the chart's height from the top.
        # -----------------------------------------------------------------
        SCAN_START_X = 50
        SCAN_END_X = chart_rectangle['width'] - 50
        SCAN_Y = chart_rectangle['height'] * 0.3  # 30% down from the top of the chart.
        current_scan_x = SCAN_START_X  # Initialize scanning position.
        scraped_data = []             # List to hold data records.
        data_headers = set()          # Set to hold unique header names extracted from tooltips.

        # -----------------------------------------------------------------
        # Define a JavaScript snippet that simulates a hover event.
        # The script:
        #   - Moves the red dot (visual indicator) to (x, y) coordinates.
        #   - Simulates mouseover, mousemove, and mouseenter events on the element under that point.
        #   - Returns the outer HTML of the target element (if found).
        # -----------------------------------------------------------------
        hover_event_script = """
        // Update the position of the visual indicator (red dot).
        const dot = document.getElementById('hoverDot');
        dot.style.left = `${arguments[0] - 4}px`;
        dot.style.top = `${arguments[1] - 4}px`;
        dot.style.display = 'block';

        // Identify the element at the given (x, y) position.
        const targetElement = document.elementFromPoint(arguments[0], arguments[1]);
        if (targetElement) {
            // Dispatch multiple events to simulate a hover that triggers tooltip display.
            ['mouseover', 'mousemove', 'mouseenter'].forEach(eventType => {
                targetElement.dispatchEvent(new MouseEvent(eventType, {
                    bubbles: true,
                    clientX: arguments[0],
                    clientY: arguments[1],
                    view: window
                }));
            });
        }
        // Return the HTML of the target element if it exists.
        return targetElement ? targetElement.outerHTML : null;
        """

        # -----------------------------------------------------------------
        # Loop across the horizontal range (SCAN_START_X to SCAN_END_X) to simulate hover events
        # and extract tooltip data from the chart.
        # In this updated version, we move very slowly by incrementing the x-coordinate by 1 pixel at every step.
        # -----------------------------------------------------------------
        while current_scan_x <= SCAN_END_X:
            try:
                # Set target coordinates for hovering.
                target_x = current_scan_x
                target_y = SCAN_Y

                # Execute the hover event script with the target coordinates.
                element_html = driver.execute_script(hover_event_script, target_x, target_y)
                
                # If no element is found at these coordinates, raise an exception.
                if not element_html:
                    raise Exception("No element found at the current coordinates")

                # Wait briefly (up to 1.5 seconds) for the tooltip to become visible.
                tooltip_element = WebDriverWait(driver, 1.5).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, "div.google-visualization-tooltip.visible"))
                )

                # -----------------------------------------------------------------
                # Extract data from the tooltip:
                #   - The first list item contains the date.
                #   - The remaining list items contain metrics (key-value pairs).
                # -----------------------------------------------------------------
                tooltip_date = tooltip_element.find_element(By.CSS_SELECTOR, "li:first-child span").text.strip()
                data_entry = {"Date": tooltip_date}
                
                # Loop through the other list items to extract metric data.
                for metric_element in tooltip_element.find_elements(By.CSS_SELECTOR, "li:not(:first-child)"):
                    # Each metric is expected to have two span elements: one for the label and one for the value.
                    label_spans = metric_element.find_elements(By.CSS_SELECTOR, "span.custom-label")
                    if len(label_spans) >= 2:
                        metric_label = label_spans[0].text.strip().rstrip(':')
                        metric_value = label_spans[1].text.strip()
                        data_entry[metric_label] = metric_value
                        data_headers.add(metric_label)
                
                # Avoid duplicate entries: add the entry only if the date hasn't been captured yet.
                if not any(existing_entry["Date"] == tooltip_date for existing_entry in scraped_data):
                    scraped_data.append(data_entry)
                    print(f"✅ Captured data for date: {tooltip_date}")
                # In all cases, advance by 1 pixel (moving very slowly).
                current_scan_x += 1

            except Exception as error:
                # Print an error message (up to 50 characters) and move forward by 1 pixel.
                print(f"⚠️ Error at X={current_scan_x}: {str(error)[:50]}")
                current_scan_x += 1
                continue

            finally:
                # Calculate and print the scanning progress as a percentage.
                progress = ((current_scan_x - SCAN_START_X) / (SCAN_END_X - SCAN_START_X)) * 100
                print(f"Progress: {min(progress, 100):.1f}%")

    finally:
        # -----------------------------------------------------------------
        # After scanning, switch back to the default content (exit the iframe).
        # Ensure that the output folder "data/" exists, then save the scraped data to a CSV file.
        # -----------------------------------------------------------------
        driver.switch_to.default_content()
        output_data_folder = "data"  # Folder where the CSV file will be saved.
        if not os.path.exists(output_data_folder):
            os.makedirs(output_data_folder)
        
        if scraped_data:
            output_csv_path = os.path.join(output_data_folder, "pvc_data.csv")
            # Write the data to CSV with the field names: "Date" plus all other sorted headers.
            with open(output_csv_path, "w", newline="", encoding="utf-8") as csv_file:
                csv_writer = csv.DictWriter(csv_file, fieldnames=["Date"] + sorted(data_headers))
                csv_writer.writeheader()
                csv_writer.writerows(scraped_data)
            print(f"✅ Saved {len(scraped_data)} records to {output_csv_path}")
        else:
            print("❌ No data collected")
        
        # Close the browser to end the session.
        driver.quit()
