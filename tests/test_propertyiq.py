"""
PropertyIQ Comprehensive Automated Test Suite
Validates database integrity, model training, valuation accuracy,
What-If sensitivity, market simulation immutability, and YoY calculations.
"""

import sys
import unittest
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.schema import get_db_connection, DB_PATH
from src.data_loader import DataLoader
from src.data_cleaning import DataCleaner
from src.feature_engineering import FeatureEngineer
from src.prediction import ValuationEngine, format_inr
from src.market_simulation import MarketSimulator
from src.transaction_analysis import TransactionAnalyzer
from src.map_data import MapDataService
from src.clustering import LocalityClusterer


class TestPropertyIQ(unittest.TestCase):
    """Test suite covering data, ML, simulation, and business logic."""

    @classmethod
    def setUpClass(cls):
        cls.loader = DataLoader()
        cls.engine = ValuationEngine()
        cls.simulator = MarketSimulator()
        cls.tx_analyzer = TransactionAnalyzer()
        cls.map_service = MapDataService()

    def test_database_initialization(self):
        """Verify database tables and minimum record counts."""
        self.assertTrue(DB_PATH.exists(), "Database file must exist")
        with self.loader.get_connection() as conn:
            prop_count = conn.execute("SELECT COUNT(*) FROM properties").fetchone()[0]
            loc_count = conn.execute("SELECT COUNT(*) FROM localities").fetchone()[0]
            txn_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            amn_count = conn.execute("SELECT COUNT(*) FROM amenities").fetchone()[0]

            self.assertGreaterEqual(prop_count, 1000, "Must have at least 1,000 property records")
            self.assertGreaterEqual(loc_count, 14, "Must have at least 14 localities")
            self.assertGreaterEqual(txn_count, 3000, "Must have at least 3,000 historical transactions")
            self.assertGreaterEqual(amn_count, 40, "Must have at least 40 amenities")

    def test_database_foreign_key_relationships(self):
        """Verify relational integrity between properties, transactions, and localities."""
        with self.loader.get_connection() as conn:
            # Check for orphaned properties
            orphaned_props = conn.execute("""
            SELECT COUNT(*) FROM properties
            WHERE locality_id NOT IN (SELECT locality_id FROM localities)
            """).fetchone()[0]
            self.assertEqual(orphaned_props, 0, "No orphaned properties should exist")

            # Check for orphaned transactions
            orphaned_txs = conn.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE locality_id NOT IN (SELECT locality_id FROM localities)
            """).fetchone()[0]
            self.assertEqual(orphaned_txs, 0, "No orphaned transactions should exist")

    def test_data_cleaning_and_feature_engineering(self):
        """Verify feature engineering produces required numerical and categorical features."""
        raw_df = self.loader.load_properties()
        cleaned, report = DataCleaner.clean_property_dataframe(raw_df)
        self.assertEqual(len(cleaned), len(raw_df))

        X, y = FeatureEngineer.prepare_dataset(cleaned)
        self.assertEqual(len(X), len(cleaned))
        self.assertIn("carpet_to_built_ratio", X.columns)
        self.assertIn("floor_ratio", X.columns)
        self.assertTrue((y > 0).all(), "Target prices must all be strictly positive")

    def test_ml_model_artifacts_and_metrics(self):
        """Verify saved models exist and achieve required academic benchmarks."""
        metrics_file = BASE_DIR / "models" / "metrics.json"
        self.assertTrue(metrics_file.exists(), "metrics.json must be saved")

        with open(metrics_file, "r") as f:
            metrics = json.load(f)

        models = metrics.get("models", {})
        self.assertIn("linear_regression", models)
        self.assertIn("decision_tree", models)
        self.assertIn("random_forest", models)

        rf_r2 = models["random_forest"]["r2_score"]
        self.assertGreater(rf_r2, 0.85, "Random Forest test R2 should exceed 0.85")
        self.assertGreater(models["random_forest"]["mae_lakhs"], 0)

    def test_valuation_engine_prediction(self):
        """Verify ML valuation returns formatted price and price/sqft."""
        with self.loader.get_connection() as conn:
            prop = conn.execute("SELECT * FROM properties LIMIT 1").fetchone()
            prop_dict = dict(prop)

        val = self.engine.predict_property(prop_dict)
        self.assertIn("predicted_price_inr", val)
        self.assertIn("predicted_price_formatted", val)
        self.assertIn("predicted_price_per_sqft", val)
        self.assertGreater(val["predicted_price_inr"], 1000000)
        self.assertTrue("₹" in val["predicted_price_formatted"])

    def test_what_if_analysis_immutability(self):
        """Verify What-If sensitivity recalculates without altering underlying DB records."""
        with self.loader.get_connection() as conn:
            prop_before = conn.execute("SELECT * FROM properties WHERE property_id = 'PROP-0001'").fetchone()
            orig_area = prop_before["built_up_area"]
            orig_price = prop_before["actual_price_inr"]

        scenario = self.engine.run_what_if_analysis(
            dict(prop_before),
            {"built_up_area": orig_area + 300, "bhk": prop_before["bhk"] + 1}
        )

        self.assertNotEqual(
            scenario["scenario_valuation"]["predicted_price_inr"],
            scenario["original_valuation"]["predicted_price_inr"]
        )
        self.assertNotEqual(scenario["percentage_difference"], 0.0)

        # Confirm database row was unchanged
        with self.loader.get_connection() as conn:
            prop_after = conn.execute("SELECT * FROM properties WHERE property_id = 'PROP-0001'").fetchone()
            self.assertEqual(prop_after["built_up_area"], orig_area)
            self.assertEqual(prop_after["actual_price_inr"], orig_price)

    def test_market_simulation_consistency(self):
        """Verify simulation tick updates snapshots while leaving historical data immutable."""
        with self.loader.get_connection() as conn:
            tx_count_before = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

        snapshot = self.simulator.trigger_simulation_tick()
        self.assertIn("timestamp", snapshot)
        self.assertGreater(len(snapshot["locality_snapshots"]), 0)

        # Confirm historical transactions remain untouched
        with self.loader.get_connection() as conn:
            tx_count_after = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            self.assertEqual(tx_count_before, tx_count_after, "Historical transactions must remain immutable")

    def test_historical_yoy_growth_formula(self):
        """Verify formal YoY Growth formula calculation on historical data."""
        trends = self.tx_analyzer.get_yearly_trends("LOC-ANDW")
        self.assertGreaterEqual(len(trends), 3)

        # First year baseline should be None
        self.assertIsNone(trends[0]["yoy_growth_pct"])

        # Subsequent years should have non-null growth %
        for i in range(1, len(trends)):
            prev_rate = trends[i - 1]["avg_price_sqft"]
            curr_rate = trends[i]["avg_price_sqft"]
            expected_growth = round(((curr_rate - prev_rate) / prev_rate) * 100, 2)
            self.assertAlmostEqual(trends[i]["yoy_growth_pct"], expected_growth, places=1)

    def test_map_data_service(self):
        """Verify map data service marker counts and bounding ranges."""
        res = self.map_service.get_map_properties()
        self.assertGreaterEqual(res["total_count"], 1000)
        marker = res["markers"][0]
        self.assertTrue(18.9 <= marker["lat"] <= 19.35, "Latitude must be in Mumbai MMR bounds")
        self.assertTrue(72.75 <= marker["lng"] <= 73.15, "Longitude must be in Mumbai MMR bounds")

    def test_kmeans_clustering_assignments(self):
        """Verify all localities have valid K-Means cluster IDs."""
        localities = self.loader.load_localities()
        self.assertTrue((localities["cluster_id"] >= 0).all())
        self.assertTrue((localities["cluster_label"] != "Unassigned").all())


if __name__ == "__main__":
    unittest.main()
