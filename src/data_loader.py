"""
Data Loader Module for Capstone Project
Extracts data from FRED, EIA, and other sources

Walsh College - QM640 Data Analytics Capstone
Author: [Your Name]
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

# Load environment variables from .env file if present
load_dotenv()

class DataLoader:
    """
    Class to handle data extraction from various sources
    """
    
    def __init__(self, start_date='2015-01-01', end_date='2025-12-31'):
        """
        Initialize DataLoader with date range
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
        """
        self.start_date = start_date
        self.end_date = end_date
        
        # Try to get API keys from environment or Colab secrets
        try:
            from google.colab import userdata
            self.fred_api_key = userdata.get('FRED_API_KEY')
            self.eia_api_key = userdata.get('EIA_API_KEY')
            print("✅ API keys loaded from Colab secrets")
        except:
            self.fred_api_key = os.getenv('FRED_API_KEY')
            self.eia_api_key = os.getenv('EIA_API_KEY')
            if self.fred_api_key:
                print("✅ API keys loaded from .env file")
        
        # FRED series IDs (these are the codes for each economic indicator)
        self.fred_series = {
            'WTI': 'DCOILWTICO',           # WTI Crude Oil
            'BRENT': 'DCOILBRENTEU',       # Brent Crude Oil
            'RBOB': 'GASREGW',             # RBOB Gasoline
            'HEATING_OIL': 'DHOILNYH',     # Heating Oil/ULSD
            'VIX': 'VIXCLS',               # CBOE Volatility Index
            'DXY': 'DTWEXBGS',             # US Dollar Index
            'T10Y': 'DGS10',               # 10-Year Treasury Yield
            'CPI': 'CPIAUCSL',             # Consumer Price Index
        }
        
        # UPDATED EIA series IDs (Weekly Petroleum Status Report)
        # Using the correct EIA API v2 endpoints
        self.eia_series = {
            'refinery_utilization': 'PET.WIRTU_RAIL_EPC0_RAIL_Y04_NUS.W',
            'crude_inventory': 'PET.WCESTUS1.W',
            'gasoline_inventory': 'PET.WGASUS1.W',
            'distillate_inventory': 'PET.WDISTUS1.W',
        }
    
    def fetch_fred_data(self):
        """
        Fetch data from FRED API
        
        Returns:
            pd.DataFrame: DataFrame with all FRED series
        """
        try:
            from fredapi import Fred
            fred = Fred(api_key=self.fred_api_key)
            
            print("📊 Fetching FRED data...")
            data = {}
            
            for name, series_id in self.fred_series.items():
                try:
                    series = fred.get_series(
                        series_id, 
                        observation_start=self.start_date,
                        observation_end=self.end_date
                    )
                    data[name] = series
                    print(f"  ✅ {name}: {len(series)} observations")
                except Exception as e:
                    print(f"  ⚠️ Error fetching {name}: {e}")
                    data[name] = None
            
            # Create DataFrame
            df_fred = pd.DataFrame(data)
            df_fred.index.name = 'Date'
            
            return df_fred
            
        except ImportError:
            print("⚠️  fredapi not installed. Please install: pip install fredapi")
            return None
        except Exception as e:
            print(f"❌ Error fetching FRED data: {e}")
            return None
    
    def fetch_eia_data(self):
        """
        Fetch data from EIA API using the correct v2 endpoints
        Returns:
            pd.DataFrame: DataFrame with all EIA series
        """
        try:
            import requests
            
            print("📊 Fetching EIA data...")
            base_url = "https://api.eia.gov/v2"
            
            # UPDATED: Correct EIA API v2 endpoints
            # These are the correct series IDs for weekly petroleum data
            eia_series_corrected = {
                'refinery_utilization': 'PET.WIRTU_RAIL_EPC0_RAIL_Y04_NUS.W',
                'crude_inventory': 'PET.WCESTUS1.W',
                'gasoline_inventory': 'PET.WGASUS1.W',
                'distillate_inventory': 'PET.WDISTUS1.W',
            }
            
            data = {}
            
            for name, series_id in eia_series_corrected.items():
                try:
                    # EIA API v2 format
                    url = f"{base_url}/petroleum/ste/wpsr/data/"
                    params = {
                        'api_key': self.eia_api_key,
                        'frequency': 'weekly',
                        'data[0]': 'value',
                        'facets[series][0]': series_id.split('.')[-1] if '.' in series_id else series_id,
                        'start': self.start_date,
                        'end': self.end_date,
                        'sort[0][column]': 'period',
                        'sort[0][direction]': 'asc',
                        'offset': 0,
                        'length': 5000
                    }
                    
                    response = requests.get(url, params=params)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Parse the response
                        if 'response' in result and 'data' in result['response']:
                            records = result['response']['data']
                            if records:
                                # Extract dates and values
                                dates = []
                                values = []
                                for record in records:
                                    if 'period' in record and 'value' in record:
                                        try:
                                            date_val = pd.to_datetime(record['period'])
                                            val = float(record['value']) if record['value'] is not None else np.nan
                                            dates.append(date_val)
                                            values.append(val)
                                        except:
                                            continue
                                
                                if dates:
                                    series_df = pd.DataFrame({
                                        'Date': dates,
                                        name: values
                                    })
                                    series_df.set_index('Date', inplace=True)
                                    # Remove duplicates by aggregating
                                    series_df = series_df.groupby(level=0).first()
                                    data[name] = series_df
                                    print(f"  ✅ {name}: {len(series_df)} observations")
                                else:
                                    print(f"  ⚠️ No valid data for {name}")
                                    data[name] = None
                            else:
                                print(f"  ⚠️ No records for {name}")
                                data[name] = None
                        else:
                            print(f"  ⚠️ Unexpected response format for {name}")
                            data[name] = None
                    else:
                        print(f"  ❌ Error {response.status_code} for {name}")
                        data[name] = None
                        
                except Exception as e:
                    print(f"  ⚠️ Error fetching {name}: {e}")
                    data[name] = None
            
            # Combine all EIA series
            eia_dfs = []
            for name, df in data.items():
                if df is not None and not df.empty:
                    eia_dfs.append(df)
            
            if eia_dfs:
                # Start with the first non-empty DataFrame
                df_eia = eia_dfs[0].copy()
                for df in eia_dfs[1:]:
                    df_eia = df_eia.join(df, how='outer')
                return df_eia
            else:
                print("⚠️ No EIA data retrieved")
                return None
            
        except ImportError:
            print("⚠️  requests not installed. Please install: pip install requests")
            return None
        except Exception as e:
            print(f"❌ Error fetching EIA data: {e}")
            return None
    
    def fetch_alternative_data(self):
        """
        Fetch alternative data - NOTE: yfinance may have issues in Colab
        Returns:
            pd.DataFrame: DataFrame with alternative data
        """
        print("📊 Alternative data: Skipping yfinance (known issues in Colab)")
        return None
    
    def load_all_data(self):
        """
        Load all data from all sources
        
        Returns:
            dict: Dictionary containing all DataFrames
        """
        print("=" * 60)
        print("🚀 Starting Data Collection")
        print("=" * 60)
        
        # Fetch FRED data
        df_fred = self.fetch_fred_data()
        
        # Fetch EIA data
        df_eia = self.fetch_eia_data()
        
        # Alternative data (skipping yfinance for now)
        df_alt = None
        
        return {
            'fred': df_fred,
            'eia': df_eia,
            'alternative': df_alt
        }

# Test the module when run directly
if __name__ == "__main__":
    loader = DataLoader()
    data = loader.load_all_data()
    print("\n✅ Data loading complete!")
    for key, df in data.items():
        if df is not None:
            print(f"  {key}: {df.shape}")
        else:
            print(f"  {key}: No data")
