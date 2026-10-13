"""
PropertyIQ Locality Clustering Module
Uses K-Means Clustering to group Mumbai/MMR localities into distinct market tiers
based on price per square foot, density, growth, transit access, and infrastructure.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.schema import get_db_connection
from src.data_loader import DataLoader

MODELS_DIR = BASE_DIR / "models"


class LocalityClusterer:
    """Performs K-Means clustering on locality feature vectors."""

    CLUSTER_FEATURES = [
        "avg_price_sqft",
        "population_density",
        "historical_cagr_5yr",
        "transit_accessibility_score",
        "infrastructure_rating"
    ]

    def __init__(self, n_clusters: int = 4, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.data_loader = DataLoader()
        self.scaler = StandardScaler()
        self.kmeans = None

    def run_clustering(self, n_clusters: int = 4) -> Dict[str, Any]:
        """Fits K-Means, labels clusters, updates SQLite database, and saves model."""
        self.n_clusters = n_clusters
        localities_df = self.data_loader.load_localities()

        if len(localities_df) < self.n_clusters:
            raise ValueError("Number of localities is smaller than number of clusters.")

        X = localities_df[self.CLUSTER_FEATURES].copy()
        X_scaled = self.scaler.fit_transform(X)

        self.kmeans = KMeans(
            n_clusters=self.n_clusters,
            init="k-means++",
            n_init=10,
            max_iter=300,
            random_state=self.random_state
        )
        labels = self.kmeans.fit_predict(X_scaled)
        localities_df["cluster_id"] = labels

        # Compute silhouette score if clusters > 1
        sil_score = float(silhouette_score(X_scaled, labels)) if self.n_clusters > 1 else 0.0
        inertia = float(self.kmeans.inertia_)

        # Derive intuitive cluster profiles based on average price and transit score
        cluster_summaries = {}
        cluster_labels_map = {}

        for c_id in range(self.n_clusters):
            c_subset = localities_df[localities_df["cluster_id"] == c_id]
            mean_sqft = c_subset["avg_price_sqft"].mean()
            mean_transit = c_subset["transit_accessibility_score"].mean()
            mean_growth = c_subset["historical_cagr_5yr"].mean()

            # Name clusters intelligently based on centroid
            if mean_sqft > 40000:
                c_label = "Ultra-Premium Waterfront & Heritage Hubs"
            elif mean_sqft > 25000:
                c_label = "Prime High-Density Commercial & Tech Corridors"
            elif mean_sqft > 18000:
                c_label = "Established Suburban Family Residential"
            else:
                c_label = "High-Growth Developing MMR Suburban Corridors"

            cluster_labels_map[c_id] = c_label
            cluster_summaries[c_id] = {
                "cluster_id": c_id,
                "label": c_label,
                "locality_count": len(c_subset),
                "localities": c_subset["locality_name"].tolist(),
                "mean_price_sqft": round(mean_sqft, 2),
                "mean_transit_score": round(mean_transit, 2),
                "mean_cagr_5yr": round(mean_growth, 2),
                "mean_density": round(c_subset["population_density"].mean(), 1)
            }

        localities_df["cluster_label"] = localities_df["cluster_id"].map(cluster_labels_map)

        # Update SQLite database
        conn = get_db_connection()
        for _, row in localities_df.iterrows():
            conn.execute("""
            UPDATE localities
            SET cluster_id = ?, cluster_label = ?
            WHERE locality_id = ?
            """, (int(row["cluster_id"]), str(row["cluster_label"]), str(row["locality_id"])))
        conn.commit()
        conn.close()

        # Save artifacts
        joblib.dump(self.kmeans, MODELS_DIR / "kmeans.joblib")
        joblib.dump(self.scaler, MODELS_DIR / "kmeans_scaler.joblib")

        output = {
            "n_clusters": self.n_clusters,
            "inertia": round(inertia, 2),
            "silhouette_score": round(sil_score, 4),
            "cluster_profiles": cluster_summaries,
            "features_used": self.CLUSTER_FEATURES,
            "viva_explanation": (
                "K-Means partitions localities into k groups by minimizing intra-cluster inertia (sum of squared Euclidean distances to cluster centroids). "
                "Feature standardization via StandardScaler is mandatory because price per sq.ft (~₹50,000) and transit score (0-10) have vastly different scales."
            )
        }

        with open(MODELS_DIR / "kmeans_metadata.json", "w") as f:
            json.dump(output, f, indent=2)

        print(f"K-Means clustering completed (k={self.n_clusters}, Silhouette: {sil_score:.3f}, Inertia: {inertia:.1f})")
        return output


if __name__ == "__main__":
    clusterer = LocalityClusterer(n_clusters=4)
    res = clusterer.run_clustering()
    print("Cluster Profiles:", json.dumps(res["cluster_profiles"], indent=2))
