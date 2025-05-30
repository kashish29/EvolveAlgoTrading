from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime

class AbstractDataSource(ABC):
    """
    Abstract base class for data sources.
    It defines the interface for fetching historical market data and
    provides common utility methods for data validation and standardization.
    """

    @abstractmethod
    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime, timeframe: str) -> pd.DataFrame:
        """
        Fetches historical market data for a given symbol and time range.

        Args:
            symbol (str): The trading symbol (e.g., "SBIN-EQ").
            start_date (datetime): The start date for the data.
            end_date (datetime): The end date for the data.
            timeframe (str): The timeframe for the data (e.g., "1D", "5MIN").

        Returns:
            pd.DataFrame: A Pandas DataFrame containing the historical data.
                          The DataFrame must include 'timestamp' (datetime64)
                          and OHLCV columns ('open', 'high', 'low', 'close', 'volume').
                          Returns an empty DataFrame if no data is found or an error occurs.
        """
        pass

    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validates the structure of the fetched DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame to validate.

        Returns:
            bool: True if the DataFrame is valid, False otherwise.
        """
        if df is None:
            print("Validation Error: DataFrame is None.")
            return False

        if not isinstance(df, pd.DataFrame):
            print(f"Validation Error: Expected pd.DataFrame, got {type(df)}.")
            return False

        # Allow empty DataFrames to be valid, as fetch_data might return an empty DF for no data.
        # Specific checks for columns will only apply if the DataFrame is not empty.
        if df.empty:
            return True

        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            print(f"Validation Error: DataFrame is missing required columns: {missing_columns}.")
            return False

        # Further checks can be added here (e.g., data types of columns if needed,
        # but standardize_data is expected to handle type conversions).

        return True

    def standardize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardizes the DataFrame:
        - Ensures 'timestamp' column is of datetime64 type.
        - Ensures OHLCV columns are of appropriate numeric types.

        Args:
            df (pd.DataFrame): The DataFrame to standardize.

        Returns:
            pd.DataFrame: The standardized DataFrame. Returns an empty DataFrame if input is empty.
        """
        if df is None or df.empty:
            # print("Standardize Data: Input DataFrame is None or empty. Returning as is.")
            return pd.DataFrame() # Return an empty DF with no columns by default if input is None/empty

        df_copy = df.copy()

        # Standardize 'timestamp' column
        if 'timestamp' in df_copy.columns:
            try:
                df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'])
            except Exception as e:
                print(f"Standardize Data Error: Could not convert 'timestamp' to datetime: {e}. Dropping 'timestamp'.")
                # Decide on error handling: drop column, raise error, or return original df_copy
                # For now, let's make it NaT where conversion fails, or handle more gracefully
                df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'], errors='coerce')
        else:
            print("Standardize Data Warning: 'timestamp' column not found.")


        # Standardize OHLCV columns to numeric types
        ohlcv_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in ohlcv_columns:
            if col in df_copy.columns:
                try:
                    df_copy[col] = pd.to_numeric(df_copy[col])
                except Exception as e:
                    print(f"Standardize Data Error: Could not convert column '{col}' to numeric: {e}. Column may contain non-numeric data.")
                    # Coerce errors, converting non-numeric to NaN
                    df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce') 
            else:
                print(f"Standardize Data Warning: Column '{col}' not found for standardization.")
        
        return df_copy

    def adjust_for_splits(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adjusts historical data for stock splits.
        Placeholder for now. This method should be implemented by concrete
        data sources if they need to handle split adjustments.

        Args:
            df (pd.DataFrame): The DataFrame with historical data.

        Returns:
            pd.DataFrame: The DataFrame adjusted for splits.
        """
        # print("Adjust for Splits: No adjustment logic implemented. Returning original DataFrame.")
        # For now, this is a pass-through.
        # Concrete implementations might override this or call a shared utility.
        return df

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
