"""
PropertyIQ Data Science & ML Reporting Module
Renders rigorous statistical and machine learning charts using Matplotlib and Seaborn.
Uses headless 'Agg' backend and returns high-resolution base64 PNG data URLs for web UI display.
"""

import sys
import io
import base64
from pathlib import Path
from typing import Dict, Any, Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import joblib

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.schema import get_db_connection
from src.data_loader import DataLoader
from src.feature_engineering import FeatureEngineer

MODELS_DIR = BASE_DIR / "models"

# Configure clean, elegant styling for Seaborn and Matplotlib
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
plt.rcParams["axes.edgecolor"] = "#c9bda4"
plt.rcParams["axes.linewidth"] = 0.8


def fig_to_base64(fig: plt.Figure) -> str:
    """Converts a Matplotlib figure into a base64 encoded PNG data URL."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{img_b64}"


class ChartGenerator:
    """Generates analytical visualizations using Matplotlib & Seaborn."""

    def __init__(self):
        self.loader = DataLoader()

    def generate_historical_trends_chart(self, top_n_localities: int = 6) -> str:
        """
        Matplotlib/Seaborn line chart of yearly average price per sqft across top localities (2021-2026).
        """
        with self.loader.get_connection() as conn:
            query = """
            SELECT locality_name, transaction_year, ROUND(AVG(price_per_sqft), 2) as avg_sqft
            FROM transactions
            GROUP BY locality_name, transaction_year
            ORDER BY transaction_year ASC
            """
            df = pd.read_sql_query(query, conn)

        # Filter to top localities by volume or price
        top_locs = df.groupby("locality_name")["avg_sqft"].mean().nlargest(top_n_localities).index.tolist()
        df_filtered = df[df["locality_name"].isin(top_locs)]

        fig, ax = plt.subplots(figsize=(10, 5.2))
        palette = sns.color_palette("tab10", n_colors=len(top_locs))

        sns.lineplot(
            data=df_filtered,
            x="transaction_year",
            y="avg_sqft",
            hue="locality_name",
            marker="o",
            linewidth=2.4,
            palette=palette,
            ax=ax
        )

        ax.set_title("Historical Price Trends by Locality (₹ / sq.ft, 2021-2026)", fontsize=13, fontweight="bold", pad=12, color="#1a1a1a")
        ax.set_xlabel("Transaction Year", fontsize=10, color="#4a4a45")
        ax.set_ylabel("Average Price (₹ / sq.ft)", fontsize=10, color="#4a4a45")
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: f"₹{int(x):,}"))
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        ax.legend(title="Locality", title_fontsize="9", fontsize="8.5", frameon=True, facecolor="#f5f0e6", loc="upper left")
        ax.grid(True, linestyle="--", alpha=0.5)

        return fig_to_base64(fig)

    def generate_model_comparison_chart(self) -> str:
        """
        Matplotlib/Seaborn bar chart comparing MAE, RMSE, and R2 across the 3 permitted models.
        """
        metrics_file = MODELS_DIR / "metrics.json"
        if not metrics_file.exists():
            return ""

        import json
        with open(metrics_file, "r") as f:
            data = json.load(f)

        models_data = data.get("models", {})
        names = []
        r2_scores = []
        mae_lakhs = []

        for k, v in models_data.items():
            names.append(v.get("algorithm_name", k))
            r2_scores.append(v.get("r2_score", 0))
            mae_lakhs.append(v.get("mae_lakhs", 0))

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

        # R2 Bar Chart
        colors_r2 = ["#6b8f71", "#5a7d5f", "#4f6b55"]
        bars1 = ax1.bar(names, r2_scores, color=colors_r2, width=0.55, edgecolor="#2a2a27", linewidth=0.5)
        ax1.set_title("R² Score (Goodness of Fit on Test Set)", fontsize=11, fontweight="bold", pad=10, color="#1a1a1a")
        ax1.set_ylabel("R² (Max 1.0)", fontsize=9.5, color="#4a4a45")
        ax1.set_ylim(0, 1.05)
        for b in bars1:
            h = b.get_height()
            ax1.text(b.get_x() + b.get_width() / 2., h + 0.02, f"{h:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#2a2a27")
        ax1.tick_params(axis="x", rotation=12)

        # MAE Bar Chart (lower is better)
        colors_mae = ["#b08d57", "#ec4899", "#5a7d5f"]
        bars2 = ax2.bar(names, mae_lakhs, color=colors_mae, width=0.55, edgecolor="#2a2a27", linewidth=0.5)
        ax2.set_title("Mean Absolute Error (₹ Lakhs, Lower is Better)", fontsize=11, fontweight="bold", pad=10, color="#1a1a1a")
        ax2.set_ylabel("MAE (₹ Lakhs)", fontsize=9.5, color="#4a4a45")
        for b in bars2:
            h = b.get_height()
            ax2.text(b.get_x() + b.get_width() / 2., h + 1.5, f"₹{h:.1f}L", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#2a2a27")
        ax2.tick_params(axis="x", rotation=12)

        plt.tight_layout()
        return fig_to_base64(fig)

    def generate_feature_importance_chart(self, top_n: int = 10) -> str:
        """
        Matplotlib/Seaborn horizontal bar chart showing Random Forest Gini feature importances.
        """
        rf_path = MODELS_DIR / "random_forest.joblib"
        prep_path = MODELS_DIR / "preprocessor.joblib"
        if not rf_path.exists() or not prep_path.exists():
            return ""

        rf = joblib.load(rf_path)
        preprocessor = joblib.load(prep_path)

        # Extract transformed feature names
        try:
            feature_names = preprocessor.get_feature_names_out()
            # Clean feature names (strip 'num__', 'cat__')
            clean_names = [f.replace("num__", "").replace("cat__", "").replace("locality_name_", "Loc: ") for f in feature_names]
            importances = rf.feature_importances_

            fi_df = pd.DataFrame({"feature": clean_names, "importance": importances})
            fi_df = fi_df.sort_values(by="importance", ascending=False).head(top_n)

            fig, ax = plt.subplots(figsize=(9, 4.8))
            sns.barplot(data=fi_df, x="importance", y="feature", hue="feature", legend=False, palette="Blues_r", ax=ax, edgecolor="#3a3a36")
            ax.set_title("Random Forest Regressor — Top Predictive Features", fontsize=11.5, fontweight="bold", pad=12, color="#1a1a1a")
            ax.set_xlabel("Relative Importance (Gini Impurity Reduction)", fontsize=9.5, color="#4a4a45")
            ax.set_ylabel("", fontsize=9)

            for p in ax.patches:
                val = p.get_width()
                ax.annotate(f"{val*100:.1f}%", (val + 0.005, p.get_y() + p.get_height() / 2.),
                            ha="left", va="center", fontsize=8.5, fontweight="bold", color="#1a1a1a")

            ax.set_xlim(0, max(fi_df["importance"]) * 1.18)
            plt.tight_layout()
            return fig_to_base64(fig)
        except Exception as e:
            print("Feature importance error:", e)
            return ""

    def generate_kmeans_cluster_chart(self) -> str:
        """
        Matplotlib/Seaborn scatter plot of K-Means locality clusters: Price/sqft vs Transit Score.
        """
        localities_df = self.loader.load_localities()
        if localities_df.empty:
            return ""

        fig, ax = plt.subplots(figsize=(9, 5))
        palette = sns.color_palette("Set2", n_colors=len(localities_df["cluster_id"].unique()))

        sns.scatterplot(
            data=localities_df,
            x="transit_accessibility_score",
            y="avg_price_sqft",
            hue="cluster_label",
            style="zone",
            s=220,
            palette=palette,
            ax=ax,
            edgecolor="#2a2a27",
            linewidth=1.2
        )

        # Label points with locality names
        for _, row in localities_df.iterrows():
            ax.text(
                row["transit_accessibility_score"] + 0.04,
                row["avg_price_sqft"] + 450,
                row["locality_name"],
                fontsize=7.5,
                color="#1a1a1a",
                fontweight="medium"
            )

        ax.set_title("K-Means Locality Clusters: Price/sq.ft vs Transit Accessibility Score", fontsize=12, fontweight="bold", pad=12, color="#1a1a1a")
        ax.set_xlabel("Transit Accessibility Score (0 to 10)", fontsize=9.5, color="#4a4a45")
        ax.set_ylabel("Average Price (₹ / sq.ft)", fontsize=9.5, color="#4a4a45")
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: f"₹{int(x):,}"))
        ax.legend(title="Cluster Classification", title_fontsize="8.5", fontsize="7.5", loc="upper left", frameon=True, facecolor="#f5f0e6")

        plt.tight_layout()
        return fig_to_base64(fig)


if __name__ == "__main__":
    cg = ChartGenerator()
    b64_trends = cg.generate_historical_trends_chart()
    print("Trends chart b64 length:", len(b64_trends))
    b64_models = cg.generate_model_comparison_chart()
    print("Model comparison b64 length:", len(b64_models))
    b64_fi = cg.generate_feature_importance_chart()
    print("Feature importance b64 length:", len(b64_fi))
    b64_cluster = cg.generate_kmeans_cluster_chart()
    print("K-Means chart b64 length:", len(b64_cluster))
