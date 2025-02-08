#!/usr/bin/env python3

import os
import glob
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from prophet import Prophet
from dateutil.parser import parse

def parse_portuguese_date(date_str):
    """
    Convert potential Portuguese abbreviations to English months,
    then parse. Return pd.NaT if invalid.
    """
    month_map = {
        'jan.': 'Jan', 'fev.': 'Feb', 'mar.': 'Mar', 'abr.': 'Apr',
        'mai.': 'May', 'jun.': 'Jun', 'jul.': 'Jul', 'ago.': 'Aug',
        'set.': 'Sep', 'out.': 'Oct', 'nov.': 'Nov', 'dez.': 'Dec',
        'z.': 'Dec'
    }
    if not isinstance(date_str, str):
        return pd.NaT
    for pt, en in month_map.items():
        date_str = date_str.replace(pt, en)
    try:
        # If data is day-first, use dayfirst=True
        return parse(date_str, fuzzy=True)
    except:
        return pd.NaT

def sanitize_filename(name):
    """
    Replace forbidden filename characters (\\, /, :, *, ?, ", <, >, |)
    with underscores so filenames are valid on Windows.
    """
    return re.sub(r'[\\/:*?"<>|]+', '_', str(name))

def run_prophet_on_subdf(
    sub_df, 
    product, 
    base_name, 
    out_folder, 
    periods=12
):
    """
    Fit a Prophet model with:
      - yearly_seasonality=True (explicit annual cycles)
      - weekly_seasonality=False (disabled)
      - custom monthly seasonality
      - bigger prior scales for more flexibility
    """
    sub_df = sub_df.dropna(subset=['Value']).sort_values('Date')
    if sub_df.empty:
        return

    df_forecast = sub_df[['Date','Value']].copy()
    df_forecast.rename(columns={'Date':'ds','Value':'y'}, inplace=True)
    df_forecast['ds'] = pd.to_datetime(df_forecast['ds'])

    # 1) Initialize Prophet with yearly seasonality ON, weekly OFF
    #    and heavier prior scales for more flexible fits
    model = Prophet(
        weekly_seasonality=False,
        yearly_seasonality=True,
        seasonality_prior_scale=15,  # default=10
        changepoint_prior_scale=0.5  # default=0.05
    )

    # 2) Add a custom monthly seasonality 
    model.add_seasonality(
        name='monthly',
        period=30.5,
        fourier_order=5,
        prior_scale=10
    )

    # 3) Fit the model
    model.fit(df_forecast)

    # 4) Make future dataframe (12 months by default)
    future = model.make_future_dataframe(periods=periods, freq='MS')
    forecast = model.predict(future)

    # 5) Plot forecast
    fig1 = model.plot(forecast)
    fig1.suptitle(f"Prophet Forecast - Product: {product}", fontsize=14)
    fig1.subplots_adjust(top=0.88)  # Ensure title not clipped

    safe_product = sanitize_filename(product)
    out_name_main = f"{base_name}__{safe_product}__forecast.png"
    out_path_main = os.path.join(out_folder, out_name_main)
    fig1.savefig(out_path_main, dpi=150)
    plt.close(fig1)
    print(f"   -> Saved forecast: {out_path_main}")

    # 6) Plot components (trend, yearly, monthly, etc.)
    fig2 = model.plot_components(forecast)
    fig2.suptitle(f"Forecast Components - Product: {product}", fontsize=14)
    fig2.subplots_adjust(top=0.88)

    out_name_comp = f"{base_name}__{safe_product}__components.png"
    out_path_comp = os.path.join(out_folder, out_name_comp)
    fig2.savefig(out_path_comp, dpi=150)
    plt.close(fig2)
    print(f"   -> Saved components: {out_path_comp}")

def generate_forecasts(
    normalized_folder='normalized_files',
    output_folder='regression_plots',
    forecast_periods=12
):
    """
    Reads each *_normalized.csv in `normalized_folder`,
    expects [Date, Product, Value].
    For each product, calls run_prophet_on_subdf(...) with 
    yearly seasonality, monthly, & tuned priors.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    all_files = glob.glob(os.path.join(normalized_folder, '*_normalized.csv'))
    if not all_files:
        print(f"No normalized files found in '{normalized_folder}'.")
        return

    for csv_file in all_files:
        base_name = os.path.splitext(os.path.basename(csv_file))[0]
        print(f"\n[Prophet] Processing file: {csv_file}")

        df = pd.read_csv(csv_file, dtype=str)
        df.columns = df.columns.str.strip().str.capitalize()

        needed = {'Date','Product','Value'}
        if set(df.columns) != needed:
            print("   -> Skipping (not 3-col [Date, Product, Value])")
            continue

        # parse date, numeric value
        df['Date'] = df['Date'].apply(parse_portuguese_date)
        df['Value'] = df['Value'].str.replace(',', '.')
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        df.dropna(subset=['Date'], inplace=True)

        # group by product
        for product, sub_df in df.groupby('Product'):
            run_prophet_on_subdf(
                sub_df=sub_df,
                product=product,
                base_name=base_name,
                out_folder=output_folder,
                periods=forecast_periods
            )

if __name__ == '__main__':
    generate_forecasts(
        normalized_folder='normalized_files',
        output_folder='regression_plots',
        forecast_periods=12
    )
    print("\nForecasting complete!")
