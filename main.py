from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv

# Initialize browser
driver = webdriver.Chrome()
driver.maximize_window()

try:
    # Load main page
    driver.get("https://businessanalytiq.com/procurementanalytics/index/pvc-price-index/")

    # Create visual indicator directly in the iframe
    iframe = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='datastudio']"))
    )
    
    # Store iframe position before switching
    iframe_rect = driver.execute_script("""
        const rect = arguments[0].getBoundingClientRect();
        return {
            left: rect.left + window.pageXOffset,
            top: rect.top + window.pageYOffset,
            width: rect.width,
            height: rect.height
        };
    """, iframe)

    # Switch to iframe and set up elements
    driver.switch_to.frame(iframe)
    
    # Add visual indicator inside iframe
    driver.execute_script("""
        const dot = document.createElement('div');
        dot.id = 'hoverDot';
        dot.style = 'position: fixed; width: 8px; height: 8px; background: red;'
                  + 'border-radius: 50%; z-index: 99999; display: none;'
                  + 'box-shadow: 0 0 5px red; pointer-events: none;';
        document.body.appendChild(dot);
    """)

    # Wait for chart elements
    chart = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "div.ng2-canvas-container.grid"))
    )
    chart_rect = driver.execute_script("return arguments[0].getBoundingClientRect();", chart)

    # Configure scanning parameters
    SCAN_START_X = 50
    SCAN_END_X = chart_rect['width'] - 50
    SCAN_Y = chart_rect['height'] * 0.3  # 30% from top
    current_x = SCAN_START_X
    data = []
    headers = set()

    # Enhanced event simulation script
    hover_script = """
    // Update visual indicator
    const dot = document.getElementById('hoverDot');
    dot.style.left = `${arguments[0] - 4}px`;
    dot.style.top = `${arguments[1] - 4}px`;
    dot.style.display = 'block';

    // Create synthetic hover event sequence
    const target = document.elementFromPoint(arguments[0], arguments[1]);
    if (target) {
        // Full event sequence for tooltip activation
        ['mouseover', 'mousemove', 'mouseenter'].forEach(type => {
            target.dispatchEvent(new MouseEvent(type, {
                bubbles: true,
                clientX: arguments[0],
                clientY: arguments[1],
                view: window
            }));
        });
    }
    return target ? target.outerHTML : null;
    """

    while current_x <= SCAN_END_X:
        try:
            # Calculate coordinates within iframe
            target_x = current_x
            target_y = SCAN_Y

            # Execute combined hover simulation and visual update
            element_html = driver.execute_script(hover_script, target_x, target_y)
            
            if not element_html:
                raise Exception("No element at coordinates")

            # Wait for tooltip stabilization
            tooltip = WebDriverWait(driver, 1.5).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.google-visualization-tooltip.visible"))
            )

            # Extract data (keep your existing code here)
            date = tooltip.find_element(By.CSS_SELECTOR, "li:first-child span").text.strip()
            entry = {"Date": date}
            
            for metric in tooltip.find_elements(By.CSS_SELECTOR, "li:not(:first-child)"):
                spans = metric.find_elements(By.CSS_SELECTOR, "span.custom-label")
                if len(spans) >= 2:
                    key = spans[0].text.strip().rstrip(':')
                    value = spans[1].text.strip()
                    entry[key] = value
                    headers.add(key)
            
            if not any(d['Date'] == date for d in data):
                data.append(entry)
                print(f"✅ Captured {date}")
                current_x += 5  # Fine step after success
            else:
                current_x += 15  # Skip duplicates faster

        except Exception as e:
            print(f"⚠️ Error at X={current_x}: {str(e)[:50]}")
            current_x += 25  # Skip problematic areas
            continue

        finally:
            # Update progress
            progress = ((current_x - SCAN_START_X) / (SCAN_END_X - SCAN_START_X)) * 100
            print(f"Progress: {min(progress, 100):.1f}%")

finally:
    # Cleanup and save data
    driver.switch_to.default_content()
    if data:
        with open("pvc_data.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Date"] + sorted(headers))
            writer.writeheader()
            writer.writerows(data)
        print(f"✅ Saved {len(data)} records")
    else:
        print("❌ No data collected")
    
    driver.quit()