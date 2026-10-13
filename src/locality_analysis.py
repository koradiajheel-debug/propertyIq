"""
PropertyIQ Locality Analysis Module
Aggregates neighbourhood intelligence, demographic metrics, amenity distributions,
and provides multi-locality comparative benchmarking.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.schema import get_db_connection
from src.data_loader import DataLoader


class LocalityAnalyzer:
    """Provides detailed locality intelligence profiles and comparative analytics."""

    def __init__(self):
        self.loader = DataLoader()

    def get_locality_profile(self, locality_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full structured profile of a locality."""
        with self.loader.get_connection() as conn:
            loc = conn.execute("SELECT * FROM localities WHERE locality_id = ?", (locality_id,)).fetchone()
            if not loc:
                return None

            loc_dict = dict(loc)

            # Property inventory breakdown
            props_df = pd.read_sql_query(
                "SELECT property_type, bhk, built_up_area, price_per_sqft FROM properties WHERE locality_id = ?",
                conn, params=(locality_id,)
            )

            bhk_dist = props_df["bhk"].value_counts().to_dict() if not props_df.empty else {}
            type_dist = props_df["property_type"].value_counts().to_dict() if not props_df.empty else {}

            # Amenities in locality
            amenities = conn.execute(
                "SELECT * FROM amenities WHERE locality_id = ? ORDER BY rating DESC",
                (locality_id,)
            ).fetchall()
            amenities_list = [dict(a) for a in amenities]

            # Infrastructure projects in locality
            projects = conn.execute(
                "SELECT * FROM development_projects WHERE locality_id = ? ORDER BY announcement_year DESC",
                (locality_id,)
            ).fetchall()
            projects_list = [dict(p) for p in projects]

            # Recent market snapshot
            snapshot = conn.execute(
                "SELECT * FROM market_snapshots WHERE locality_id = ? ORDER BY snapshot_id DESC LIMIT 1",
                (locality_id,)
            ).fetchone()
            snapshot_dict = dict(snapshot) if snapshot else {}

            return {
                "locality_id": loc_dict["locality_id"],
                "locality_name": loc_dict["locality_name"],
                "city": loc_dict["city"],
                "zone": loc_dict["zone"],
                "coordinates": {"lat": loc_dict["latitude"], "lng": loc_dict["longitude"]},
                "demographics": {
                    "population": loc_dict["population"],
                    "population_density_per_sqkm": loc_dict["population_density"],
                    "avg_household_income_lakhs": loc_dict["avg_household_income_lakhs"],
                    "socioeconomic_tier": loc_dict["socioeconomic_tier"]
                },
                "pricing": {
                    "avg_price_sqft": loc_dict["avg_price_sqft"],
                    "median_price_sqft": loc_dict["median_price_sqft"],
                    "yoy_price_change_pct": loc_dict["yoy_price_change_pct"],
                    "historical_cagr_5yr": loc_dict["historical_cagr_5yr"],
                    "market_movement_status": "Simulated Market Feed"
                },
                "inventory": {
                    "total_properties": loc_dict["property_count"],
                    "bhk_distribution": bhk_dist,
                    "type_distribution": type_dist
                },
                "transit_and_infra": {
                    "transit_score": loc_dict["transit_accessibility_score"],
                    "infrastructure_rating": loc_dict["infrastructure_rating"],
                    "highway_connectivity": loc_dict["highway_connectivity"],
                    "hospital_count": loc_dict["hospital_count"],
                    "school_count": loc_dict["school_count"],
                    "metro_count": loc_dict["metro_station_count"],
                    "railway_count": loc_dict["railway_station_count"],
                    "mall_count": loc_dict["mall_market_count"],
                    "park_count": loc_dict["park_count"]
                },
                "clustering": {
                    "cluster_id": loc_dict["cluster_id"],
                    "cluster_label": loc_dict["cluster_label"]
                },
                "amenities": amenities_list,
                "development_projects": projects_list,
                "market_snapshot": snapshot_dict,
                "data_provenance": "Aggregated locality intelligence (Simulated demonstration)",
                "last_updated": loc_dict["last_updated"]
            }

    def compare_localities(self, locality_ids: List[str]) -> List[Dict[str, Any]]:
        """Compares multiple localities side-by-side."""
        results = []
        for loc_id in locality_ids:
            profile = self.get_locality_profile(loc_id)
            if profile:
                results.append({
                    "locality_id": profile["locality_id"],
                    "locality_name": profile["locality_name"],
                    "zone": profile["zone"],
                    "avg_price_sqft": profile["pricing"]["avg_price_sqft"],
                    "yoy_price_change_pct": profile["pricing"]["yoy_price_change_pct"],
                    "historical_cagr_5yr": profile["pricing"]["historical_cagr_5yr"],
                    "population_density": profile["demographics"]["population_density_per_sqkm"],
                    "avg_income_lakhs": profile["demographics"]["avg_household_income_lakhs"],
                    "transit_score": profile["transit_and_infra"]["transit_score"],
                    "infra_rating": profile["transit_and_infra"]["infrastructure_rating"],
                    "total_properties": profile["inventory"]["total_properties"],
                    "cluster_label": profile["clustering"]["cluster_label"]
                })
        return results


if __name__ == "__main__":
    analyzer = LocalityAnalyzer()
    profile = analyzer.get_locality_profile("LOC-ANDW")
    print(f"Profile loaded for {profile['locality_name']}, Cluster: {profile['clustering']['cluster_label']}")
    comp = analyzer.compare_localities(["LOC-ANDW", "LOC-BANDW", "LOC-THANE"])
    print("Comparison count:", len(comp))
