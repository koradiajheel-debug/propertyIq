"""
PropertyIQ Market Simulation Service
Provides a live-looking, controlled dynamic market snapshot simulation.
Updates a separate `market_snapshots` table with small, bounded daily price drifts (+/- 0.1% - 0.6%)
and market demand indexes without altering immutable historical transactions or retraining ML models.
"""

import sys
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.schema import get_db_connection
from src.data_loader import DataLoader


class MarketSimulator:
    """Maintains controlled dynamic market simulation feed snapshots."""

    def __init__(self):
        self.loader = DataLoader()

    def get_latest_market_snapshot(self) -> Dict[str, Any]:
        """Returns the most recent market snapshot state across all localities."""
        with self.loader.get_connection() as conn:
            # Get latest timestamp
            row = conn.execute("SELECT timestamp FROM market_snapshots ORDER BY snapshot_id DESC LIMIT 1").fetchone()
            if not row:
                return {"snapshots": [], "timestamp": "No snapshot available"}

            latest_ts = row[0]
            snapshots = conn.execute("""
            SELECT s.*, l.zone, l.avg_household_income_lakhs
            FROM market_snapshots s
            JOIN localities l ON s.locality_id = l.locality_id
            WHERE s.snapshot_id IN (
                SELECT MAX(snapshot_id) FROM market_snapshots GROUP BY locality_id
            )
            ORDER BY s.indicative_avg_price_sqft DESC
            """).fetchall()

            metrics = conn.execute("""
            SELECT 
                ROUND(AVG(daily_change_pct), 2), 
                ROUND(AVG(demand_activity_index), 1),
                ROUND(AVG(indicative_avg_price_sqft), 0),
                ROUND(MIN(indicative_avg_price_sqft), 0),
                ROUND(MAX(indicative_avg_price_sqft), 0),
                SUM(simulated_volume_indicator),
                SUM(CASE WHEN daily_change_pct >= 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN daily_change_pct < 0 THEN 1 ELSE 0 END)
            FROM market_snapshots 
            WHERE snapshot_id IN (
                SELECT MAX(snapshot_id) FROM market_snapshots GROUP BY locality_id
            )
            """).fetchone()

            overall_drift = metrics[0] if (metrics and metrics[0] is not None) else 0.0
            demand_idx = metrics[1] if (metrics and metrics[1] is not None) else 75.0
            volume = metrics[5] if (metrics and metrics[5] is not None) else 450
            gaining_cnt = metrics[6] if (metrics and metrics[6] is not None) else 7
            softening_cnt = metrics[7] if (metrics and metrics[7] is not None) else 7

            # Live market rates: real aggregates of the latest simulated locality prices
            live_indexed_avg_sqft = int(metrics[2]) if (metrics and metrics[2] is not None) else 30977
            live_min_sqft = int(metrics[3]) if (metrics and metrics[3] is not None) else 11200
            live_max_sqft = int(metrics[4]) if (metrics and metrics[4] is not None) else 62000

            return {
                "timestamp": latest_ts,
                "overall_drift_pct": overall_drift,
                "overall_demand_index": demand_idx,
                "indicative_market_avg_sqft": live_indexed_avg_sqft,
                "min_price_sqft": live_min_sqft,
                "max_price_sqft": live_max_sqft,
                "simulated_daily_volume": volume,
                "gaining_localities_count": gaining_cnt,
                "softening_localities_count": softening_cnt,
                "locality_snapshots": [dict(s) for s in snapshots],
                "feed_status": "Controlled Simulated Feed",
                "disclaimer": "Simulated market movements represent synthetic liquidity fluctuations and do not modify underlying property records or ML weights."
            }

    def trigger_simulation_tick(self) -> Dict[str, Any]:
        """
        Executes a controlled simulation tick:
        1. Reads the latest indicative price per sqft for each locality
        2. Applies a bounded, plausible small movement: random.uniform(-0.45%, +0.55%)
        3. Updates demand activity index with mean-reversion around 75
        4. Writes a new snapshot record with the current timestamp
        5. Returns the updated state
        """
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self.loader.get_connection() as conn:
            localities = conn.execute("SELECT locality_id, locality_name, avg_price_sqft FROM localities").fetchall()

            for loc in localities:
                loc_id = loc["locality_id"]
                loc_name = loc["locality_name"]
                base_sqft = float(loc["avg_price_sqft"])

                # Get previous snapshot for this locality if exists
                prev = conn.execute(
                    "SELECT indicative_avg_price_sqft, demand_activity_index FROM market_snapshots WHERE locality_id = ? ORDER BY snapshot_id DESC LIMIT 1",
                    (loc_id,)
                ).fetchone()

                if prev:
                    prev_indicative = float(prev["indicative_avg_price_sqft"])
                    prev_demand = float(prev["demand_activity_index"])
                else:
                    prev_indicative = base_sqft
                    prev_demand = 75.0

                # Bounded drift between -0.4% and +0.5%
                daily_drift_pct = round(random.uniform(-0.35, 0.45), 2)
                new_indicative = round(prev_indicative * (1.0 + daily_drift_pct / 100.0), 2)

                # Mean-reverting demand index (60 to 95)
                demand_delta = random.uniform(-3.0, 3.0) + (75.0 - prev_demand) * 0.1
                new_demand = round(max(55.0, min(95.0, prev_demand + demand_delta)), 1)
                sim_volume = random.randint(15, 55)

                conn.execute("""
                INSERT INTO market_snapshots (
                    timestamp, locality_id, locality_name, indicative_avg_price_sqft,
                    daily_change_pct, demand_activity_index, simulated_volume_indicator, snapshot_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Simulated Market Feed')
                """, (
                    now_ts, loc_id, loc_name, new_indicative,
                    daily_drift_pct, new_demand, sim_volume
                ))

            # Prune old records to maintain lean performance during recurring 5s feeds
            conn.execute("""
            DELETE FROM market_snapshots 
            WHERE snapshot_id < (
                SELECT COALESCE(MIN(snapshot_id), 0) FROM (
                    SELECT snapshot_id FROM market_snapshots ORDER BY snapshot_id DESC LIMIT 500
                )
            )
            """)
            conn.commit()

        return self.get_latest_market_snapshot()


if __name__ == "__main__":
    simulator = MarketSimulator()
    print("Latest snapshot before tick:", simulator.get_latest_market_snapshot()["timestamp"])
    new_snap = simulator.trigger_simulation_tick()
    print("Triggered simulation tick! New snapshot timestamp:", new_snap["timestamp"])
    print("Localities simulated:", len(new_snap["locality_snapshots"]))
