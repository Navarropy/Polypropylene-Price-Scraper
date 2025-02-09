---

# Business Analytics Data Processing & Forecasting

This project contains several Python scripts that work together to process raw data, generate diagrams, perform multi-resolution analysis, and forecast future trends. The code is designed to handle data related to procurement analytics (e.g., PVC price index) and can deal with multiple data formats (e.g., raw Excel/CSV files, normalized data).

Below is an overview of each file in the project and what it does.

---

## File: `start.py`

- **Purpose:**  
  Serves as the main entry point to run the entire processing pipeline. This file orchestrates the execution of the other scripts in the correct order.
  
- **What It Does:**  
  - Typically, it might call functions from the other modules (normalization, diagram generation, MRA, and forecasting) to perform the complete workflow.
  - It ensures that data flows from the raw input to normalized output, then to visualization and forecast stages.
  
- **How to Use:**  
  - Run this file to execute the entire pipeline.  
    ```bash
    python start.py
    ```
  - It should automatically locate the raw data files (depending on your configuration) and invoke the other modules in sequence.

---

## File: `normalization.py`

- **Purpose:**  
  Reads raw data files (Excel or CSV) from an input folder (e.g., `data/`), normalizes them into a consistent format with three columns (`Date`, `Product`, `Value`), and writes normalized CSV files to an output folder (e.g., `normalized_files/`).

- **Key Functions and Components:**
  - **`parse_portuguese_date(date_str)`**  
    Converts date strings that may contain Portuguese month abbreviations into standard datetime objects.
    
  - **`parse_kw_date(kw_str)`**  
    Parses week-based strings (e.g., "KW 2/2018") and converts them to a date (usually representing the Monday of that ISO week).
    
  - **`clean_numeric(val)`**  
    Standardizes numeric values by removing thousand separators and ensuring the correct decimal notation.
    
  - **`trim_row(row)`**  
    Removes trailing empty cells from a row.
    
  - **`process_quarters(df, product_name)`**  
    Converts a table with a year column and quarterly columns into a long format DataFrame with proper dates (using mid-quarter dates).
    
  - **`load_normalized(filepath)`**  
    Detects the layout of the input file (date-based, week-based, or multi-block/year–quarter) and returns a normalized DataFrame.
    
  - **`process_folder(input, output)`**  
    Iterates through all raw files in the input folder, processes them, and writes normalized CSV files to the output folder.

- **How to Use:**  
  - Run this script (or call its `process_folder` function) to normalize your raw data.  
    ```bash
    python normalization.py
    ```
  - Ensure that your raw data files are in the designated input folder (default is `data/`).

---

## File: `diagram.py`

- **Purpose:**  
  Uses Selenium to automate a browser, simulate hover events on a webpage’s chart (such as a PVC price index chart), extract tooltip data, and save the scraped data as a CSV file in the `data/` directory.

- **Key Functions and Components:**
  - **Browser Initialization and Navigation:**  
    Opens a Chrome browser window, navigates to the target URL, and waits for the page (and specific iframe) to load.
    
  - **Iframe and Chart Handling:**  
    Locates an iframe containing Data Studio content and extracts the chart container’s position and dimensions.
    
  - **Visual Indicator:**  
    Inserts a red dot inside the iframe to indicate where hover events are being simulated.
    
  - **Hover Event Simulation:**  
    Uses a JavaScript snippet to simulate mouse hover events (mouseover, mousemove, mouseenter) over the chart at precise coordinates.  
    In this updated version, the scanning loop moves horizontally in 1‑pixel increments.
    
  - **Data Extraction:**  
    When a tooltip appears, the script extracts the date (from the first list item) and other metrics (from subsequent list items) and stores them in a list.
    
  - **Progress Reporting and Error Handling:**  
    Displays progress percentage as the scan proceeds and handles errors by moving the scan position by 1 pixel.
    
  - **CSV Output:**  
    After scanning, the script saves the scraped data into a CSV file (`pvc_data.csv`) in the `data/` folder.
  - Make sure that the required dependencies (Selenium, ChromeDriver, etc.) are installed and correctly configured.

    ![pvc_data_normalized__Europe actual](https://github.com/user-attachments/assets/9c9c5ab7-18ed-4f70-b15f-fffd5081b129)


---

## File: `mra.py`

- **Purpose:**  
  Performs Multi-Resolution Analysis (MRA) on time series data using the Discrete Wavelet Transform (DWT). The analysis decomposes the data into multiple levels of detail (high-frequency components) and an approximation (low-frequency component).

- **Key Functions and Components:**
  - **`parse_portuguese_date(date_str)`**  
    Similar to the normalization file, it converts Portuguese date abbreviations to standard dates.
    
  - **`sanitize_filename(name)`**  
    Ensures filenames are valid by replacing forbidden characters.
    
  - **`do_mra_on_subdf(sub_df, base_name, product, output_folder)`**  
    For a given product’s subset of data:
    - Sorts data by date and drops missing values.
    - Normalizes the time series.
    - Uses the `db4` wavelet to perform DWT up to 8 levels (or maximum possible).
    - Reconstructs each detail component (representing high-frequency variations) and the approximation (low-frequency component).
    - Plots each component and the original data in a multi-panel diagram.
    - Saves the diagram as a PNG file.
    
  - **`generate_mra_all_files(data_folder, output_folder)`**  
    Iterates over all normalized files in the input folder, and for files with exactly 3 columns (`Date`, `Product`, `Value`), groups data by product and generates MRA diagrams.
  - The diagrams will be saved in the `mra_diagrams/` folder (or as configured).

  ![pvc_data_normalized__MRA__India actual](https://github.com/user-attachments/assets/1a90fa54-09a1-4a20-908d-bdec7c3b682f)


---

## File: `forecast.py`

- **Purpose:**  
  Uses Facebook Prophet to generate forecasts on time series data. It fits a forecasting model for each product and produces:
  - A forecast plot that shows historical data along with future predictions.
  - A components plot that displays trend, yearly seasonality, and custom monthly seasonality.
  
- **Key Functions and Components:**
  - **`parse_portuguese_date(date_str)`**  
    Converts date strings with Portuguese month abbreviations into datetime objects.
    
  - **`sanitize_filename(name)`**  
    Sanitizes product names to be safe for file naming.
    
  - **`run_prophet_on_subdf(sub_df, product, base_name, output_folder, periods=12)`**  
    For each product’s data:
    - Cleans and sorts the data.
    - Prepares the data by renaming columns as required by Prophet (`ds` for date and `y` for the value).
    - Initializes the Prophet model with custom parameters:
      - Yearly seasonality enabled, weekly seasonality disabled.
      - Custom monthly seasonality added.
      - Adjusted prior scales for seasonality and trend change.
    - Fits the model and creates a future dataframe (default 12 periods, usually months).
    - Generates forecast and components plots.
    - Saves these plots as PNG images.
    
  - **`generate_forecasts(normalized_folder, output_folder, forecast_periods=12)`**  
    Iterates over all normalized CSV files in the designated folder.
    - Checks that each file has exactly 3 columns (`Date`, `Product`, `Value`).
    - Converts and cleans the data.
    - Groups data by product and calls `run_prophet_on_subdf` to generate forecasts.
    
- **How to Use:**  
  - The forecast and component plots will be saved in the `regression_plots/` folder (or as configured).

![pvc_data_normalized__U S A  outlook__forecast](https://github.com/user-attachments/assets/de988ec4-8dd3-4d35-be51-b061fc2e4274)
![pvc_data_normalized__U S A  outlook__forecast](https://github.com/user-attachments/assets/15419ff2-ac51-4f5b-8d36-3bea243614df)


---

# Prerequisites

- **Python 3:** Ensure you have Python 3 installed.
- **Required Libraries:**  
  Install required Python packages (you may use `pip`):
  ```bash
  pip install pandas numpy matplotlib pywt python-dateutil selenium prophet
  ```
  - For Selenium, you also need the corresponding WebDriver (e.g., ChromeDriver) installed and in your system path.
- **Data Files:**  
  Place your raw data files in the expected input folder (for example, `data/` for normalization) before running the scripts.

---

# Running the Pipeline

1. **Normalization:**  
   Run `normalization.py` to convert raw data files into normalized CSV files.
   ```bash
   python normalization.py
   ```

2. **Diagram Generation:**  
   Run `diagram.py` to scrape tooltip data from the web and generate a CSV file.
   ```bash
   python diagram.py
   ```

3. **Multi-Resolution Analysis (MRA):**  
   Run `mra.py` to perform wavelet-based analysis and generate MRA diagrams.
   ```bash
   python mra.py
   ```

4. **Forecasting:**  
   Run `forecast.py` to generate forecasts and plots using Prophet.
   ```bash
   python forecast.py
   ```

5. **Overall Start:**  
   Optionally, if you have a `start.py` that calls these modules in order, run:
   ```bash
   python start.py
   ```

---

# Summary

- **start.py:**  
  Main entry point to run the entire data processing, visualization, and forecasting pipeline.

- **normalization.py:**  
  Reads raw data files, normalizes them into a standard format (with columns: Date, Product, Value), and saves the output.

- **diagram.py:**  
  Uses Selenium to automate a browser session, simulate hover events on a chart, extract tooltip data, and save it as a CSV file.

- **mra.py:**  
  Performs Multi-Resolution Analysis (MRA) using wavelet transforms (DWT with 'db4') to decompose time series data into detail and approximation components, then plots and saves the results.

- **forecast.py:**  
  Uses Facebook Prophet to forecast future values based on normalized time series data, generating both forecast plots and component (trend/seasonality) plots.

This README should provide you and your client with a clear understanding of what each file does and how the overall pipeline works. Happy coding!
