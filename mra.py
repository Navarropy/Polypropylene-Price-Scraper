#!/usr/bin/env python3
# mra.py: This script performs Multi-Resolution Analysis (MRA) on time series data.
# It uses the Discrete Wavelet Transform (DWT) with the 'db4' wavelet to decompose the data
# into detail and approximation components, then plots and saves the resulting diagram.

import os                    # Provides functions for interacting with the operating system.
import glob                  # Helps in file pattern matching (e.g., finding all CSV files in a folder).
import re                    # Provides regular expressions for text processing (e.g., sanitizing filenames).
import pandas as pd          # Data analysis library for handling DataFrames.
import numpy as np           # Supports numerical operations and array manipulation.
import matplotlib.pyplot as plt  # Used for creating plots and visualizations.
import pywt                  # PyWavelets library: used to perform wavelet transforms.
from dateutil.parser import parse  # Used to parse date strings into datetime objects.

# ---------------------------------------------------------------------
# Function: parse_portuguese_date
# ---------------------------------------------------------------------
def parse_portuguese_date(date_str):
    """
    Safely parse potential Portuguese month abbreviations into English,
    then parse with dateutil. If invalid, return pd.NaT ("Not a Time").
    
    Parameters:
      date_str (str): A date string that may include Portuguese month abbreviations.
    
    Returns:
      datetime or pd.NaT: The parsed datetime object, or pd.NaT if parsing fails.
    """
    # Dictionary mapping Portuguese month abbreviations to English abbreviations.
    month_map = {
        'jan.': 'Jan', 'fev.': 'Feb', 'mar.': 'Mar', 'abr.': 'Apr',
        'mai.': 'May', 'jun.': 'Jun', 'jul.': 'Jul', 'ago.': 'Aug',
        'set.': 'Sep', 'out.': 'Oct', 'nov.': 'Nov', 'dez.': 'Dec'
    }
    # If the input is not a string, return pd.NaT.
    if not isinstance(date_str, str):
        return pd.NaT

    # Replace each Portuguese abbreviation with the corresponding English abbreviation.
    for pt, en in month_map.items():
        date_str = date_str.replace(pt, en)
    try:
        # Parse the date string.
        # 'dayfirst=True' because the date is in day-first format.
        # 'fuzzy=True' allows ignoring extra text.
        return parse(date_str, dayfirst=True, fuzzy=True)
    except:
        return pd.NaT

# ---------------------------------------------------------------------
# Function: sanitize_filename
# ---------------------------------------------------------------------
def sanitize_filename(name):
    """
    Replace forbidden filename characters with underscores,
    so that Windows does not complain about invalid paths.
    
    Parameters:
      name (str): The original filename.
      
    Returns:
      str: A sanitized filename safe for saving.
    """
    return re.sub(r'[\\/:*?"<>|]+', '_', name)

# ---------------------------------------------------------------------
# Function: do_mra_on_subdf
# ---------------------------------------------------------------------
def do_mra_on_subdf(sub_df, base_name, product, output_folder):
    """
    Perform the DWT-based Multi-Resolution Analysis (MRA) on the 'Value' time series
    for a single product. This function:
      - Sorts the data by Date and drops missing values.
      - Normalizes the data to the range [0, 1].
      - Decomposes the normalized time series into detail and approximation components using DWT.
      - Reconstructs each detail component and the approximation.
      - Plots the detail components, the approximation, and the original normalized data.
      - Saves the resulting diagram to the output folder.
    
    Parameters:
      sub_df (DataFrame): Subset of data for one product (must include 'Date' and 'Value').
      base_name (str): Base name of the original file (used for output naming).
      product (str): The product name.
      output_folder (str): The directory where the output image will be saved.
    """
    # Sort by Date and drop rows where 'Value' is missing.
    sub_df = sub_df.dropna(subset=['Value']).sort_values('Date')
    # Extract the time series values and corresponding dates.
    time_series = sub_df['Value'].values
    time_index = sub_df['Date']

    # If there's no data left after dropping missing values, exit the function.
    if len(time_series) == 0:
        return

    # Normalize the time series to the range [0, 1] for consistent scaling.
    min_val, max_val = time_series.min(), time_series.max()
    if max_val != min_val:
        norm_series = (time_series - min_val) / (max_val - min_val)
    else:
        norm_series = time_series - min_val  # All values are equal; normalization yields zeros.

    # -----------------------------------------------------------------
    # Perform Discrete Wavelet Transform (DWT) using the 'db4' wavelet.
    # 'db4' is a Daubechies wavelet with 4 vanishing moments.
    # Determine the maximum level of decomposition possible, then use up to 8 levels.
    # -----------------------------------------------------------------
    wavelet_name = 'db4'
    max_decomp_level = pywt.dwt_max_level(len(norm_series), pywt.Wavelet(wavelet_name).dec_len)
    dwt_level = min(8, max_decomp_level)
    # Compute the wavelet decomposition coefficients.
    wavelet_coeffs = pywt.wavedec(norm_series, wavelet_name, level=dwt_level)

    # -----------------------------------------------------------------
    # Reconstruct detail components for each level.
    # Each detail component represents the high-frequency parts (variations) at that level.
    # -----------------------------------------------------------------
    detail_components = []
    for i in range(1, len(wavelet_coeffs)):
        coeffs_copy = []
        # Create a copy of the coefficients where only the current level is kept,
        # and all other levels are replaced with zeros.
        for j, c in enumerate(wavelet_coeffs):
            if j == i:
                coeffs_copy.append(c)
            else:
                coeffs_copy.append(np.zeros_like(c))
        # Reconstruct the signal corresponding to this detail component using the inverse DWT.
        detail_signal = pywt.waverec(coeffs_copy, wavelet_name)[:len(norm_series)]
        detail_components.append(detail_signal)
    # Reverse the list so that the highest resolution detail (smallest scale) comes first.
    detail_components.reverse()

    # -----------------------------------------------------------------
    # Reconstruct the approximation (the low-frequency component).
    # Only the approximation coefficients (level 0) are kept; the rest are set to zeros.
    # -----------------------------------------------------------------
    approx_coeffs = [wavelet_coeffs[0]] + [np.zeros_like(c) for c in wavelet_coeffs[1:]]
    approximation_signal = pywt.waverec(approx_coeffs, wavelet_name)[:len(norm_series)]

    # -----------------------------------------------------------------
    # Plot the Multi-Resolution Analysis (MRA):
    # - Each detail component is plotted in its own subplot.
    # - The approximation signal is plotted.
    # - The original (normalized) data is also plotted.
    # The number of plots = number of detail components + 2.
    # -----------------------------------------------------------------
    num_plots = dwt_level + 2
    fig, axes = plt.subplots(num_plots, 1, sharex=True, figsize=(10, 2 * num_plots))
    fig.suptitle(f"MRA (db4)\nFile: {base_name}, Product: {product}", fontsize=14)

    # Plot each detail component.
    for idx, detail in enumerate(detail_components):
        axes[idx].plot(time_index, detail, 'C0', linewidth=1)
        # Label the subplot with "D1", "D2", etc. ("D" stands for detail).
        axes[idx].set_ylabel(f"D{idx+1}", rotation=0, labelpad=25)
        axes[idx].grid(True)

    # Plot the approximation (smooth) component in the second-to-last subplot.
    axes[-2].plot(time_index, approximation_signal, 'C1', linewidth=1)
    # Label with "S<level>" where S stands for the smooth or approximation component.
    axes[-2].set_ylabel(f"S{dwt_level}", rotation=0, labelpad=25)
    axes[-2].grid(True)

    # Plot the original (normalized) data in the last subplot.
    axes[-1].plot(time_index, norm_series, 'k', linewidth=1)
    axes[-1].set_ylabel("Data", rotation=0, labelpad=25)
    axes[-1].grid(True)
    axes[-1].set_xlabel("Date")

    # Adjust the layout so that subplots do not overlap.
    plt.tight_layout()

    # -----------------------------------------------------------------
    # Save the MRA diagram:
    # Create a safe file name for the product, construct the output path,
    # save the figure as a PNG image at 150 dpi, and close the figure.
    # -----------------------------------------------------------------
    safe_product = sanitize_filename(product)
    out_name = f"{base_name}__MRA__{safe_product}.png"
    out_path = os.path.join(output_folder, out_name)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"   -> MRA saved: {out_path}")

# ---------------------------------------------------------------------
# Function: generate_mra_all_files
# ---------------------------------------------------------------------
def generate_mra_all_files(data_folder='normalized_files', output_folder='mra_diagrams'):
    """
    Process all normalized files in the specified data folder to generate MRA diagrams.
    For each file with exactly 3 columns (Date, Product, Value), perform MRA analysis.
    
    Parameters:
      data_folder (str): Directory containing normalized data files.
      output_folder (str): Directory where the MRA diagrams will be saved.
    """
    # Create the output folder if it doesn't exist.
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Find all files in the data folder (regardless of extension).
    all_files = glob.glob(os.path.join(data_folder, '*.*'))
    # Process each file.
    for fpath in all_files:
        # Get the file extension (e.g., .csv, .xls, .xlsx).
        ext = os.path.splitext(fpath)[1].lower()
        # Only process files with these extensions.
        if ext not in ['.csv','.xls','.xlsx']:
            continue

        # Get the base file name (without directory and extension) for output naming.
        base_name = os.path.splitext(os.path.basename(fpath))[0]

        # Read the file as a DataFrame, interpreting all columns as strings.
        if ext in ['.xls','.xlsx']:
            df = pd.read_excel(fpath, dtype=str)
        else:
            df = pd.read_csv(fpath, dtype=str, encoding='utf-8')
        
        # Convert all column names to lower case and remove extra whitespace.
        df.columns = df.columns.str.strip().str.lower()
        
        # Create a set of the column names.
        colset = set(df.columns)
        # Define the required set of columns.
        needed = {'date','product','value'}
        
        # If the DataFrame has exactly 3 columns and they match the needed set:
        if len(df.columns) == 3 and colset == needed:
            print(f"\n[MRA] 3-col file: {fpath}")
            
            # Rename the columns to standard names with capital letters.
            df.rename(columns={'date':'Date','product':'Product','value':'Value'}, inplace=True)
            
            # Parse the Date column using the custom Portuguese date parser.
            df['Date'] = df['Date'].apply(parse_portuguese_date)
            # Replace commas with periods in the Value column to standardize decimals.
            df['Value'] = df['Value'].str.replace(',', '.')
            # Convert the Value column to numeric values.
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
            # Drop rows where Date parsing failed.
            df.dropna(subset=['Date'], inplace=True)
            # Sort the DataFrame by Date.
            df.sort_values('Date', inplace=True)

            # Group the data by Product and perform MRA on each group.
            for product, sub_df in df.groupby('Product'):
                do_mra_on_subdf(sub_df, base_name, product, output_folder)

        else:
            # If the file does not have exactly 3 columns, skip it and print the column names.
            print(f"\n[MRA] Skipping: {fpath}")
            print("Columns are:", df.columns.tolist())
