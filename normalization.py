#!/usr/bin/env python3
# Tells the operating system to run this script with Python 3.

import os                    # Provides functions for interacting with the operating system (e.g., file paths, directory operations).
import re                    # Provides regular expression operations for pattern matching and string manipulation.
import pandas as pd          # Used for data manipulation and analysis via DataFrames.
from dateutil.parser import parse  # Converts date strings into Python datetime objects.
from itertools import dropwhile  # Provides a function to drop items from an iterable based on a condition.
from pathlib import Path     # Provides an object-oriented interface for file system paths.

# ---------------------------------------------------------------------
# Function: parse_portuguese_date
# ---------------------------------------------------------------------
def parse_portuguese_date(date_str):
    """
    Converts a date string that might use Portuguese month abbreviations into a standard datetime object.
    If the input is not a string or parsing fails, it returns pd.NaT (Not a Time).
    
    Parameters:
      date_str (str): A date represented as a string.
      
    Returns:
      datetime or pd.NaT: The parsed date or a 'Not a Time' value.
    """
    if not isinstance(date_str, str):
        # If the provided date_str is not a string, return pd.NaT to indicate an invalid date.
        return pd.NaT
    # Create a mapping of Portuguese month abbreviations to their English equivalents.
    month_map = {
        'jan.': 'Jan', 'fev.': 'Feb', 'mar.': 'Mar', 'abr.': 'Apr',
        'mai.': 'May', 'jun.': 'Jun', 'jul.': 'Jul', 'ago.': 'Aug',
        'set.': 'Sep', 'out.': 'Oct', 'nov.': 'Nov', 'dez.': 'Dec'
    }
    # Loop through each Portuguese abbreviation and replace it with the English abbreviation.
    for pt, en in month_map.items():
        date_str = date_str.replace(pt, en)
    try:
        # Parse the date string into a datetime object.
        # 'dayfirst=True' tells the parser to interpret the first number as the day.
        # 'fuzzy=True' allows the parser to ignore unknown tokens.
        return parse(date_str, dayfirst=True, fuzzy=True)
    except:
        # If parsing fails, return pd.NaT.
        return pd.NaT

# ---------------------------------------------------------------------
# Function: parse_kw_date
# ---------------------------------------------------------------------
def parse_kw_date(kw_str):
    """
    Parses a week string in the format 'KW X/YYYY' into a datetime object representing the start of that ISO week.
    
    Parameters:
      kw_str (str): A string representing the week (e.g., "KW 2/2018").
      
    Returns:
      datetime or pd.NaT: The parsed datetime for the week or pd.NaT if parsing fails.
    """
    # Use a regular expression to match the format "KW <number>/<year>".
    if match := re.match(r'KW\s*(\d+)/(\d+)', str(kw_str).strip(), re.I):
        # Construct a datetime using ISO week format: year, week number, and weekday (1 = Monday).
        return pd.to_datetime(f"{match[2]}-W{match[1]}-1", format='%G-W%V-%u')
    # If no match, return pd.NaT.
    return pd.NaT

# ---------------------------------------------------------------------
# Function: clean_numeric
# ---------------------------------------------------------------------
def clean_numeric(val):
    """
    Converts a value to a numeric type.
    It first converts the value to a string, replaces thousands separators ('.') with nothing,
    replaces commas with periods (to standardize decimals), and removes any dashes.
    
    Parameters:
      val: A value that is expected to represent a number.
      
    Returns:
      numeric: The value converted to a number (or NaN if conversion fails).
    """
    return pd.to_numeric(
        str(val).replace('.', '').replace(',', '.').replace('–', ''),
        errors='coerce'  # If conversion fails, returns NaN.
    )

# ---------------------------------------------------------------------
# Function: trim_row
# ---------------------------------------------------------------------
def trim_row(row):
    """
    Removes trailing empty cells from a list representing a row.
    It uses dropwhile to remove values from the end that are None or empty (after stripping).
    
    Parameters:
      row (list): A list of cell values.
      
    Returns:
      list: The trimmed row with trailing empty cells removed.
    """
    # 'dropwhile' iterates from the end (using reversed(row)) until the condition is false.
    trimmed = list(dropwhile(lambda v: v is None or (isinstance(v, str) and not v.strip()),
                              reversed(row)))
    # Reverse again to restore the original order.
    return list(reversed(trimmed))

# ---------------------------------------------------------------------
# Function: process_quarters
# ---------------------------------------------------------------------
def process_quarters(df, product_name):
    """
    Processes a DataFrame that contains quarterly data.
    
    Expects a DataFrame where the first column is a year and the remaining columns are quarter values.
    It "melts" (un-pivots) the DataFrame, extracts the quarter number, maps it to a representative month,
    and constructs a datetime (assuming the day is 15 for each quarter).
    
    Parameters:
      df (DataFrame): The input DataFrame containing year and quarter data.
      product_name (str): The product name to assign to all rows.
      
    Returns:
      DataFrame: A normalized DataFrame with columns: Date, Product, and Value.
    """
    # Rename the first column to "Year" for clarity.
    df = df.rename(columns={df.columns[0]: 'Year'})
    # "Melt" the DataFrame: convert columns (quarters) into rows with a 'Quarter' column and a 'Value' column.
    melted = df.melt(id_vars='Year', value_name='Value', var_name='Quarter')
    # Extract the quarter number from the 'Quarter' column safely.
    q_extract = melted['Quarter'].astype(str).str.extract(r'(\d+)')[0]
    # Create a boolean mask for valid quarter numbers (non-empty and non-null).
    valid = q_extract.notna() & q_extract.str.strip().ne('')
    # Filter the melted DataFrame to keep only rows with a valid quarter number.
    melted = melted[valid].copy()
    # Convert the extracted quarter numbers to numeric values.
    q_num = pd.to_numeric(q_extract[valid], errors='coerce')
    # Define a mapping from quarter number to a representative month.
    # Q1 -> March (03), Q2 -> June (06), Q3 -> September (09), Q4 -> December (12)
    month_map = {1: '03', 2: '06', 3: '09', 4: '12'}
    # Map the numeric quarter to the corresponding month using the mapping.
    month = q_num.map(month_map)
    # Construct a new 'Date' column by combining the Year, mapped Month, and a fixed day (15).
    melted['Date'] = pd.to_datetime(
        melted['Year'].astype(str) + '-' + month.fillna('03') + '-15',
        errors='coerce'
    )
    # Assign the product name to every row, clean the numeric values, drop rows with missing Date or Value,
    # and sort the DataFrame by Date. Then, select only the desired columns.
    return (melted.assign(Product=product_name,
                          Value=lambda d: d['Value'].apply(clean_numeric))
                  .dropna(subset=['Date', 'Value'])
                  .sort_values('Date')[['Date', 'Product', 'Value']])

# ---------------------------------------------------------------------
# Function: load_normalized
# ---------------------------------------------------------------------
def load_normalized(filepath):
    """
    Loads a file (Excel or CSV) and processes it to produce a normalized DataFrame with columns:
    Date, Product, and Value.
    
    Supports three layouts:
      1. Date-based layout: If one column is named "Date" (case-insensitive), it is processed accordingly.
      2. Week-based (KW) layout: If the first column is "Product" and other headers contain "kw",
         it processes weekly data by converting week strings to dates.
      3. Multi-block or simple Year/Quarter layout: Otherwise, the file is assumed to be in a multi-block format
         or a simple table with Year and Quarter columns.
    
    Parameters:
      filepath (str): The path to the input file.
      
    Returns:
      DataFrame: A normalized DataFrame with columns Date, Product, and Value.
      
    Raises:
      ValueError: If the file format is unsupported.
    """
    # Create a Path object for the file.
    path = Path(filepath)
    # Read the file based on its extension: Excel files or CSV files.
    df = (pd.read_excel(path) if path.suffix in ['.xls', '.xlsx']
          else pd.read_csv(path, decimal=','))
    # Standardize column names to lower-case and strip extra spaces.
    cols_lower = [str(c).lower().strip() for c in df.columns]
    
    # Layout 1: Date-based layout.
    if 'date' in cols_lower:
        # Find the column that is identified as "date" (case-insensitive).
        date_col = df.columns[cols_lower.index('date')]
        # Convert the date column using our custom parser, melt the DataFrame to long format,
        # clean numeric values, drop rows with missing dates or values, rename the date column to "Date",
        # and sort the DataFrame by Date.
        return (df.assign(**{date_col: df[date_col].apply(parse_portuguese_date)})
                .melt(id_vars=date_col, var_name='Product', value_name='Value')
                .assign(Value=lambda d: d['Value'].apply(clean_numeric))
                .dropna(subset=[date_col, 'Value'])
                .rename(columns={date_col: 'Date'})
                .sort_values('Date'))
    
    # Layout 2: Week-based (KW) layout.
    elif cols_lower[0] == 'product' and any('kw' in c for c in cols_lower[1:]):
        # Melt the DataFrame with 'Product' as the identifier, convert week strings to dates,
        # clean numeric values, drop rows with missing dates or values, and sort by Date.
        return (df.melt(id_vars='Product', var_name='Week', value_name='Value')
                .assign(Date=lambda d: d['Week'].apply(parse_kw_date),
                        Value=lambda d: d['Value'].apply(clean_numeric))
                .dropna(subset=['Date', 'Value'])
                .sort_values('Date')[['Date', 'Product', 'Value']])
    
    # Layout 3: Multi-block or simple Year/Quarter layout.
    try:
        # Check if the first column header does not start with "20" or "19" (indicating a year).
        if not any(str(df.columns[0]).strip().startswith(s) for s in ('20', '19')):
            # Re-read the file without headers since it's assumed to be in a multi-block format.
            df = (pd.read_excel(path, header=None)
                  if path.suffix in ['.xls', '.xlsx']
                  else pd.read_csv(path, header=None))
            # Convert each row to a list with trailing empty cells removed.
            rows = [trim_row(r) for r in df.values.tolist()]
            normalized_blocks = []  # To store processed data blocks.
            i = 0
            # Loop through the rows.
            while i < len(rows):
                # Skip blank rows.
                if not rows[i]:
                    i += 1
                    continue
                # Determine the product title from the row if the first cell is not numeric.
                if str(rows[i][0]).strip() and not str(rows[i][0]).replace('.', '').isdigit():
                    product = str(rows[i][0]).strip()
                    i += 1
                else:
                    # If not, use the file's base name as the product name.
                    product = path.stem
                # Skip any blank rows that follow.
                while i < len(rows) and not rows[i]:
                    i += 1
                if i >= len(rows):
                    break
                # The next row is expected to be the header row.
                header = rows[i]
                # If the header's first cell is empty, set it to "Year".
                if not str(header[0]).strip():
                    header[0] = "Year"
                i += 1
                # Collect data rows where the first cell is numeric (indicating a year).
                data_rows = []
                while i < len(rows) and rows[i] and str(rows[i][0]).replace('.', '').isdigit():
                    data_rows.append(rows[i])
                    i += 1
                # If data rows were collected, convert them into a DataFrame and process the quarters.
                if data_rows:
                    block_df = pd.DataFrame(data_rows, columns=header)
                    normalized_blocks.append(process_quarters(block_df, product))
            # If any blocks were processed, concatenate them into one DataFrame.
            if normalized_blocks:
                return pd.concat(normalized_blocks, ignore_index=True)
            else:
                # Fallback: process the original DataFrame as a simple Year/Quarter layout.
                return process_quarters(df, path.stem)
        else:
            # If the first column header starts with a year, assume a simple Year/Quarter table.
            return process_quarters(df, path.stem)
    
    except Exception as e:
        # If any error occurs during processing, raise a ValueError with details.
        raise ValueError(f"Unsupported file format: {filepath}. Error: {e}")

# ---------------------------------------------------------------------
# Function: process_folder
# ---------------------------------------------------------------------
def process_folder(input='data', output='normalized'):
    """
    Processes all files (Excel or CSV) in the input folder and writes normalized CSV files to the output folder.
    
    Each file is read and normalized to have three columns: Date, Product, and Value.
    The normalized file is saved with a suffix "_normalized.csv".
    
    Parameters:
      input (str): The folder containing input files.
      output (str): The folder where normalized files will be saved.
    """
    # Create a Path object for the output folder and make the folder if it doesn't exist.
    output_dir = Path(output)
    output_dir.mkdir(exist_ok=True)
    
    # Loop through all files in the input folder.
    for file in Path(input).glob('*.*'):
        # Process only files with extensions CSV, XLS, or XLSX.
        if file.suffix.lower() not in {'.csv', '.xls', '.xlsx'}:
            continue
        try:
            # Load and normalize the file, then save it as a new CSV file in the output folder.
            load_normalized(file).to_csv(output_dir / f"{file.stem}_normalized.csv", index=False)
            print(f"Processed: {file.name}")
        except Exception as e:
            # If an error occurs, print an error message.
            print(f"Error processing {file.name}: {str(e)}")
