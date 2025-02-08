# diagram.py

import os
import glob
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pywt

wavelet_name = 'cmor1.5-1.0'
scales = np.arange(1, 128)
sampling_period = 1  # daily? Or 1/12 monthly?

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]+', '_', name)

def generate_wavelet_diagram(df, product, output_path):
    # This function always generates the figure
    # (it's only called if we decide we want to overwrite or create new).
    
    df = df.sort_values('Date').dropna(subset=['Value'])
    time_index = df['Date']
    time_series = df['Value'].values

    fig = plt.figure(figsize=(14, 10))
    fig.suptitle(f"Wavelet Scalogram - Product: {product}", fontsize=16)

    gs = fig.add_gridspec(2, 2, width_ratios=[0.95, 0.05], height_ratios=[1, 3])
    ax_time = fig.add_subplot(gs[0, 0])
    ax_scalogram = fig.add_subplot(gs[1, 0], sharex=ax_time)
    cbar_ax = fig.add_subplot(gs[:, 1])

    # Time series
    ax_time.plot(time_index, time_series, color='blue', linewidth=2)
    ax_time.set(title='Time Series', ylabel='Value')
    ax_time.grid(True)

    # Wavelet transform
    cwt_coeffs, _ = pywt.cwt(time_series, scales, wavelet_name, sampling_period=sampling_period)
    wavelet_power = np.abs(cwt_coeffs)**2
    wavelet_power[wavelet_power == 0] = 1e-6
    log_wavelet_power = np.log10(wavelet_power)

    # Scalogram
    contour = ax_scalogram.contourf(
        time_index,
        np.log2(scales),
        log_wavelet_power,
        100,
        cmap='viridis'
    )
    ax_scalogram.set(title='Scalogram (CWT)', xlabel='Date', ylabel='Scale (log2)')
    ax_scalogram.grid(True)

    fig.colorbar(contour, cax=cbar_ax, label='Log10 Wavelet Power')
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

def generate_diagrams(normalized_folder='normalized_files', diagrams_folder='diagrams'):
    if not os.path.exists(diagrams_folder):
        os.makedirs(diagrams_folder)

    all_files = glob.glob(os.path.join(normalized_folder, '*_normalized.csv'))
    if not all_files:
        print(f"No normalized files found in '{normalized_folder}'.")
        return

    for csv_file in all_files:
        print(f"\nGenerating wavelet diagrams from: {csv_file}")
        df = pd.read_csv(csv_file, parse_dates=['Date'])
        base_name = os.path.splitext(os.path.basename(csv_file))[0]

        for product, sub_df in df.groupby('Product'):
            safe_product = sanitize_filename(product)
            out_name = f"{base_name}__{safe_product}.png"
            out_path = os.path.join(diagrams_folder, out_name)

            # --------------- SKIP CHECK ---------------
            if os.path.exists(out_path):
                print(f"   -> Diagram already exists, skipping: {out_path}")
                continue
            # ------------------------------------------

            # If the file does not exist, generate it
            generate_wavelet_diagram(sub_df, product, out_path)
            print(f"   -> Diagram saved: {out_path}")
