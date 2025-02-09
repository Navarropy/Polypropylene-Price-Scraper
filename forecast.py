#!/usr/bin/env python3

import os                    # Operating system interfaces (e.g., file paths)
import glob                  # Filename pattern matching (to find files)
import re                    # Regular expression operations
import pandas as pd          # Data analysis library (for DataFrames)
import numpy as np           # Numerical operations library
import matplotlib.pyplot as plt  # Plotting library
from prophet import Prophet  # Forecasting library by Facebook
from dateutil.parser import parse  # Date string parser

# ---------------------------------------------------------------------
# Function: parse_portuguese_date
# ---------------------------------------------------------------------
def parse_portuguese_date(date_string):
    """
    Convert a date string that may contain Portuguese month abbreviations
    into a standard datetime object. If the conversion fails, return pd.NaT.
    
    Parameters:
      date_string (str): The input date string (possibly with Portuguese abbreviations)
    
    Returns:
      datetime or pd.NaT: The parsed date or a "Not a Time" value if parsing fails.
    """
    # Mapping of Portuguese month abbreviations to English abbreviations.
    month_translation = {
        'jan.': 'Jan', 'fev.': 'Feb', 'mar.': 'Mar', 'abr.': 'Apr',
        'mai.': 'May', 'jun.': 'Jun', 'jul.': 'Jul', 'ago.': 'Aug',
        'set.': 'Sep', 'out.': 'Oct', 'nov.': 'Nov', 'dez.': 'Dec',
        'z.': 'Dec'
    }
    # Ensure the input is a string; if not, return "Not a Time".
    if not isinstance(date_string, str):
        return pd.NaT
    # Replace any Portuguese month abbreviations with their English equivalents.
    for pt_abbr, en_abbr in month_translation.items():
        date_string = date_string.replace(pt_abbr, en_abbr)
    try:
        # Parse the date string using fuzzy parsing (ignoring unknown tokens).
        return parse(date_string, fuzzy=True)
    except:
        return pd.NaT

# ---------------------------------------------------------------------
# Function: sanitize_filename
# ---------------------------------------------------------------------
def sanitize_filename(file_name):
    """
    Replace any characters that are forbidden in Windows filenames with underscores.
    
    Parameters:
      file_name (str): The original file name.
      
    Returns:
      str: A sanitized version of the file name safe for use on Windows.
    """
    # The regular expression matches any forbidden character.
    return re.sub(r'[\\/:*?"<>|]+', '_', str(file_name))

# ---------------------------------------------------------------------
# Function: run_prophet_on_subdf
# ---------------------------------------------------------------------
def run_prophet_on_subdf(product_data, product_name, file_base_name, output_directory, forecast_periods=12):
    """
    Fit a Prophet forecasting model on a single product's data,
    generate future predictions, and save both forecast and component plots.
    
    Parameters:
      product_data (DataFrame): Data for one product (must include 'Date' and 'Value' columns).
      product_name (str): The name of the product.
      file_base_name (str): The base name from the original input file.
      output_directory (str): Directory to save the generated plots.
      forecast_periods (int): The number of future periods to forecast (default 12).
    """
    # Remove rows with missing values in 'Value' and sort the data by 'Date'
    product_data = product_data.dropna(subset=['Value']).sort_values('Date')
    if product_data.empty:
        return  # Exit if there's no data to forecast

    # Prepare the DataFrame for Prophet by selecting relevant columns and renaming them
    forecast_data = product_data[['Date', 'Value']].copy()
    # Prophet requires columns to be named 'ds' (for date) and 'y' (for the value)
    forecast_data.rename(columns={'Date': 'ds', 'Value': 'y'}, inplace=True)
    forecast_data['ds'] = pd.to_datetime(forecast_data['ds'])  # Ensure 'ds' is in datetime format

    # Initialize the Prophet model with custom settings:
    # - yearly seasonality enabled to capture annual trends
    # - weekly seasonality disabled
    # - increased prior scales for seasonality and trend flexibility
    model = Prophet(
        weekly_seasonality=False,
        yearly_seasonality=True,
        seasonality_prior_scale=15,   # Default is 10; increased for flexibility
        changepoint_prior_scale=0.5   # Default is 0.05; increased for more responsive trend changes
    )

    # Add a custom monthly seasonality component to capture monthly fluctuations.
    model.add_seasonality(
        name='monthly',
        period=30.5,        # Approximately the number of days in a month
        fourier_order=5,    # Number of Fourier terms to model the seasonality shape
        prior_scale=10
    )

    # Fit the model on the historical data.
    model.fit(forecast_data)

    # Create a DataFrame that extends into the future by 'forecast_periods' months.
    future_dates = model.make_future_dataframe(periods=forecast_periods, freq='MS')  # 'MS' = Month Start
    # Use the model to predict future values.
    forecast = model.predict(future_dates)

    # Generate the forecast plot (shows historical data plus predictions)
    forecast_plot = model.plot(forecast)
    forecast_plot.suptitle(f"Prophet Forecast - Product: {product_name}", fontsize=14)
    forecast_plot.subplots_adjust(top=0.88)  # Adjust layout to ensure the title is not clipped

    # Create a safe file name for the product by removing forbidden characters.
    safe_product_name = sanitize_filename(product_name)
    forecast_filename = f"{file_base_name}__{safe_product_name}__forecast.png"
    forecast_output_path = os.path.join(output_directory, forecast_filename)
    # Save the forecast plot as a PNG file.
    forecast_plot.savefig(forecast_output_path, dpi=150)
    plt.close(forecast_plot)  # Close the figure to free memory
    print(f"   -> Saved forecast: {forecast_output_path}")

    # Generate the components plot (shows trend, yearly and monthly seasonality, etc.)
    components_plot = model.plot_components(forecast)
    components_plot.suptitle(f"Forecast Components - Product: {product_name}", fontsize=14)
    components_plot.subplots_adjust(top=0.88)
    components_filename = f"{file_base_name}__{safe_product_name}__components.png"
    components_output_path = os.path.join(output_directory, components_filename)
    # Save the components plot.
    components_plot.savefig(components_output_path, dpi=150)
    plt.close(components_plot)
    print(f"   -> Saved components: {components_output_path}")

# ---------------------------------------------------------------------
# Function: generate_forecasts
# ---------------------------------------------------------------------
def generate_forecasts(normalized_folder='normalized_files', output_folder='regression_plots', forecast_periods=12):
    """
    Read each normalized CSV file (with columns [Date, Product, Value]) from the given folder,
    group the data by product, and run the Prophet forecast for each product.
    Save the resulting forecast and component plots to the output folder.
    
    Parameters:
      normalized_folder (str): Directory containing the normalized CSV files.
      output_folder (str): Directory where the output plots will be saved.
      forecast_periods (int): Number of future periods (months) to forecast.
    """
    # Create the output folder if it doesn't exist.
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Get a list of all files ending with '_normalized.csv' in the normalized folder.
    normalized_files = glob.glob(os.path.join(normalized_folder, '*_normalized.csv'))
    if not normalized_files:
        print(f"No normalized files found in '{normalized_folder}'.")
        return

    # Process each normalized CSV file.
    for csv_file in normalized_files:
        # Extract the base filename (without extension) for naming output files.
        file_base_name = os.path.splitext(os.path.basename(csv_file))[0]
        print(f"\n[Prophet] Processing file: {csv_file}")

        # Read the CSV file, treating all columns as strings.
        data_frame = pd.read_csv(csv_file, dtype=str)
        # Standardize column names by stripping whitespace and capitalizing.
        data_frame.columns = data_frame.columns.str.strip().str.capitalize()

        # Ensure the file contains exactly three columns: Date, Product, and Value.
        required_columns = {'Date', 'Product', 'Value'}
        if set(data_frame.columns) != required_columns:
            print("   -> Skipping (not 3-col [Date, Product, Value])")
            continue

        # Convert the Date column into proper datetime objects using our parser.
        data_frame['Date'] = data_frame['Date'].apply(parse_portuguese_date)
        # Standardize the numeric values: replace commas with periods and convert to numbers.
        data_frame['Value'] = data_frame['Value'].str.replace(',', '.')
        data_frame['Value'] = pd.to_numeric(data_frame['Value'], errors='coerce')
        # Remove any rows with invalid or missing dates.
        data_frame.dropna(subset=['Date'], inplace=True)

        # Group the data by product and run the forecast for each group.
        for product_name, product_data in data_frame.groupby('Product'):
            run_prophet_on_subdf(
                product_data,      # DataFrame for the product
                product_name,    
                file_base_name,  
                output_folder,  
                forecast_periods   # Number of future periods to forecast
            )

# ---------------------------------------------------------------------
# Main Script Entry Point
# ---------------------------------------------------------------------
if __name__ == '__main__':
    # Run the forecast generation function with:
    # - normalized data from the folder 'normalized_files'
    # - output images saved to 'regression_plots'
    # - forecast period set to 12 (e.g., 12 months)
    generate_forecasts(
        normalized_folder='normalized_files',
        output_folder='regression_plots',
        forecast_periods=12
    )
    print("\nForecasting complete!")
