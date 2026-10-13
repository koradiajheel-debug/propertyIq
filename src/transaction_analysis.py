"""
PropertyIQ Historical Transaction Analysis Module
Calculates yearly price trends, median prices, price/sqft, transaction volumes,
and formal Year-over-Year (YoY) growth percentages across Mumbai/MMR localities.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.schema import get_db_connection
from src.data_loader import DataLoader


class TransactionAnalyzer:
    """Computes historical market metrics, multi-year appreciation, and transaction aggregations."""

    def __init__(self):
        self.loader = DataLoader()

    def get_yearly_trends(self, locality_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Computes yearly average price, median price, price/sqft, transaction counts,
        and strict YoY Growth %:
        Growth (%) = ((Current Avg Price - Prev Avg Price) / Prev Avg Price) * 100
        """
        with self.loader.get_connection() as conn:
            query = """
            SELECT transaction_year, price_per_sqft, transaction_price_inr, built_up_area
            FROM transactions
            """
            params = ()
            if locality_id:
                query += " WHERE locality_id = ?"
                params = (locality_id,)

            query += " ORDER BY transaction_year ASC"
            df = pd.read_sql_query(query, conn, params=params)

        if df.empty:
            return []

        # Group by year
        grouped = df.groupby("transaction_year").agg(
            avg_price_sqft=("price_per_sqft", "mean"),
            median_price_sqft=("price_per_sqft", "median"),
            avg_price_inr=("transaction_price_inr", "mean"),
            median_price_inr=("transaction_price_inr", "median"),
            volume=("transaction_price_inr", "count")
        ).reset_index()

        results = []
        prev_avg_sqft = None

        for _, row in grouped.iterrows():
            curr_year = int(row["transaction_year"])
            curr_avg_sqft = float(row["avg_price_sqft"])

            # Compute YoY growth %
            if prev_avg_sqft is not None and prev_avg_sqft > 0:
                yoy_growth = round(((curr_avg_sqft - prev_avg_sqft) / prev_avg_sqft) * 100, 2)
            else:
                yoy_growth = None  # First year has no previous comparable year

            prev_avg_sqft = curr_avg_sqft

            results.append({
                "year": curr_year,
                "avg_price_sqft": round(curr_avg_sqft, 2),
                "median_price_sqft": round(float(row["median_price_sqft"]), 2),
                "avg_price_inr": round(float(row["avg_price_inr"]), 2),
                "median_price_inr": round(float(row["median_price_inr"]), 2),
                "transaction_volume": int(row["volume"]),
                "yoy_growth_pct": yoy_growth
            })

        return results

    def get_property_type_breakdown(self, locality_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Averages by property type (Apartment, Penthouse, etc.)."""
        with self.loader.get_connection() as conn:
            query = """
            SELECT property_type, AVG(price_per_sqft) as avg_sqft,
                   AVG(transaction_price_inr) as avg_price, COUNT(*) as count
            FROM transactions
            """
            params = ()
            if locality_id:
                query += " WHERE locality_id = ?"
                params = (locality_id,)
            query += " GROUP BY property_type ORDER BY avg_sqft DESC"
            rows = conn.execute(query, params).fetchall()

        return [
            {
                "property_type": r["property_type"],
                "avg_price_sqft": round(float(r["avg_sqft"]), 2),
                "avg_price_inr": round(float(r["avg_price"]), 2),
                "volume": int(r["count"])
            }
            for r in rows
        ]

    def get_recent_transactions(self, locality_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves raw recent transactions for searchable table views."""
        with self.loader.get_connection() as conn:
            query = "SELECT * FROM transactions"
            params = ()
            if locality_id:
                query += " WHERE locality_id = ?"
                params = (locality_id,)
            query += " ORDER BY transaction_date DESC LIMIT ?"
            params = params + (limit,)
            rows = conn.execute(query, params).fetchall()

        return [dict(r) for r in rows]


if __name__ == "__main__":
    tx_anal = TransactionAnalyzer()
    trends = tx_anal.get_yearly_trends("LOC-ANDW")
    print("Yearly Trends for Andheri West:")
    for t in trends:
        print(f"Year {t['year']}: Avg SqFt ₹{t['avg_price_sqft']}, YoY: {t['yoy_growth_pct']}% (Vol: {t['transaction_volume']})")
