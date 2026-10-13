"""
PropertyIQ Model Training Pipeline
Trains permitted regression models:
1. Linear Regression
2. Decision Tree Regressor
3. Random Forest Regressor (Ensemble)
Uses train/test split, column transformation, fits models, evaluates on held-out test data,
selects the best performer, and saves fitted artifacts.
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.schema import get_db_connection
from src.data_loader import DataLoader
from src.data_cleaning import DataCleaner
from src.feature_engineering import FeatureEngineer
from src.model_evaluation import ModelEvaluator

MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


class ModelTrainer:
    """Manages model training, evaluation, comparison, and serialization."""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.data_loader = DataLoader()

    def run_training_pipeline(self) -> Dict[str, Any]:
        """Executes full reproducible training workflow."""
        print("Starting PropertyIQ Machine Learning Pipeline...")

        # 1. Load and clean raw properties
        raw_df = self.data_loader.load_properties()
        cleaned_df, clean_report = DataCleaner.clean_property_dataframe(raw_df)
        print(f"Loaded {len(cleaned_df)} records after cleaning.")

        # 2. Extract feature matrix X and target vector y
        X, y = FeatureEngineer.prepare_dataset(cleaned_df)

        # 3. Perform reproducible 80/20 train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=self.random_state
        )
        print(f"Dataset split: {len(X_train)} training samples, {len(X_test)} held-out test samples.")

        # 4. Fit Preprocessor on X_train ONLY (preventing data leakage)
        preprocessor = FeatureEngineer.get_preprocessor()
        X_train_trans = preprocessor.fit_transform(X_train)
        X_test_trans = preprocessor.transform(X_test)

        # Save fitted preprocessor
        joblib.dump(preprocessor, MODELS_DIR / "preprocessor.joblib")

        # 5. Define permitted candidate models
        models = {
            "linear_regression": {
                "name": "Linear Regression",
                "estimator": LinearRegression(),
                "file": "linear_regression.joblib",
                "syllabus_category": "Parametric Linear Regression"
            },
            "decision_tree": {
                "name": "Decision Tree Regressor",
                "estimator": DecisionTreeRegressor(
                    max_depth=12,
                    min_samples_split=4,
                    min_samples_leaf=2,
                    random_state=self.random_state
                ),
                "file": "decision_tree.joblib",
                "syllabus_category": "Non-Parametric Decision Trees"
            },
            "random_forest": {
                "name": "Random Forest Regressor",
                "estimator": RandomForestRegressor(
                    n_estimators=100,
                    max_depth=16,
                    min_samples_split=3,
                    min_samples_leaf=2,
                    random_state=self.random_state,
                    n_jobs=-1
                ),
                "file": "random_forest.joblib",
                "syllabus_category": "Ensemble Learning (Bagging)"
            }
        }

        results = {}
        best_model_key = None
        best_r2 = -float("inf")

        conn = get_db_connection()
        conn.execute("DELETE FROM model_metadata;")

        # 6. Fit, Predict, and Evaluate each model
        for key, m_info in models.items():
            print(f"Training {m_info['name']}...")
            start_time = time.time()
            estimator = m_info["estimator"]
            estimator.fit(X_train_trans, y_train)
            train_duration = round(time.time() - start_time, 3)

            # Predictions on held-out test set
            y_pred_test = estimator.predict(X_test_trans)

            # Evaluate metrics
            metrics = ModelEvaluator.evaluate_predictions(y_test.values, y_pred_test)
            metrics["train_time_sec"] = train_duration
            metrics["algorithm_name"] = m_info["name"]
            metrics["syllabus_category"] = m_info["syllabus_category"]

            # Save individual fitted model
            model_path = MODELS_DIR / m_info["file"]
            joblib.dump(estimator, model_path)

            results[key] = metrics

            if metrics["r2_score"] > best_r2:
                best_r2 = metrics["r2_score"]
                best_model_key = key

        # 7. Designate Best Model
        for key in results:
            results[key]["is_best"] = (key == best_model_key)
            m_info = models[key]
            metrics = results[key]

            # Log to SQLite metadata table
            conn.execute("""
            INSERT INTO model_metadata (
                model_id, algorithm_name, version, training_date,
                mae_inr, rmse_inr, r2_score, train_samples, test_samples,
                features_used, is_best_model, pipeline_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                key, m_info["name"], "1.0.0", datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                metrics["mae_inr"], metrics["rmse_inr"], metrics["r2_score"],
                len(X_train), len(X_test),
                json.dumps(FeatureEngineer.NUMERICAL_FEATURES + FeatureEngineer.CATEGORICAL_FEATURES),
                1 if (key == best_model_key) else 0,
                str(MODELS_DIR / m_info["file"])
            ))

        conn.commit()
        conn.close()

        # Save alias to best_model.joblib
        best_estimator = models[best_model_key]["estimator"]
        joblib.dump(best_estimator, MODELS_DIR / "best_model.joblib")

        # Save summary JSON
        summary = {
            "training_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "best_model": best_model_key,
            "models": results,
            "data_source_status": "Trained on internally consistent simulated demonstration records",
            "feature_count": X_train_trans.shape[1]
        }

        with open(MODELS_DIR / "metrics.json", "w") as f:
            json.dump(summary, f, indent=2)

        print(f"Training completed! Best model: {models[best_model_key]['name']} (R2: {best_r2})")
        return summary


if __name__ == "__main__":
    trainer = ModelTrainer()
    trainer.run_training_pipeline()
