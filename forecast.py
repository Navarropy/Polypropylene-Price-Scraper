import pandas as pd
import numpy as np
from dateutil.parser import parse
import matplotlib.pyplot as plt

# Prophet
from prophet import Prophet

def parse_portuguese_date(date_str):
    month_translation = {
        'jan.': 'Jan', 'fev.': 'Feb', 'mar.': 'Mar', 'abr.': 'Apr',
        'mai.': 'May', 'jun.': 'Jun', 'jul.': 'Jul', 'ago.': 'Aug',
        'set.': 'Sep', 'out.': 'Oct', 'nov.': 'Nov', 'dez.': 'Dec', 'z.': 'Dec'
    }
    for pt, en in month_translation.items():
        date_str = date_str.replace(pt, en)
    parts = date_str.split()
    if len(parts) >= 2:
        return parse(parts[0] + ' ' + parts[-1])
    return parse(date_str)

# 1) Read and parse CSV
df = pd.read_csv("pvc_data.csv", dtype=str, encoding="utf-8")
df["Date"] = df["Date"].apply(parse_portuguese_date)
df.set_index("Date", inplace=True)

# 2) Collect “actual” columns, convert comma decimals to dot decimals, forward fill, etc.
actual_cols = [c for c in df.columns if "actual" in c.lower()]
df_actual = df[actual_cols].replace("", np.nan)
df_actual = df_actual.apply(lambda s: s.str.replace(",", ".")).astype(float).ffill()

# 3) Min–max normalize each column, then average across them
df_norm = (df_actual - df_actual.min()) / (df_actual.max() - df_actual.min())
aggregated = df_norm.mean(axis=1)
aggregated = (aggregated - aggregated.min()) / (aggregated.max() - aggregated.min())

# Prepare for Prophet (column names: ds, y)
df_forecast = aggregated.reset_index()
df_forecast.columns = ["ds", "y"]
df_forecast["ds"] = pd.to_datetime(df_forecast["ds"])

# 4) Train Prophet on the historical data
model = Prophet()
model.fit(df_forecast)

# 5) Forecast 12 future periods (months)
future = model.make_future_dataframe(periods=12, freq="MS")  
# "MS" = Month Start; pick your frequency as needed

forecast = model.predict(future)

# 6) Plot the forecast
model.plot(forecast)
plt.title("Prophet Forecast of pvc_data.csv (Aggregated Actuals)")
plt.show()

# Optionally: plot forecast components (trend, yearly, weekly, etc.)
model.plot_components(forecast)
plt.show()

print("\nForecast tail:")
print(forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(12))
