# Polypropylene Price Scraper

A Selenium-based automation tool that collects historical polypropylene price data from Trading Economics.

## Features

- 📅 Automated date range selection (2014-01-01 to 3 days before current date)
- 📈 Dynamic chart interaction with mouse movement simulation
- 🚀 Adaptive scanning speed (slows down for data points, speeds up in empty areas)
- 📊 Outputs structured JSON data with date-value pairs
- ✅ Real-time progress tracking and duplicate prevention

## Requirements

- Python 3.8+
- Google Chrome browser
- ChromeDriver (matching your Chrome version)
- Python packages:
  ```bash
  pip install selenium


## Installation

1. Install ChromeDriver:
   - Download from [ChromeDriver site](https://sites.google.com/chromium.org/driver/)
   - Add to system PATH or place in project directory

2. Clone repository:
   ```bash
   git clone https://github.com/yourusername/polypropylene-scraper.git
   cd polypropylene-scraper
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the script:
```bash
python main.py
```

The script will:
1. Open Chrome browser and navigate to Trading Economics
2. Set date range automatically
3. Scan the price chart
4. Output `polypropylene_prices.json` with collected data

Sample output:
```json
[
  {
    "date": "Mar 01 2020",
    "value": "7321.0"
  },
  {
    "date": "Mar 02 2020",
    "value": "7345.0"
  }
]
```

## Configuration

Modify these variables in the script:
```python
# Date settings (format: "YYYY-MM-DD")
start_date = "2014-01-01"
end_date = datetime.now() - timedelta(days=3)

# Scanning parameters
step = 1               # Initial step size (pixels)
max_step = 50          # Maximum step size acceleration
scan_timeout = 0.5     # Element detection timeout (seconds)
```

## Troubleshooting

Common issues:
- **ChromeDriver version mismatch**:  
  Ensure ChromeDriver matches your Chrome version
- **Element not found**:  
  Check for website layout changes or popups
- **Empty output**:  
  Add longer `time.sleep()` after chart loading

For cookie consent handling (add before main script):
```python
try:
    driver.find_element(By.XPATH, '//*[contains(text(), "Accept")]').click()
except:
    pass
```

## Performance

Typical results:
- ⏱️ 10-15 minutes for full historical range
- 📈 500-700 data points collected
- 💾 20-30KB JSON file output

## License

Free for non-commercial use. For commercial applications, ensure compliance with [Trading Economics' terms of service](https://tradingeconomics.com/terms-of-service).

---
**Note**: This script is for educational purposes only. Respect website scraping policies and consider using official APIs for production use.
```
