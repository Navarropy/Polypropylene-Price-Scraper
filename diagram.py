import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pywt
from dateutil.parser import parse

def parse_portuguese_date(date_str):
    # Replace Portuguese month abbreviations with English equivalents
    month_map = {
        'jan.': 'Jan', 'fev.': 'Feb', 'mar.': 'Mar', 'abr.': 'Apr',
        'mai.': 'May', 'jun.': 'Jun', 'jul.': 'Jul', 'ago.': 'Aug',
        'set.': 'Sep', 'out.': 'Oct', 'nov.': 'Nov', 'dez.': 'Dec', 'z.': 'Dec'
    }
    for pt_month, en_month in month_map.items():
        date_str = date_str.replace(pt_month, en_month)
    date_parts = date_str.split()
    return parse(date_parts[0] + ' ' + date_parts[-1])

# Load the CSV data and set the 'Date' column as the index
df = pd.read_csv('pvc_data.csv', parse_dates=['Date'], date_parser=parse_portuguese_date,
                 decimal=',', encoding='utf-8').set_index('Date')

# Select columns containing 'actual', clean, and convert to float
actual_columns = [col for col in df.columns if 'actual' in col]
actual_data = df[actual_columns].replace('', np.nan).ffill().astype(float)

# Normalize each column to the [0, 1] range
normalized_data = (actual_data - actual_data.min()) / (actual_data.max() - actual_data.min())

# Compute the aggregated signal as the average across all regions, then re-normalize
aggregated_signal = normalized_data.mean(axis=1)
aggregated_signal = (aggregated_signal - aggregated_signal.min()) / (aggregated_signal.max() - aggregated_signal.min())

# Extract the aggregated time series and its time index
aggregated_time_series = aggregated_signal.values
time_index = aggregated_signal.index

# Set Continuous Wavelet Transform parameters and compute the CWT
wavelet_name = 'cmor1.5-1.0'      # Complex Morlet wavelet
scales = np.arange(1, 128)        # Scale range
sampling_period = 1/12            # Monthly data (in years)
cwt_coefficients, _ = pywt.cwt(aggregated_time_series, scales, wavelet_name, sampling_period=sampling_period)
wavelet_power = np.abs(cwt_coefficients)**2
wavelet_power[wavelet_power == 0] = 1e-6  # Prevent log(0)
log_wavelet_power = np.log10(wavelet_power)

# Create plots: time series (top) and scalogram (bottom)
fig, (ax_time, ax_scalogram) = plt.subplots(2, 1, figsize=(14, 10), sharex=True,
                                            gridspec_kw={'height_ratios': [1, 3]})
ax_time.plot(time_index, aggregated_time_series, color='blue', linewidth=2)
ax_time.set(title='Aggregated Normalized Signal in Time', ylabel='Normalized Value', ylim=(0, 1))
ax_time.grid(True)

contour = ax_scalogram.contourf(time_index, np.log2(scales), log_wavelet_power, 100, cmap='viridis')
ax_scalogram.set(title='Scalogram (Continuous Wavelet Transform)', xlabel='Date', ylabel='Scale (log2)')
plt.colorbar(contour, ax=ax_scalogram, label='Log10 Wavelet Power')

plt.tight_layout()
plt.show()
