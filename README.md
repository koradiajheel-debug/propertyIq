# PropertyIQ — Property Valuation & Real-Time Locality Intelligence System

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Scikit--Learn](https://img.shields.io/badge/Scikit--Learn-1.5+-F7931E.svg)](https://scikit-learn.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-199900.svg)](https://leafletjs.com/)
[![License: Academic](https://img.shields.io/badge/Academic-Diploma%20CSE-green.svg)](#)

**PropertyIQ** is an academic Machine Learning and full-stack locality intelligence platform built specifically according to the **Diploma in Computer Science Engineering syllabus**. It estimates residential property values using genuinely trained regression models and delivers neighbourhood demographics, historical price appreciation, transit connectivity, infrastructure projects, and geospatial mapping across the **Mumbai & Mumbai Metropolitan Region (MMR)**.

---

## 🏛️ Academic Machine Learning Syllabus Compliance

In strict adherence to syllabus boundaries:
- **Permitted Algorithms Only**:
  1. `Linear Regression` (`sklearn.linear_model.LinearRegression`)
  2. `Decision Tree Regressor` (`sklearn.tree.DecisionTreeRegressor`)
  3. `Random Forest Regressor` (`sklearn.ensemble.RandomForestRegressor` — Bagging Ensemble)
  4. `K-Means Clustering` (`sklearn.cluster.KMeans` — Unsupervised Locality Grouping)
- **Permitted Data Science Libraries**: `NumPy`, `Pandas`, `Matplotlib`, `Seaborn`, `Scikit-learn`, `SciPy`.
- **Zero Black-Box APIs**: Strictly no neural networks, XGBoost, LightGBM, or LLM-generated prices.
- **Zero Manual User Data Entry**: Users search and select from 1,250 pre-populated properties and 14 localities.

---

## 🚀 Quick Start Guide

### 1. Requirements & Prerequisites
Ensure Python 3.10+ is installed:
```powershell
python --version
pip --version
```

### 2. Installation
Navigate to the project directory:
```powershell
cd C:\Users\Admin\.gemini\antigravity-ide\scratch\propertyiq
pip install -r requirements.txt
```

### 3. Automatic Initialization & Launch
PropertyIQ features self-initialization. If the SQLite database or trained models are missing, it seeds the data and fits the ML models on startup:
```powershell
python app.py
```
Or start via Uvicorn directly:
```powershell
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to access the live dashboard.

---

## 🧪 Running Automated Unit Tests
A test suite covering database integrity, foreign keys, model evaluation, What-If sensitivity, and YoY growth calculations is provided:
```powershell
python -m unittest tests/test_propertyiq.py
```

---

## 🗄️ Project Architecture & Directory Structure

```text
propertyiq/
├── app.py                     # FastAPI REST API server & static HTML router
├── requirements.txt           # Syllabus-compliant Python dependencies
├── .env.example               # Environment variables template
├── README.md                  # Comprehensive documentation and viva guide
├── database/
│   ├── schema.py              # SQLite schema, tables, foreign keys, and indexes
│   ├── seed_database.py       # Seed engine: 1,250 properties, 14 localities, 3,699 txns
│   └── propertyiq.db          # Persisted SQLite database
├── data/                      # Exported companion CSV datasets
│   ├── properties.csv
│   ├── localities.csv
│   ├── transactions.csv
│   ├── amenities.csv
│   └── development_projects.csv
├── src/
│   ├── data_loader.py         # Thread-safe queries and DataFrame loaders
│   ├── data_cleaning.py       # Imputation, range assertions, and schema sanitization
│   ├── feature_engineering.py # ColumnTransformer: StandardScaler + OneHotEncoder
│   ├── model_training.py      # 80/20 train-test split, model fitting, and evaluation
│   ├── prediction.py          # ValuationEngine and What-If scenario sensitivity
│   ├── model_evaluation.py    # Formal MAE, RMSE, and R² calculations
│   ├── locality_analysis.py   # Locality profiles and multi-locality comparison
│   ├── clustering.py          # K-Means clustering with standardized centroids
│   ├── transaction_analysis.py# Historical yearly trends and YoY Growth %
│   ├── market_simulation.py   # Controlled bounded dynamic feed simulator
│   ├── map_data.py            # GeoJSON marker clustering service for Leaflet
│   └── reporting.py           # Matplotlib & Seaborn analytical chart generator
├── models/                    # Serialized model artifacts (.joblib) & metrics.json
│   ├── preprocessor.joblib
│   ├── linear_regression.joblib
│   ├── decision_tree.joblib
│   ├── random_forest.joblib
│   ├── best_model.joblib
│   ├── kmeans.joblib
│   ├── kmeans_scaler.joblib
│   └── metrics.json
├── static/
│   ├── css/styles.css         # Modern styling, responsive cards, dark/light accents
│   └── js/app.js              # Leaflet integration, tab controller, What-If reactivity
├── templates/
│   └── index.html             # Single-page interface with 8 functional intelligence tabs
└── tests/
    └── test_propertyiq.py     # 10 automated unit and integration tests
```

---

## 📊 Technical Explanation for College Practical / Viva

### 1. Database Population & Data Provenance
- **Localities**: 14 micromarkets across Mumbai and MMR (`Bandra West`, `Worli`, `Dadar West`, `Powai`, `Andheri West`, `Goregaon East`, `Andheri East`, `Malad West`, `Borivali West`, `Kandivali East`, `Kurla West`, `Vashi`, `Thane West`, `Kharghar`).
- **Residential Properties**: 1,250 distinct properties distributed proportionally. Each record contains built-up area, carpet area, BHK, bathrooms, age, floor, parking, road type, transit distances (metro, railway, highway), and utility availability.
- **Amenities**: 63 realistic landmarks (e.g. Kokilaben Hospital, Lilavati Hospital, IIT Bombay, Inorbit Mall, Akurli Metro Station).
- **Infrastructure Projects**: 8 regional projects (Mumbai Coastal Road, Metro Line 3 Aqua Line, MTHL Atal Setu, GMLR Tunnel, Navi Mumbai Airport).
- **Historical Transactions**: 3,699 transaction records from 2021 to 2026.
- **Data Provenance Disclosure**: Property units and transactions are simulated demonstration records with mathematical internal consistency. Landmarks and regional transit projects reflect genuine Mumbai geography.

### 2. Feature Engineering & Preprocessing Pipeline
To prevent **Data Leakage**, preprocessing is fit strictly on the 80% training set (1,000 records) and applied to the 20% test set (250 records):
- **Continuous Features**: Scaled using `StandardScaler` to zero mean and unit variance ($\mu=0, \sigma=1$).
- **Engineered Ratios**:
  $$\text{Carpet Ratio} = \frac{\text{Carpet Area}}{\text{Built-up Area}}$$
  $$\text{Floor Ratio} = \frac{\text{Floor Number}}{\text{Total Floors}}$$
- **Categorical Features**: Encoded using `OneHotEncoder(handle_unknown='ignore', sparse_output=False)` for `locality_name`, `property_type`, `furnishing_status`, `road_type`, and `parking_type`.

### 3. Machine Learning Model Training & Evaluation Metrics
All 3 permitted regression models were evaluated on the identical held-out test partition (250 samples):

| Algorithm | Syllabus Category | Test $R^2$ Score | Test MAE (₹ Lakhs) | Test RMSE (₹ Lakhs) | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Linear Regression** | Parametric Linear | `0.8554` | ₹121.47 L | ₹191.67 L | Baseline |
| **Decision Tree Regressor** | Non-Parametric Trees | `0.9145` | ₹70.17 L | ₹147.33 L | Strong |
| **Random Forest Regressor** | Bagging Ensemble | **`0.9527`** | **₹58.23 L** | **₹109.61 L** | **Best Model** |

#### Formal Metric Definitions:
1. **Mean Absolute Error (MAE)**:
   $$\text{MAE} = \frac{1}{n}\sum_{i=1}^{n}|y_i - \hat{y}_i|$$
   Represents the average rupee deviation between predicted and actual transaction values.
2. **Root Mean Squared Error (RMSE)**:
   $$\text{RMSE} = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2}$$
   Penalizes large outlier estimation errors heavily because residuals are squared before averaging.
3. **Coefficient of Determination ($R^2$)**:
   $$R^2 = 1 - \frac{\sum_{i=1}^{n}(y_i - \hat{y}_i)^2}{\sum_{i=1}^{n}(y_i - \bar{y})^2}$$
   Indicates that **95.3% of the variance** in residential property prices across MMR is explained by physical dimensions, location, amenities, and transit distances.

### 4. Unsupervised K-Means Locality Clustering
Localities are clustered based on 5 standardized attributes: `avg_price_sqft`, `population_density`, `historical_cagr_5yr`, `transit_accessibility_score`, and `infrastructure_rating`.
- Feature standardization via `StandardScaler` is mandatory because Price/sqft (~₹50,000) and Transit Score (0-10) operate on wildly different magnitudes.
- Results group localities into 4 distinct clusters:
  - **Cluster 0**: Established Suburban Family Residential (Powai, Goregaon East, Vashi, Thane, Kharghar)
  - **Cluster 1**: Prime High-Density Commercial Nodes (Dadar West, Andheri West, Andheri East, Kurla West)
  - **Cluster 2**: Ultra-Premium Waterfront & Heritage Hubs (Bandra West, Worli)
  - **Cluster 3**: Established Western Suburbs (Borivali West, Malad West, Kandivali East)

### 5. Year-on-Year (YoY) Growth Calculation
Historical appreciation is computed via the strict formula:
$$\text{YoY Growth (\%)} = \left(\frac{\text{Current Comparable Avg Price} - \text{Previous Comparable Avg Price}}{\text{Previous Comparable Avg Price}}\right) \times 100$$

### 6. Controlled Market Simulation vs ML Valuation
- **Live Market Feed**: Maintains a separate `market_snapshots` table with small bounded daily price drifts ($\pm 0.1\% \text{ to } 0.6\%$) and liquidity demand indices (55–95).
- **ML Valuation**: Uses the static fitted weights of the trained Scikit-learn model.
- **Immutability Guarantee**: Simulation ticks **never** modify historical transaction tables and **never** retrain or distort the ML model.

### 7. Interactive What-If Scenario Analysis
Users can adjust built-up area, BHK, age, parking, or furnishing on any selected property. The scenario is evaluated through the fitted pipeline to display original valuation vs scenario valuation, absolute difference, and percentage delta without mutating the database record.

---

## 🔌 Connecting Genuine Real-World Data Later
To connect real-world transaction feeds (e.g., IGR Maharashtra registration open data or municipal GIS feeds):
1. Replace or supplement CSV files in `data/` (`properties.csv`, `transactions.csv`).
2. Run `python database/seed_database.py` or invoke the admin import script.
3. Execute `python src/model_training.py` to retrain the pipeline on genuine registered deeds.
4. Model metrics will automatically update to reflect real-world validation scores.

---

## ⚖️ Academic Disclaimer
*PropertyIQ is an educational project created for computer science diploma coursework. Property records and transactions are simulated demonstration data with internal mathematical consistency. Predictions demonstrate machine learning workflows and cannot be construed as certified real-estate appraisals or financial advice.*
