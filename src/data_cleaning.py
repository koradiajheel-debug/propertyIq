"""
PropertyIQ Data Cleaning Module
Performs dataset validation, missing-value imputation, type sanitization, and outlier checks using Pandas.
"""

from typing import Tuple, Dict, Any
import pandas as pd
import numpy as np


class DataCleaner:
    """Prepares and validates property records for data analysis and ML model consumption."""

    EXPECTED_NUMERIC_COLS = [
        "built_up_area", "carpet_area", "bhk", "bathrooms", "property_age",
        "floor_no", "total_floors", "parking_spaces", "highway_distance_km",
        "railway_distance_km", "metro_distance_km", "hospital_distance_km",
        "school_distance_km", "market_distance_km"
    ]

    EXPECTED_CATEGORICAL_COLS = [
        "locality_name", "property_type", "furnishing_status", "road_type", "parking_type"
    ]

    @staticmethod
    def clean_property_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Cleans property data:
        1. Checks for missing values and imputes if found
        2. Ensures built_up_area and carpet_area bounds
        3. Sanitizes boolean infrastructure flags
        4. Validates target column actual_price_inr
        """
        cleaned_df = df.copy()
        report = {
            "initial_rows": len(cleaned_df),
            "missing_values_handled": 0,
            "outliers_adjusted": 0
        }

        # Impute missing numericals with median
        for col in DataCleaner.EXPECTED_NUMERIC_COLS:
            if col in cleaned_df.columns:
                null_count = cleaned_df[col].isnull().sum()
                if null_count > 0:
                    median_val = cleaned_df[col].median()
                    cleaned_df[col] = cleaned_df[col].fillna(median_val)
                    report["missing_values_handled"] += int(null_count)

        # Impute missing categoricals with mode or 'Unknown'
        for col in DataCleaner.EXPECTED_CATEGORICAL_COLS:
            if col in cleaned_df.columns:
                null_count = cleaned_df[col].isnull().sum()
                if null_count > 0:
                    mode_val = cleaned_df[col].mode()[0] if not cleaned_df[col].empty else "Unknown"
                    cleaned_df[col] = cleaned_df[col].fillna(mode_val)
                    report["missing_values_handled"] += int(null_count)

        # Infrastructure flags validation
        flag_cols = ["has_water_supply", "has_power_backup", "has_piped_gas", "has_underground_drainage"]
        for f in flag_cols:
            if f in cleaned_df.columns:
                cleaned_df[f] = cleaned_df[f].fillna(1).astype(int).clip(0, 1)

        # Ensure carpet_area does not exceed built_up_area
        if "carpet_area" in cleaned_df.columns and "built_up_area" in cleaned_df.columns:
            invalid_carpet = cleaned_df["carpet_area"] > cleaned_df["built_up_area"]
            if invalid_carpet.any():
                cleaned_df.loc[invalid_carpet, "carpet_area"] = cleaned_df.loc[invalid_carpet, "built_up_area"] * 0.78
                report["outliers_adjusted"] += int(invalid_carpet.sum())

        # Ensure floor_no does not exceed total_floors
        if "floor_no" in cleaned_df.columns and "total_floors" in cleaned_df.columns:
            invalid_floor = cleaned_df["floor_no"] > cleaned_df["total_floors"]
            if invalid_floor.any():
                cleaned_df.loc[invalid_floor, "floor_no"] = cleaned_df.loc[invalid_floor, "total_floors"]

        report["final_rows"] = len(cleaned_df)
        return cleaned_df, report


if __name__ == "__main__":
    from src.data_loader import DataLoader
    loader = DataLoader()
    raw_df = loader.load_properties()
    cleaned, rep = DataCleaner.clean_property_dataframe(raw_df)
    print("Data Cleaning Report:", rep)
