"""
PropertyIQ Feature Engineering Module
Builds standard Scikit-learn ColumnTransformer preprocessor and prepares feature matrices.
"""

from typing import Tuple, List
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder


class FeatureEngineer:
    """Manages feature definitions, column transformation pipelines, and matrix preparations."""

    NUMERICAL_FEATURES: List[str] = [
        "built_up_area",
        "carpet_area",
        "bhk",
        "bathrooms",
        "property_age",
        "floor_no",
        "total_floors",
        "parking_spaces",
        "highway_distance_km",
        "railway_distance_km",
        "metro_distance_km",
        "hospital_distance_km",
        "school_distance_km",
        "market_distance_km",
        "has_water_supply",
        "has_power_backup",
        "has_piped_gas",
        "has_underground_drainage",
        "carpet_to_built_ratio",
        "floor_ratio"
    ]

    CATEGORICAL_FEATURES: List[str] = [
        "locality_name",
        "property_type",
        "furnishing_status",
        "road_type",
        "parking_type"
    ]

    TARGET_COLUMN: str = "actual_price_inr"

    @classmethod
    def create_engineered_features(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Computes derived ratios and interaction terms."""
        enhanced_df = df.copy()

        # Carpet to built-up efficiency ratio
        if "carpet_area" in enhanced_df.columns and "built_up_area" in enhanced_df.columns:
            enhanced_df["carpet_to_built_ratio"] = (
                enhanced_df["carpet_area"] / enhanced_df["built_up_area"].replace(0, np.nan)
            ).fillna(0.78).clip(0.5, 1.0)
        else:
            enhanced_df["carpet_to_built_ratio"] = 0.78

        # Floor position ratio within building height
        if "floor_no" in enhanced_df.columns and "total_floors" in enhanced_df.columns:
            enhanced_df["floor_ratio"] = (
                enhanced_df["floor_no"] / enhanced_df["total_floors"].replace(0, np.nan)
            ).fillna(0.3).clip(0.0, 1.0)
        else:
            enhanced_df["floor_ratio"] = 0.3

        return enhanced_df

    @classmethod
    def get_preprocessor(cls) -> ColumnTransformer:
        """
        Constructs an explicit Scikit-Learn ColumnTransformer:
        - StandardScaler for continuous and engineered ratios
        - OneHotEncoder for nominal categoricals
        """
        numeric_transformer = StandardScaler()
        categorical_transformer = OneHotEncoder(handle_unknown="ignore", sparse_output=False)

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, cls.NUMERICAL_FEATURES),
                ("cat", categorical_transformer, cls.CATEGORICAL_FEATURES)
            ],
            remainder="drop"
        )
        return preprocessor

    @classmethod
    def prepare_dataset(cls, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepares feature dataframe X and target vector y."""
        enhanced_df = cls.create_engineered_features(df)
        all_features = cls.NUMERICAL_FEATURES + cls.CATEGORICAL_FEATURES

        missing_cols = [c for c in all_features if c not in enhanced_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in dataset: {missing_cols}")

        X = enhanced_df[all_features].copy()
        y = enhanced_df[cls.TARGET_COLUMN].copy()
        return X, y


if __name__ == "__main__":
    from src.data_loader import DataLoader
    from src.data_cleaning import DataCleaner

    loader = DataLoader()
    raw = loader.load_properties()
    cleaned, _ = DataCleaner.clean_property_dataframe(raw)
    X, y = FeatureEngineer.prepare_dataset(cleaned)
    print("Features matrix X shape:", X.shape)
    print("Target y shape:", y.shape)
