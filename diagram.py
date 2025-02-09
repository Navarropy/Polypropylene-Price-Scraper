#!/usr/bin/env python3
# Tells the operating system to use Python 3 to run this script.

import os                    # Provides functions for interacting with the operating system.
import glob                  # Helps find files matching specified patterns (e.g., "*.csv").
import re                    # Provides support for regular expressions for pattern matching.
import pandas as pd          # Used for data manipulation and analysis (DataFrames).
import numpy as np           # Provides support for numerical operations and arrays.
import matplotlib.pyplot as plt  # Used for creating plots and visualizations.
import pywt                  # PyWavelets library: used to perform wavelet transforms (analyzing signals in time and frequency).

# Global parameters for wavelet analysis:
wavelet_name = 'cmor1.5-1.0'   # Name of the wavelet to use (here, a complex Morlet wavelet with specific parameters).
scales = np.arange(1, 128)     # Array of scales for the continuous wavelet transform (CWT); scales affect time-frequency resolution.
sampling_period = 1            # Sampling period of the data (e.g., 1 if data is daily or 1/12 if data is monthly).

# ---------------------------------------------------------------------
# Function: sanitize_filename
# ---------------------------------------------------------------------
def sanitize_filename(file_name):
    """
    Replace characters that are forbidden in file names (\, /, :, *, ?, ", <, >, |)
    with an underscore. This ensures the filename is valid for Windows.
    
    Parameters:
      file_name (str): The original file name.
    
    Returns:
      str: A sanitized file name safe for saving.
    """
    # Replace any forbidden character with an underscore.
    return re.sub(r'[\\/:*?"<>|]+', '_', str(file_name))

# ---------------------------------------------------------------------
# Function: generate_wavelet_diagram
# ---------------------------------------------------------------------
def generate_wavelet_diagram(data_frame, product_name, output_file_path):
    """
    Generate and save a wavelet scalogram diagram for a product's time series data.
    
    This function:
      - Sorts the data by date and removes missing values.
      - Extracts the time series (dates and values).
      - Computes the Continuous Wavelet Transform (CWT) of the time series using a chosen wavelet.
      - Converts the wavelet power to a logarithmic scale for better visualization.
      - Creates a figure with:
          * A plot of the original time series.
          * A scalogram (contour plot of the wavelet power vs. time and scale).
          * A color bar indicating the log10 wavelet power.
      - Saves the figure as a PNG file.
    
    Parameters:
      data_frame (DataFrame): Contains the time series data with at least 'Date' and 'Value' columns.
      product_name (str): The product name, used for labeling the diagram.
      output_file_path (str): The full path (including file name) where the diagram will be saved.
    """
    # Sort data by the 'Date' column and drop rows where 'Value' is missing.
    data_frame = data_frame.sort_values('Date').dropna(subset=['Value'])
    time_axis = data_frame['Date']              # X-axis: dates.
    signal_values = data_frame['Value'].values    # Y-axis: numeric values of the time series.

    # Create a new figure with a specified size.
    figure = plt.figure(figsize=(14, 10))
    # Set the main title of the figure, including the product name.
    figure.suptitle(f"Wavelet Scalogram - Product: {product_name}", fontsize=16)

    # Create a grid layout for subplots:
    # - 2 rows and 2 columns.
    # - The left column takes 95% of the width, and the right column takes 5% (for the color bar).
    # - The bottom row is taller (3x height) than the top row.
    grid_spec = figure.add_gridspec(2, 2, width_ratios=[0.95, 0.05], height_ratios=[1, 3])
    # Subplot for the time series at the top left.
    ax_time_series = figure.add_subplot(grid_spec[0, 0])
    # Subplot for the scalogram (wavelet transform) at the bottom left; shares the x-axis with the time series plot.
    ax_scalogram = figure.add_subplot(grid_spec[1, 0], sharex=ax_time_series)
    # Subplot for the colorbar on the right, spanning both rows.
    ax_colorbar = figure.add_subplot(grid_spec[:, 1])

    # Plot the time series data in blue.
    ax_time_series.plot(time_axis, signal_values, color='blue', linewidth=2)
    ax_time_series.set(title='Time Series', ylabel='Value')
    ax_time_series.grid(True)  # Add gridlines for easier reading.

    # ---------------------------------------------------------------------
    # Compute the Continuous Wavelet Transform (CWT):
    # - The CWT decomposes the time series into time-frequency space.
    # - 'pywt.cwt' returns coefficients representing how much a wavelet (scaled version of a function)
    #   matches the data at each scale and time.
    # - Here we compute the power (magnitude squared) of these coefficients.
    # - To better visualize the range of power values, we take the logarithm (base 10) of the power.
    # ---------------------------------------------------------------------
    cwt_coefficients, _ = pywt.cwt(signal_values, scales, wavelet_name, sampling_period=sampling_period)
    wavelet_power = np.abs(cwt_coefficients) ** 2  # Compute power from coefficients.
    # Replace any zeros with a very small number to avoid issues when taking the logarithm.
    wavelet_power[wavelet_power == 0] = 1e-6
    log_wavelet_power = np.log10(wavelet_power)

    # Create a contour plot (scalogram) of the log-transformed wavelet power.
    # - X-axis: time.
    # - Y-axis: log2 of the scales (provides a more uniform display of scales).
    # - 100 contour levels with the 'viridis' color map.
    contour_plot = ax_scalogram.contourf(
        time_axis,                     # X-axis values (time).
        np.log2(scales),               # Y-axis values: log2 of scales.
        log_wavelet_power,             # Z-axis values: log10 of wavelet power.
        100,                           # Number of contour levels.
        cmap='viridis'                 # Color map for visualization.
    )
    ax_scalogram.set(title='Scalogram (CWT)', xlabel='Date', ylabel='Scale (log2)')
    ax_scalogram.grid(True)  # Enable grid lines.

    # Add a colorbar to the right of the scalogram indicating the log10 wavelet power.
    figure.colorbar(contour_plot, cax=ax_colorbar, label='Log10 Wavelet Power')

    # Adjust the layout to prevent overlapping elements.
    plt.tight_layout()
    # Save the entire figure (time series + scalogram) to the specified output file.
    figure.savefig(output_file_path, dpi=150)
    plt.close(figure)  # Close the figure to free up memory.

# ---------------------------------------------------------------------
# Function: generate_diagrams
# ---------------------------------------------------------------------
def generate_diagrams(normalized_folder='normalized_files', diagrams_folder='diagrams'):
    """
    For each normalized CSV file in the specified folder, generate wavelet scalogram diagrams for each product.
    
    Parameters:
      normalized_folder (str): Directory containing normalized CSV files (with columns [Date, Product, Value]).
      diagrams_folder (str): Directory where the generated diagram images will be saved.
      
    This function:
      - Ensures the output directory exists.
      - Finds all normalized CSV files.
      - For each file, groups the data by product.
      - For each product, generates and saves a wavelet diagram.
      - Skips diagram generation if an output file already exists.
    """
    # Create the output directory for diagrams if it doesn't exist.
    if not os.path.exists(diagrams_folder):
        os.makedirs(diagrams_folder)

    # Use glob to list all files ending with "_normalized.csv" in the normalized folder.
    all_normalized_files = glob.glob(os.path.join(normalized_folder, '*_normalized.csv'))
    if not all_normalized_files:
        print(f"No normalized files found in '{normalized_folder}'.")
        return

    # Loop through each normalized CSV file.
    for csv_file in all_normalized_files:
        print(f"\nGenerating wavelet diagrams from: {csv_file}")
        # Read the CSV file into a DataFrame, parsing the 'Date' column as dates.
        data_frame = pd.read_csv(csv_file, parse_dates=['Date'])
        # Get the base name of the file (without directory and extension) for naming outputs.
        base_file_name = os.path.splitext(os.path.basename(csv_file))[0]

        # Group the data by the 'Product' column.
        for product_name, product_df in data_frame.groupby('Product'):
            # Sanitize the product name to create a safe file name.
            safe_product_name = sanitize_filename(product_name)
            # Construct the output file name.
            output_file_name = f"{base_file_name}__{safe_product_name}.png"
            output_file_path = os.path.join(diagrams_folder, output_file_name)

            # --------------- SKIP CHECK ---------------
            # If the diagram file already exists, skip generating it.
            if os.path.exists(output_file_path):
                print(f"   -> Diagram already exists, skipping: {output_file_path}")
                continue
            # ------------------------------------------

            # Generate the wavelet diagram for this product's data.
            generate_wavelet_diagram(product_df, product_name, output_file_path)
            print(f"   -> Diagram saved: {output_file_path}")
