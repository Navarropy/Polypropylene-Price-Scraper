# normalization.py

import os
import glob
import pandas as pd
import numpy as np
from dateutil.parser import parse

def parse_portuguese_date(date_str):
    month_map = {
        'jan.': 'Jan', 'fev.': 'Feb', 'mar.': 'Mar', 'abr.': 'Apr',
        'mai.': 'May', 'jun.': 'Jun', 'jul.': 'Jul', 'ago.': 'Aug',
        'set.': 'Sep', 'out.': 'Oct', 'nov.': 'Nov', 'dez.': 'Dec'
    }
    if not isinstance(date_str, str):
        return pd.NaT
    for pt, en in month_map.items():
        date_str = date_str.replace(pt, en)
    # If your data uses DD/MM/YYYY, set dayfirst=True
    return parse(date_str, dayfirst=True, fuzzy=True)

def parse_kw_date(kw_str):
    # Example: parse "KW 2/2018" => Monday of that ISO week
    try:
        parts = kw_str.strip().split()
        if len(parts) == 2 and parts[0].upper() == 'KW':
            week_part = parts[1]
            if '/' in week_part:
                w, y = week_part.split('/')
                year = int(y)
                week = int(w)
                return pd.to_datetime(f'{year}-W{week}-1', format='%G-W%V-%u')
    except:
        pass
    return None

def load_and_normalize(filepath):
    """
    Reads a CSV/XLS/XLSX, detects the layout (A/B/C), 
    and returns a DF with columns [Date, Product, Value].
    """
    import pandas as pd  # local import to ensure readability

    ext = os.path.splitext(filepath)[1].lower()
    base_name = os.path.splitext(os.path.basename(filepath))[0]

    # 1) Read file
    if ext in ['.xls', '.xlsx']:
        df = pd.read_excel(filepath)
    else:
        df = pd.read_csv(filepath, encoding='utf-8', decimal=',', sep=None, engine='python')

    df.columns = df.columns.map(str)  # ensure string columns
    cols_lower = [c.lower() for c in df.columns]

    # ========== Layout C: exactly 2 cols => [Date, Value] ==========
    if len(df.columns) == 2:
        # rename
        df.rename(columns={df.columns[0]: 'Date', df.columns[1]: 'Value'}, inplace=True)
        df['Date'] = df['Date'].apply(parse_portuguese_date)
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        df['Product'] = base_name

        out_df = df[['Date','Product','Value']].dropna(subset=['Date','Value'])
        out_df['Date'] = pd.to_datetime(out_df['Date'], errors='coerce')
        out_df.dropna(subset=['Date'], inplace=True)
        out_df.sort_values('Date', inplace=True)
        return out_df

    # ========== Layout A: 'Product' column + columns with 'KW' ==========
    if any('product' in c for c in cols_lower) and any('kw' in c for c in cols_lower):
        product_col = [c for c in df.columns if 'product' in c.lower()][0]
        kw_cols = [c for c in df.columns if 'kw' in c.lower()]

        df_melt = df.melt(
            id_vars=product_col,
            value_vars=kw_cols,
            var_name='KW',
            value_name='Value'
        )
        df_melt.rename(columns={product_col: 'Product'}, inplace=True)
        df_melt['Date'] = df_melt['KW'].apply(parse_kw_date)
        df_melt['Value'] = pd.to_numeric(df_melt['Value'], errors='coerce')

        out_df = df_melt[['Date','Product','Value']].dropna(subset=['Date','Product'])
        out_df['Date'] = pd.to_datetime(out_df['Date'], errors='coerce')
        out_df.dropna(subset=['Date'], inplace=True)
        out_df.sort_values('Date', inplace=True)
        return out_df

    # ========== Layout B: 'Date' column + multiple product columns ==========
    if any('date' in c for c in cols_lower):
        date_col = [col for col in df.columns if 'date' in col.lower()][0]
        df[date_col] = df[date_col].apply(parse_portuguese_date)

        df_melt = df.melt(
            id_vars=[date_col],
            var_name='Product',
            value_name='Value'
        )
        df_melt.rename(columns={date_col: 'Date'}, inplace=True)
        df_melt['Value'] = pd.to_numeric(df_melt['Value'], errors='coerce')

        out_df = df_melt[['Date','Product','Value']].dropna(subset=['Date','Value'])
        out_df['Date'] = pd.to_datetime(out_df['Date'], errors='coerce')
        out_df.dropna(subset=['Date'], inplace=True)
        out_df.sort_values('Date', inplace=True)
        return out_df

    raise ValueError(f"Unrecognized layout in file: {filepath}")

def process_data_folder(input_folder='data', output_folder='normalized_files'):
    """
    Normalizes all .csv/.xls/.xlsx in `input_folder`,
    writes results to `output_folder` as '*_normalized.csv'.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    all_files = glob.glob(os.path.join(input_folder, '*.*'))
    for fpath in all_files:
        ext = os.path.splitext(fpath)[1].lower()
        if ext not in ['.csv','.xls','.xlsx']:
            continue

        print(f"\n--- Normalizing: {fpath}")
        try:
            norm_df = load_and_normalize(fpath)
            out_name = os.path.splitext(os.path.basename(fpath))[0] + '_normalized.csv'
            out_path = os.path.join(output_folder, out_name)
            norm_df.to_csv(out_path, index=False)
            print(f"   => Saved normalized: {out_path}")
        except Exception as e:
            print(f"   [Error in {fpath}]: {e}")
