"""
PropertyIQ Model Evaluation Module
Calculates formal regression evaluation metrics: MAE, RMSE, and R2 on held-out test data.
Includes clear mathematical and intuitive explanations suitable for college viva / practical examination.
"""

from typing import Dict, Any
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


class ModelEvaluator:
    """Computes and formats regression metrics for academic and real-estate analytics."""

    @staticmethod
    def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
        """
        Calculates:
        1. MAE (Mean Absolute Error): Average absolute difference between actual and predicted prices.
           Formula: (1 / n) * sum(|y_true - y_pred|)
        2. RMSE (Root Mean Squared Error): Square root of mean squared errors, penalizing large errors.
           Formula: sqrt((1 / n) * sum((y_true - y_pred)^2))
        3. R2 (Coefficient of Determination): Proportion of variance explained by the model.
           Formula: 1 - (SS_res / SS_tot)
        4. MAPE (Mean Absolute Percentage Error): Average percentage error.
        """
        mae = float(mean_absolute_error(y_true, y_pred))
        mse = float(mean_squared_error(y_true, y_pred))
        rmse = float(np.sqrt(mse))
        r2 = float(r2_score(y_true, y_pred))

        # Percentage error
        non_zero = y_true != 0
        mape = float(np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])) * 100)

        return {
            "mae_inr": round(mae, 2),
            "mae_lakhs": round(mae / 100000.0, 2),
            "rmse_inr": round(rmse, 2),
            "rmse_lakhs": round(rmse / 100000.0, 2),
            "r2_score": round(r2, 4),
            "mape_pct": round(mape, 2),
            "viva_explanation": {
                "mae": "Mean Absolute Error measures the average magnitude of prediction errors in rupees. An MAE of ₹8.5 Lakhs means predictions typically deviate by around ₹8.5 Lakhs from actual transaction values.",
                "rmse": "Root Mean Squared Error gives extra weight to large prediction deviations because errors are squared before averaging. Useful for detecting severe outlier misvaluations.",
                "r2": f"R-squared ({round(r2*100, 1)}%) indicates what percentage of the variance in property prices across Mumbai/MMR is successfully explained by physical specifications, location, amenities, and transit distances."
            }
        }


if __name__ == "__main__":
    y_t = np.array([10000000, 15000000, 25000000, 8000000])
    y_p = np.array([10200000, 14700000, 25800000, 8300000])
    print(ModelEvaluator.evaluate_predictions(y_t, y_p))
