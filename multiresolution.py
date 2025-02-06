import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pywt
from dateutil.parser import parse

def parse_portuguese_date(date_str):
    month_map = {
        'jan.': 'Jan', 'fev.': 'Feb', 'mar.': 'Mar', 'abr.': 'Apr',
        'mai.': 'May', 'jun.': 'Jun', 'jul.': 'Jul', 'ago.': 'Aug',
        'set.': 'Sep', 'out.': 'Oct', 'nov.': 'Nov', 'dez.': 'Dec', 'z.': 'Dec'
    }
    for pt_month, en_month in month_map.items():
        date_str = date_str.replace(pt_month, en_month)
    parts = date_str.split()
    return parse(parts[0] + ' ' + parts[-1]) if len(parts) >= 2 else parse(date_str)

# 1) Load CSV, parse dates, and set 'Date' as index.
data_df = pd.read_csv('pvc_data.csv', dtype=str, encoding='utf-8')
data_df['Date'] = data_df['Date'].apply(parse_portuguese_date)
data_df.set_index('Date', inplace=True)

# 2) Select "actual" columns, clean data, convert decimals and types, and forward-fill missing values.
actual_columns = [col for col in data_df.columns if 'actual' in col.lower()]
actual_data = data_df[actual_columns].replace('', np.nan).apply(lambda s: s.str.replace(',', '.')).astype(float).ffill()

# 3) Normalize each column to [0, 1] and aggregate into a single normalized time series.
normalized_data = (actual_data - actual_data.min()) / (actual_data.max() - actual_data.min())
aggregated_signal = normalized_data.mean(axis=1)
aggregated_signal = (aggregated_signal - aggregated_signal.min()) / (aggregated_signal.max() - aggregated_signal.min())
time_series = aggregated_signal.values
time_index = aggregated_signal.index

# 4) Compute Discrete Wavelet Transform (DWT) up to 8 levels using the 'db4' wavelet.
wavelet_name = 'db4'
max_decomp_level = pywt.dwt_max_level(len(time_series), pywt.Wavelet(wavelet_name).dec_len)
dwt_level = min(8, max_decomp_level)
wavelet_coeffs = pywt.wavedec(time_series, wavelet_name, level=dwt_level)

# 5) Reconstruct detail components by zeroing out all but one set of detail coefficients.
detail_components = [
    pywt.waverec(
        [np.zeros_like(coef) if j != i else wavelet_coeffs[j] for j, coef in enumerate(wavelet_coeffs)],
        wavelet_name
    )[:len(time_series)]
    for i in range(1, len(wavelet_coeffs))
]
detail_components.reverse()  # Reverse so that detail_components[0] is the highest frequency (D1)

# Reconstruct the approximation (low-frequency component).
approximation_coeffs = [wavelet_coeffs[0]] + [np.zeros_like(coef) for coef in wavelet_coeffs[1:]]
approximation_signal = pywt.waverec(approximation_coeffs, wavelet_name)[:len(time_series)]

# 6) Plot detail components, the approximation, and the original aggregated data.
num_plots = dwt_level + 2  # details + approximation + original data
fig, axes = plt.subplots(num_plots, 1, sharex=True, figsize=(10, 2 * num_plots))
fig.suptitle("Wavelet MRA up to 8 Details from pvc_data.csv", fontsize=14)

for i, detail in enumerate(detail_components):
    axes[i].plot(time_index, detail, color='C0', linewidth=1)
    axes[i].set_ylabel(f"$\\tilde{{D}}_{{{i+1}}}$", rotation=0, labelpad=25)
    axes[i].grid(True)

axes[-2].plot(time_index, approximation_signal, 'C1', linewidth=1)
axes[-2].set_ylabel(f"$S_{{{dwt_level}}}$", rotation=0, labelpad=25)
axes[-2].grid(True)

axes[-1].plot(time_index, time_series, 'k', linewidth=1)
axes[-1].set_ylabel("Data", rotation=0, labelpad=25)
axes[-1].grid(True)
axes[-1].set_xlabel("Date")

plt.tight_layout()
plt.show()
