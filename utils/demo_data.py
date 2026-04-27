import pandas as pd
import numpy as np

DEMO_DATASETS = {
    "🛒 Retail Sales (Superstore)": "retail",
    "👥 HR Attrition (IBM)": "hr",
    "🚕 NYC Taxi Trips (Sample)": "taxi",
    "🌍 World Health Indicators": "health",
}


def load_demo(key: str) -> pd.DataFrame:
    np.random.seed(42)
    n = 500
    if key == "retail":
        return _retail(n)
    elif key == "hr":
        return _hr(n)
    elif key == "taxi":
        return _taxi(n)
    elif key == "health":
        return _health()
    return pd.DataFrame()


def _obj(lst):
    """Force object dtype by returning a plain Python list."""
    return list(lst)


def _retail(n):
    categories = ["Furniture", "Technology", "Office Supplies", "furniture", "TECHNOLOGY"]
    regions = ["East", "West", "South", "Central", "east", "WEST"]
    order_dates = pd.date_range("2022-01-01", periods=n, freq="D").strftime("%Y-%m-%d").tolist()
    ship_dates = [
        "2025-08-15" if i % 50 == 0
        else str((pd.Timestamp("2022-01-01") + pd.Timedelta(days=i + 3)).date())
        for i in range(n)
    ]
    sales = _obj([round(np.random.uniform(10, 5000), 2) if i % 40 != 0 else -99.99 for i in range(n)])
    df = pd.DataFrame({
        "order_id":     _obj([f"ORD-{i:04d}" if i % 30 != 0 else f"ORD-{i-1:04d}" for i in range(n)]),
        "order_date":   order_dates,
        "ship_date":    ship_dates,
        "customer_id":  _obj([f"CUST-{np.random.randint(1, 100):03d}" for _ in range(n)]),
        "category":     _obj(np.random.choice(categories, n)),
        "sub_category": _obj(np.random.choice(["Chairs", "Phones", "Binders", None, "Chairs"], n)),
        "sales":        sales,
        "quantity":     _obj(np.random.randint(1, 20, n)),
        "discount":     _obj([round(np.random.uniform(0, 0.5), 2) if i % 25 != 0 else None for i in range(n)]),
        "profit":       _obj([round(np.random.uniform(-200, 1000), 2) for _ in range(n)]),
        "region":       _obj(np.random.choice(regions, n)),
        "postal_code":  _obj([str(np.random.randint(10000, 99999)) if i % 20 != 0 else f"0{np.random.randint(1000,9999)}" for i in range(n)]),
        "notes":        [None] * n,
        "Unnamed: 0":   list(range(n)),
    })
    dupes = df.iloc[:5].copy()
    df = pd.concat([df, dupes], ignore_index=True)
    df.at[10, "sales"] = "#NULL!"
    df.at[20, "sales"] = "#REF!"
    df.at[5,  "order_date"] = "15/03/2022"
    df.at[15, "order_date"] = "March 3, 2022"
    return df


def _hr(n):
    departments = ["Sales", "R&D", "HR", "sales", "R&d", "hr"]
    education   = ["Bachelor", "Master", "PhD", "bachelor's", "MASTER", "phd"]
    gender      = ["Male", "Female", "male", "M", "F", "FEMALE", "female"]
    df = pd.DataFrame({
        "employee_id":        _obj([f"EMP{i:04d}" if i % 40 != 0 else f"EMP{i-1:04d}" for i in range(n)]),
        "age":                _obj([np.random.randint(22, 60) if i % 35 != 0 else 150 for i in range(n)]),
        "gender":             _obj(np.random.choice(gender, n)),
        "department":         _obj(np.random.choice(departments, n)),
        "education":          _obj(np.random.choice(education, n)),
        "monthly_income":     _obj([np.random.randint(2000, 20000) if i % 45 != 0 else None for i in range(n)]),
        "years_at_company":   _obj([np.random.randint(0, 35) if i % 30 != 0 else -5 for i in range(n)]),
        "job_satisfaction":   _obj(np.random.randint(1, 5, n)),
        "attrition":          _obj(np.random.choice(["Yes", "No", "yes", "NO", "1", "0"], n)),
        "over_time":          _obj(np.random.choice(["Yes", "No", "YES", "no"], n)),
        "performance_rating": _obj(np.random.randint(1, 5, n)),
        "job_level":          _obj(np.random.randint(1, 6, n)),
        "phone":              _obj([f"555-{np.random.randint(1000,9999)}" if i % 15 != 0 else "not provided" for i in range(n)]),
        "email":              _obj([f"emp{i}@company.com" if i % 20 != 0 else "invalid-email" for i in range(n)]),
        "currency":           ["USD"] * n,
    })
    for i in range(50):
        df.at[i, "monthly_income"] = None
    return df


def _taxi(n):
    pickup_times  = pd.date_range("2023-01-01", periods=n, freq="30min").strftime("%Y-%m-%d %H:%M:%S").tolist()
    dropoff_times = pd.date_range("2023-01-01 00:25:00", periods=n, freq="30min").strftime("%Y-%m-%d %H:%M:%S").tolist()
    fare_amounts  = _obj([round(np.random.uniform(3, 80), 2) if i % 30 != 0 else -15.50 for i in range(n)])
    df = pd.DataFrame({
        "trip_id":            list(range(n)),
        "pickup_datetime":    pickup_times,
        "dropoff_datetime":   dropoff_times,
        "passenger_count":    _obj([np.random.randint(1, 6) if i % 20 != 0 else 0 for i in range(n)]),
        "trip_distance":      _obj([round(np.random.uniform(0.5, 30), 2) if i % 25 != 0 else -1.0 for i in range(n)]),
        "fare_amount":        fare_amounts,
        "tip_amount":         _obj([round(np.random.uniform(0, 20), 2) if i % 10 != 0 else None for i in range(n)]),
        "total_amount":       _obj([round(np.random.uniform(5, 100), 2) for _ in range(n)]),
        "payment_type":       _obj(np.random.choice(["Credit Card", "Cash", "credit card", "CASH", "1", "2"], n)),
        "pickup_location":    _obj(np.random.choice(["Manhattan", "Brooklyn", "Queens", "Bronx", None], n)),
        "dropoff_location":   _obj(np.random.choice(["Manhattan", "Brooklyn", "Queens", "Bronx", None], n)),
        "vendor_id":          _obj(np.random.choice([1, 2, None], n)),
        "store_and_fwd_flag": ["Y"] * n,
    })
    df.at[5,  "fare_amount"]     = "CORRUPT"
    df.at[15, "pickup_datetime"] = "not a date"
    dupes = df.iloc[:3].copy()
    df = pd.concat([df, dupes], ignore_index=True)
    return df


def _health():
    countries = [
        "United States", "USA", "U.S.A", "United States of America",
        "United Kingdom", "UK", "U.K.", "Britain",
        "Germany", "Deutschland", "India", "China", "PRC",
        "France", "Brasil", "Brazil",
    ] * 32
    np.random.shuffle(countries)
    n = len(countries)
    gdp      = _obj([round(np.random.uniform(500, 65000), 2) if i % 15 != 0 else None for i in range(n)])
    life_exp = _obj([round(np.random.uniform(55, 85), 1)    if i % 20 != 0 else None for i in range(n)])
    df = pd.DataFrame({
        "country":                _obj(countries[:n]),
        "year":                   _obj(np.random.choice([2018, 2019, 2020, 2021, 2022], n)),
        "life_expectancy":        life_exp,
        "gdp_per_capita":         gdp,
        "infant_mortality":       _obj([round(np.random.uniform(2, 60), 2) if i % 25 != 0 else -1.0 for i in range(n)]),
        "hospital_beds_per_1000": _obj([round(np.random.uniform(0.5, 14), 2) if i % 30 != 0 else None for i in range(n)]),
        "physicians_per_1000":    _obj([round(np.random.uniform(0.1, 5), 2) for _ in range(n)]),
        "population_millions":    _obj([round(np.random.uniform(1, 1400), 2) for _ in range(n)]),
        "region":                 _obj(np.random.choice(["Asia", "Europe", "Americas", "Africa", "Oceania", "asia", "EUROPE"], n)),
        "data_source":            ["WHO"] * n,
        "notes":                  [None] * n,
        "Unnamed: 0":             list(range(n)),
    })
    df.at[10, "life_expectancy"] = 999
    df.at[20, "gdp_per_capita"]  = "$45,000"
    return df
