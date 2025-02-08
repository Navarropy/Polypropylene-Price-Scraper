# mra.py

import os
import glob
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pywt
from dateutil.parser import parse

def parse_portuguese_date(date_str):
    """
    Safely parse potential Portuguese month abbreviations into English, 
    then parse with dateutil. If invalid, return NaT.
    """
    month_map = {
        'jan.': 'Jan', 'fev.': 'Feb', 'mar.': 'Mar', 'abr.': 'Apr',
        'mai.': 'May', 'jun.': 'Jun', 'jul.': 'Jul', 'ago.': 'Aug',
        'set.': 'Sep', 'out.': 'Oct', 'nov.': 'Nov', 'dez.': 'Dec'
    }
    if not isinstance(date_str, str):
        return pd.NaT

    for pt, en in month_map.items():
        date_str = date_str.replace(pt, en)
    try:
        # If your data is day-first, set dayfirst=True
        return parse(date_str, dayfirst=True, fuzzy=True)
    except:
        return pd.NaT

def sanitize_filename(name):
    """
    Replace forbidden filename characters with underscores,
    so Windows won't complain about invalid paths.
    """
    return re.sub(r'[\\/:*?"<>|]+', '_', name)

def do_mra_on_subdf(sub_df, base_name, product, output_folder):
    """
    Perform the DWT-based multi-resolution analysis on 'Value' vs. 'Date'
    for a single product's subset (sub_df).
    """
    # Sort by Date, drop missing Value
    sub_df = sub_df.dropna(subset=['Value']).sort_values('Date')
    time_series = sub_df['Value'].values
    time_index = sub_df['Date']

    # If there's no data after dropna, skip
    if len(time_series) == 0:
        return

    # Normalize [0,1]
    min_val, max_val = time_series.min(), time_series.max()
    if max_val != min_val:
        norm_series = (time_series - min_val) / (max_val - min_val)
    else:
        norm_series = time_series - min_val

    # Perform wavelet decomposition with db4, up to 8 levels (or max possible)
    wavelet_name = 'db4'
    max_decomp_level = pywt.dwt_max_level(len(norm_series),
                                          pywt.Wavelet(wavelet_name).dec_len)
    dwt_level = min(8, max_decomp_level)
    wavelet_coeffs = pywt.wavedec(norm_series, wavelet_name, level=dwt_level)

    # Reconstruct detail components
    detail_components = []
    for i in range(1, len(wavelet_coeffs)):
        coeffs_copy = []
        for j, c in enumerate(wavelet_coeffs):
            if j == i:
                coeffs_copy.append(c)
            else:
                coeffs_copy.append(np.zeros_like(c))
        detail_signal = pywt.waverec(coeffs_copy, wavelet_name)[:len(norm_series)]
        detail_components.append(detail_signal)
    detail_components.reverse()

    # Reconstruct approximation
    approx_coeffs = [wavelet_coeffs[0]] + [np.zeros_like(c) for c in wavelet_coeffs[1:]]
    approximation_signal = pywt.waverec(approx_coeffs, wavelet_name)[:len(norm_series)]

    # Plot the MRA: detail components + approximation + original
    num_plots = dwt_level + 2
    fig, axes = plt.subplots(num_plots, 1, sharex=True, figsize=(10, 2 * num_plots))
    fig.suptitle(f"MRA (db4)\nFile: {base_name}, Product: {product}", fontsize=14)

    # detail components
    for idx, detail in enumerate(detail_components):
        axes[idx].plot(time_index, detail, 'C0', linewidth=1)
        axes[idx].set_ylabel(f"D{idx+1}", rotation=0, labelpad=25)
        axes[idx].grid(True)

    # approximation
    axes[-2].plot(time_index, approximation_signal, 'C1', linewidth=1)
    axes[-2].set_ylabel(f"S{dwt_level}", rotation=0, labelpad=25)
    axes[-2].grid(True)

    # original (normalized) data
    axes[-1].plot(time_index, norm_series, 'k', linewidth=1)
    axes[-1].set_ylabel("Data", rotation=0, labelpad=25)
    axes[-1].grid(True)
    axes[-1].set_xlabel("Date")

    plt.tight_layout()

    # Save figure
    safe_product = sanitize_filename(product)
    out_name = f"{base_name}__MRA__{safe_product}.png"
    out_path = os.path.join(output_folder, out_name)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"   -> MRA saved: {out_path}")


def generate_mra_all_files(data_folder='normalized_files', output_folder='mra_diagrams'):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    all_files = glob.glob(os.path.join(data_folder, '*.*'))
    for fpath in all_files:
        ext = os.path.splitext(fpath)[1].lower()
        if ext not in ['.csv','.xls','.xlsx']:
            continue

        base_name = os.path.splitext(os.path.basename(fpath))[0]

        if ext in ['.xls','.xlsx']:
            df = pd.read_excel(fpath, dtype=str)
        else:
            df = pd.read_csv(fpath, dtype=str, encoding='utf-8')
        
        # Convert all column names -> lower case, strip spaces
        df.columns = df.columns.str.strip().str.lower()
        
        colset = set(df.columns)
        needed = {'date','product','value'}
        
        if len(df.columns) == 3 and colset == needed:
            print(f"\n[MRA] 3-col file: {fpath}")
            
            # parse date, numeric value
            # rename back to standard form for clarity
            df.rename(columns={'date':'Date','product':'Product','value':'Value'}, inplace=True)
            
            df['Date'] = df['Date'].apply(parse_portuguese_date)
            df['Value'] = df['Value'].str.replace(',', '.')
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
            df.dropna(subset=['Date'], inplace=True)
            df.sort_values('Date', inplace=True)

            # group by Product
            for product, sub_df in df.groupby('Product'):
                do_mra_on_subdf(sub_df, base_name, product, output_folder)

        else:
            # skip or fallback to wide format approach
            print(f"\n[MRA] Skipping: {fpath}")
            print("Columns are:", df.columns.tolist())