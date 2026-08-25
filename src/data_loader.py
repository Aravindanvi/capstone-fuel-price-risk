import pandas as pd
import numpy as np
from datetime import datetime
from fredapi import Fred
import requests
import os
import warnings
warnings.filterwarnings('ignore')

class DataLoader:
    """
    A class to load economic and energy data from FRED and EIA APIs.
    """

    def __init__(self):
        """Initialize the DataLoader with API credentials."""
        self.fred = Fred(api_key=os.environ.get('FRED_API_KEY'))
        self.eia_api_key = os.environ.get('EIA_API_KEY')

    def load_fred_data(self):
        """
        Load key economic and energy price data from FRED.

        Returns:
            dict: Dictionary of pandas Series for each FRED series
        """
        series_dict = {
            'WTI': 'DCOILWTICO',           # WTI Crude Oil Price
            'BRENT': 'DCOILBRENTEU',       # Brent Crude Oil Price
            'RBOB': 'GASREGCOVW',          # RBOB Gasoline Price
            'HEATING_OIL': 'DHOILNYH',     # Heating Oil Price
            'VIX': 'VIXCLS',               # VIX Volatility Index
            'DXY': 'DTWEXBGS',             # US Dollar Index
            'T10Y': 'DGS10',               # 10-Year Treasury Yield
            'CPI': 'CPIAUCSL'              # Consumer Price Index
        }

        data = {}
        for name, series_id in series_dict.items():
            try:
                data[name] = self.fred.get_series(series_id)
                print(f"  ✅ {name}: {len(data[name])} observations")
            except Exception as e:
                print(f"  ❌ Error loading {name}: {e}")
                data[name] = pd.Series()
        return data

    def load_eia_data(self):
        """
        Load energy data from the EIA API.

        Returns:
            dict: Dictionary of pandas Series for each EIA series
        """
        data = {}
        series_list = {
            'refinery_utilization': 'PET.WCRPUUS2.W',
            'crude_inventory': 'PET.WCRSTUS1.W',
            'gasoline_inventory': 'PET.WGSTUS1.W',
            'distillate_inventory': 'PET.WDSTUS1.W'
        }

        for name, series_id in series_list.items():
            try:
                url = f"http://api.eia.gov/series/?api_key={self.eia_api_key}&series_id={series_id}"
                response = requests.get(url)
                if response.status_code == 200:
                    data[name] = pd.Series(
                        {datetime.strptime(d[0], '%Y-%m-%d'): float(d[1])
                         for d in response.json()['series'][0]['data']}
                    ).sort_index()
                    print(f"  ✅ {name}: {len(data[name])} observations")
                else:
                    print(f"  ❌ Error {response.status_code} for {name}")
                    data[name] = pd.Series()
            except Exception as e:
                print(f"  ❌ Error loading {name}: {e}")
                data[name] = pd.Series()
        return data

    def load_all_data(self):
        """
        Load and combine all data sources.

        Returns:
            dict: Dictionary containing FRED and EIA data
        """
        print("============================================================")
        print("🚀 Starting Data Collection")
        print("============================================================")

        print("📊 Fetching FRED data...")
        fred_data = self.load_fred_data()

        print("📊 Fetching EIA data...")
        eia_data = self.load_eia_data()

        # Combine data - only include EIA data that loaded successfully
        all_data = {**fred_data}

        # Only add EIA data if it's not empty
        for name, series in eia_data.items():
            if not series.empty:
                all_data[name] = series

        # Create DataFrame
        df = pd.DataFrame(all_data)

        # Clean data
        df = df.dropna(how='all')

        # Ensure index is DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except:
                # If conversion fails, try to get dates from first series
                for col in df.columns:
                    if isinstance(df[col].index, pd.DatetimeIndex):
                        df.index = df[col].index
                        break

        # Remove timezone info if present
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        # Forward fill for daily/weekly alignment
        df = df.fillna(method='ffill')

        print(f"\n✅ Data loaded: {df.shape[0]} rows, {df.shape[1]} columns")

        return {'fred': df, 'eia': eia_data}
