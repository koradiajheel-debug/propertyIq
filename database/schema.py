"""
PropertyIQ Database Schema
Provides table creation, index definitions, and database connection utilities for SQLite.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional

DB_DIR = Path(__file__).resolve().parent
DB_PATH = DB_DIR / "propertyiq.db"


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Return an active connection to the SQLite database with Row factory."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize all tables, constraints, and indexes in SQLite."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    -- 1. LOCALITIES TABLE
    CREATE TABLE IF NOT EXISTS localities (
        locality_id TEXT PRIMARY KEY,
        locality_name TEXT NOT NULL UNIQUE,
        city TEXT NOT NULL,
        zone TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        population INTEGER NOT NULL,
        population_density REAL NOT NULL,
        avg_household_income_lakhs REAL NOT NULL,
        socioeconomic_tier TEXT NOT NULL,
        avg_price_sqft REAL NOT NULL,
        median_price_sqft REAL NOT NULL,
        yoy_price_change_pct REAL NOT NULL,
        historical_cagr_5yr REAL NOT NULL,
        transaction_volume INTEGER NOT NULL,
        property_count INTEGER NOT NULL,
        transit_accessibility_score REAL NOT NULL,
        hospital_count INTEGER NOT NULL,
        school_count INTEGER NOT NULL,
        metro_station_count INTEGER NOT NULL,
        railway_station_count INTEGER NOT NULL,
        mall_market_count INTEGER NOT NULL,
        park_count INTEGER NOT NULL,
        infrastructure_rating REAL NOT NULL,
        highway_connectivity TEXT NOT NULL,
        cluster_id INTEGER DEFAULT 0,
        cluster_label TEXT DEFAULT 'Unassigned',
        data_source TEXT DEFAULT 'Demonstration Locality Dataset',
        last_updated TEXT NOT NULL
    );

    -- 2. PROPERTIES TABLE
    CREATE TABLE IF NOT EXISTS properties (
        property_id TEXT PRIMARY KEY,
        property_name TEXT NOT NULL,
        address TEXT NOT NULL,
        locality_id TEXT NOT NULL,
        locality_name TEXT NOT NULL,
        city TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        property_type TEXT NOT NULL,
        built_up_area REAL NOT NULL,
        carpet_area REAL NOT NULL,
        bhk INTEGER NOT NULL,
        bathrooms INTEGER NOT NULL,
        property_age INTEGER NOT NULL,
        floor_no INTEGER NOT NULL,
        total_floors INTEGER NOT NULL,
        furnishing_status TEXT NOT NULL,
        parking_spaces INTEGER NOT NULL,
        parking_type TEXT NOT NULL,
        road_type TEXT NOT NULL,
        highway_distance_km REAL NOT NULL,
        railway_distance_km REAL NOT NULL,
        metro_distance_km REAL NOT NULL,
        hospital_distance_km REAL NOT NULL,
        school_distance_km REAL NOT NULL,
        market_distance_km REAL NOT NULL,
        has_water_supply INTEGER NOT NULL DEFAULT 1,
        has_power_backup INTEGER NOT NULL DEFAULT 1,
        has_piped_gas INTEGER NOT NULL DEFAULT 1,
        has_underground_drainage INTEGER NOT NULL DEFAULT 1,
        actual_price_inr REAL NOT NULL,
        price_per_sqft REAL NOT NULL,
        historical_reference_price_inr REAL NOT NULL,
        data_source TEXT DEFAULT 'Simulated demonstration record',
        data_status TEXT DEFAULT 'Simulated',
        created_at TEXT NOT NULL,
        FOREIGN KEY (locality_id) REFERENCES localities (locality_id)
    );

    -- 3. AMENITIES TABLE
    CREATE TABLE IF NOT EXISTS amenities (
        amenity_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        locality_id TEXT NOT NULL,
        locality_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        rating REAL NOT NULL DEFAULT 4.2,
        data_status TEXT DEFAULT 'Simulated landmark coordinates',
        FOREIGN KEY (locality_id) REFERENCES localities (locality_id)
    );

    -- 4. HISTORICAL TRANSACTIONS TABLE
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        property_id TEXT,
        locality_id TEXT NOT NULL,
        locality_name TEXT NOT NULL,
        transaction_date TEXT NOT NULL,
        transaction_year INTEGER NOT NULL,
        transaction_quarter TEXT NOT NULL,
        property_type TEXT NOT NULL,
        bhk INTEGER NOT NULL,
        built_up_area REAL NOT NULL,
        transaction_price_inr REAL NOT NULL,
        price_per_sqft REAL NOT NULL,
        transaction_source TEXT DEFAULT 'Historical Registry Simulation',
        data_status TEXT DEFAULT 'Simulated historical record',
        FOREIGN KEY (locality_id) REFERENCES localities (locality_id)
    );

    -- 5. INFRASTRUCTURE & DEVELOPMENT PROJECTS TABLE
    CREATE TABLE IF NOT EXISTS development_projects (
        project_id TEXT PRIMARY KEY,
        project_name TEXT NOT NULL,
        project_type TEXT NOT NULL,
        locality_id TEXT NOT NULL,
        locality_name TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        status TEXT NOT NULL,
        announcement_year INTEGER NOT NULL,
        expected_completion_year INTEGER NOT NULL,
        impact_zone TEXT NOT NULL,
        estimated_budget_cr REAL NOT NULL,
        data_status TEXT DEFAULT 'Regional Infrastructure Project',
        FOREIGN KEY (locality_id) REFERENCES localities (locality_id)
    );

    -- 6. MARKET SNAPSHOTS TABLE (Dynamic Live Simulation Feed)
    CREATE TABLE IF NOT EXISTS market_snapshots (
        snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        locality_id TEXT NOT NULL,
        locality_name TEXT NOT NULL,
        indicative_avg_price_sqft REAL NOT NULL,
        daily_change_pct REAL NOT NULL,
        demand_activity_index REAL NOT NULL,
        simulated_volume_indicator INTEGER NOT NULL,
        snapshot_type TEXT DEFAULT 'Simulated Market Feed',
        FOREIGN KEY (locality_id) REFERENCES localities (locality_id)
    );

    -- 7. MODEL EVALUATION & METADATA TABLE
    CREATE TABLE IF NOT EXISTS model_metadata (
        model_id TEXT PRIMARY KEY,
        algorithm_name TEXT NOT NULL,
        version TEXT NOT NULL,
        training_date TEXT NOT NULL,
        mae_inr REAL NOT NULL,
        rmse_inr REAL NOT NULL,
        r2_score REAL NOT NULL,
        train_samples INTEGER NOT NULL,
        test_samples INTEGER NOT NULL,
        features_used TEXT NOT NULL,
        is_best_model INTEGER NOT NULL DEFAULT 0,
        pipeline_path TEXT NOT NULL
    );

    -- INDEXES FOR INSTANT RETRIEVAL
    CREATE INDEX IF NOT EXISTS idx_properties_locality ON properties(locality_id);
    CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(property_type);
    CREATE INDEX IF NOT EXISTS idx_properties_bhk ON properties(bhk);
    CREATE INDEX IF NOT EXISTS idx_properties_price ON properties(actual_price_inr);
    CREATE INDEX IF NOT EXISTS idx_transactions_locality ON transactions(locality_id);
    CREATE INDEX IF NOT EXISTS idx_transactions_year ON transactions(transaction_year);
    CREATE INDEX IF NOT EXISTS idx_amenities_locality ON amenities(locality_id);
    CREATE INDEX IF NOT EXISTS idx_market_snapshots_locality ON market_snapshots(locality_id, timestamp);
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
