"""
PropertyIQ Map Data Service
Prepares GeoJSON / marker structures for Leaflet.js interactive maps.
Supports full-size map explorer filtering and compact property detail amenity maps.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.schema import get_db_connection
from src.data_loader import DataLoader
from src.prediction import format_inr


class MapDataService:
    """Prepares map points, coordinates, and filters for OpenStreetMap / Leaflet."""

    def __init__(self):
        self.loader = DataLoader()

    def get_map_properties(
        self,
        locality_id: Optional[str] = None,
        bhk: Optional[int] = None,
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 1500
    ) -> Dict[str, Any]:
        """
        Retrieves property markers matching filters.
        Returns GeoJSON-compatible points list and metadata count.
        """
        conditions = ["1=1"]
        params = []

        if locality_id:
            conditions.append("locality_id = ?")
            params.append(locality_id)

        if bhk:
            conditions.append("bhk = ?")
            params.append(bhk)

        if property_type:
            conditions.append("property_type = ?")
            params.append(property_type)

        if min_price:
            conditions.append("actual_price_inr >= ?")
            params.append(min_price)

        if max_price:
            conditions.append("actual_price_inr <= ?")
            params.append(max_price)

        sql = f"""
        SELECT property_id, property_name, address, locality_id, locality_name, city,
               latitude, longitude, property_type, built_up_area, bhk, bathrooms,
               floor_no, total_floors, furnishing_status, actual_price_inr, price_per_sqft,
               data_status
        FROM properties
        WHERE {" AND ".join(conditions)}
        ORDER BY actual_price_inr DESC
        LIMIT ?
        """
        params.append(limit)

        conn = self.loader.get_connection()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()

        markers = []
        for r in rows:
            markers.append({
                "property_id": r["property_id"],
                "property_name": r["property_name"],
                "address": r["address"],
                "locality_name": r["locality_name"],
                "locality_id": r["locality_id"],
                "city": r["city"],
                "lat": r["latitude"],
                "lng": r["longitude"],
                "property_type": r["property_type"],
                "built_up_area": r["built_up_area"],
                "bhk": r["bhk"],
                "bathrooms": r["bathrooms"],
                "floor_no": r["floor_no"],
                "price_inr": r["actual_price_inr"],
                "price_formatted": format_inr(r["actual_price_inr"]),
                "price_per_sqft": r["price_per_sqft"],
                "data_status": r["data_status"]
            })

        return {
            "total_count": len(markers),
            "markers": markers,
            "center": {"lat": 19.1200, "lng": 72.8800},
            "zoom": 11
        }

    def get_property_location_context(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves compact map coordinates for a specific property,
        along with nearby amenities and infrastructure projects within its locality.
        """
        conn = self.loader.get_connection()
        try:
            prop = conn.execute("SELECT * FROM properties WHERE property_id = ?", (property_id,)).fetchone()
            if not prop:
                return None

            prop_dict = dict(prop)
            prop_dict["price_formatted"] = format_inr(prop_dict["actual_price_inr"])

            # Locality center and bounds
            loc = conn.execute("SELECT * FROM localities WHERE locality_id = ?", (prop_dict["locality_id"],)).fetchone()
            loc_dict = dict(loc) if loc else {}

            # Nearby amenities
            amenities = conn.execute(
                "SELECT * FROM amenities WHERE locality_id = ? ORDER BY rating DESC",
                (prop_dict["locality_id"],)
            ).fetchall()

            # Nearby projects
            projects = conn.execute(
                "SELECT * FROM development_projects WHERE locality_id = ?",
                (prop_dict["locality_id"],)
            ).fetchall()

            return {
                "property": prop_dict,
                "locality": loc_dict,
                "amenities": [dict(a) for a in amenities],
                "projects": [dict(p) for p in projects],
                "map_focus": {
                    "lat": prop_dict["latitude"],
                    "lng": prop_dict["longitude"],
                    "zoom": 14
                }
            }
        finally:
            conn.close()


if __name__ == "__main__":
    service = MapDataService()
    res = service.get_map_properties(limit=5)
    print("Found markers:", res["total_count"])
    context = service.get_property_location_context("PROP-0001")
    print("Property context:", context["property"]["property_name"] if context else "None")
