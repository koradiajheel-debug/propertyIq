"""
PropertyIQ Data Loader Module
Loads structured datasets from SQLite database into Pandas DataFrames.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.schema import get_db_connection


class DataLoader:
    """Manages queries and DataFrame extractions from the PropertyIQ SQLite database."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path

    def get_connection(self):
        return get_db_connection(self.db_path)

    def load_properties(self) -> pd.DataFrame:
        """Load all properties into a Pandas DataFrame."""
        with self.get_connection() as conn:
            query = """
            SELECT p.*, l.zone, l.transit_accessibility_score, l.infrastructure_rating,
                   l.avg_household_income_lakhs, l.socioeconomic_tier, l.cluster_id, l.cluster_label
            FROM properties p
            JOIN localities l ON p.locality_id = l.locality_id
            """
            return pd.read_sql_query(query, conn)

    def load_localities(self) -> pd.DataFrame:
        """Load all localities into a Pandas DataFrame."""
        with self.get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM localities ORDER BY avg_price_sqft DESC", conn)

    def load_transactions(self) -> pd.DataFrame:
        """Load all historical transactions."""
        with self.get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM transactions ORDER BY transaction_date ASC", conn)

    def load_amenities(self, locality_id: Optional[str] = None) -> pd.DataFrame:
        """Load amenities, optionally filtered by locality."""
        with self.get_connection() as conn:
            if locality_id:
                return pd.read_sql_query(
                    "SELECT * FROM amenities WHERE locality_id = ? ORDER BY rating DESC",
                    conn, params=(locality_id,)
                )
            return pd.read_sql_query("SELECT * FROM amenities ORDER BY name ASC", conn)

    def load_development_projects(self, locality_id: Optional[str] = None) -> pd.DataFrame:
        """Load infrastructure and development projects."""
        with self.get_connection() as conn:
            if locality_id:
                return pd.read_sql_query(
                    "SELECT * FROM development_projects WHERE locality_id = ?",
                    conn, params=(locality_id,)
                )
            return pd.read_sql_query("SELECT * FROM development_projects ORDER BY announcement_year DESC", conn)

    def load_market_snapshots(self, limit_per_loc: int = 10) -> pd.DataFrame:
        """Load recent market snapshots."""
        with self.get_connection() as conn:
            query = """
            SELECT * FROM market_snapshots
            ORDER BY snapshot_id DESC
            LIMIT ?
            """
            return pd.read_sql_query(query, conn, params=(limit_per_loc * 14,))

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Compute system-wide KPI summary metrics."""
        with self.get_connection() as conn:
            prop_count = conn.execute("SELECT COUNT(*) FROM properties").fetchone()[0]
            loc_count = conn.execute("SELECT COUNT(*) FROM localities").fetchone()[0]
            txn_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            amenity_count = conn.execute("SELECT COUNT(*) FROM amenities").fetchone()[0]
            avg_sqft = conn.execute("SELECT ROUND(AVG(price_per_sqft), 2) FROM properties").fetchone()[0]
            min_sqft = conn.execute("SELECT ROUND(MIN(price_per_sqft), 2) FROM properties").fetchone()[0]
            max_sqft = conn.execute("SELECT ROUND(MAX(price_per_sqft), 2) FROM properties").fetchone()[0]

            latest_snapshot = conn.execute(
                "SELECT timestamp, ROUND(AVG(daily_change_pct), 2), ROUND(AVG(demand_activity_index), 1) FROM market_snapshots GROUP BY timestamp ORDER BY snapshot_id DESC LIMIT 1"
            ).fetchone()

            snapshot_time = latest_snapshot[0] if latest_snapshot else "Not recorded"
            avg_daily_change = latest_snapshot[1] if latest_snapshot else 0.0
            avg_demand = latest_snapshot[2] if latest_snapshot else 75.0

            return {
                "total_properties": prop_count,
                "total_localities": loc_count,
                "total_transactions": txn_count,
                "total_amenities": amenity_count,
                "avg_price_per_sqft": avg_sqft,
                "min_price_per_sqft": min_sqft,
                "max_price_per_sqft": max_sqft,
                "snapshot_time": snapshot_time,
                "market_daily_change_pct": avg_daily_change,
                "market_demand_index": avg_demand,
                "data_source_status": "Simulated Demonstration Dataset",
                "geographic_region": "Mumbai & MMR, Maharashtra, India"
            }


if __name__ == "__main__":
    loader = DataLoader()
    summary = loader.get_summary_statistics()
    print("Database Summary:", summary)
