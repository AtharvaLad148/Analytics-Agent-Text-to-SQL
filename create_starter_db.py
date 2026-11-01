"""Generate a tiny e-commerce DuckDB to develop the agent against.
Deterministic (fixed seed) so results are reproducible for the eval harness.
Swap this out for a real dataset later; the agent code does not change.
"""
import random
import datetime as dt
from pathlib import Path

import duckdb
import pandas as pd

random.seed(42)

DB_PATH = Path(__file__).parent / "data" / "starter.duckdb"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
if DB_PATH.exists():
    DB_PATH.unlink()

cities = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Pune", "Chennai", "Kolkata"]
segments = ["new", "regular", "premium"]
categories = {
    "Electronics": (1500, 60000),
    "Fashion": (300, 5000),
    "Home": (200, 8000),
    "Beauty": (150, 3000),
    "Grocery": (50, 1200),
}

# customers
n_customers = 300
customers = []
for i in range(1, n_customers + 1):
    signup = dt.date(2024, 1, 1) + dt.timedelta(days=random.randint(0, 540))
    customers.append({
        "customer_id": i,
        "name": f"Customer {i}",
        "city": random.choice(cities),
        "segment": random.choices(segments, weights=[0.5, 0.35, 0.15])[0],
        "signup_date": signup,
    })
df_customers = pd.DataFrame(customers)

# products
products = []
pid = 1
for cat, (lo, hi) in categories.items():
    for j in range(1, 13):
        products.append({
            "product_id": pid,
            "product_name": f"{cat} Item {j}",
            "category": cat,
            "price": round(random.uniform(lo, hi), 2),
        })
        pid += 1
df_products = pd.DataFrame(products)

# orders + order_items
orders, items = [], []
oid, oiid = 1, 1
statuses = ["completed", "completed", "completed", "cancelled", "returned"]
for _ in range(1500):
    cust = random.randint(1, n_customers)
    odate = dt.date(2024, 1, 1) + dt.timedelta(days=random.randint(0, 600))
    status = random.choice(statuses)
    orders.append({
        "order_id": oid,
        "customer_id": cust,
        "order_date": odate,
        "status": status,
    })
    for _ in range(random.randint(1, 4)):
        prod = df_products.sample(1).iloc[0]
        items.append({
            "order_item_id": oiid,
            "order_id": oid,
            "product_id": int(prod["product_id"]),
            "quantity": random.randint(1, 3),
            "item_price": float(prod["price"]),
        })
        oiid += 1
    oid += 1
df_orders = pd.DataFrame(orders)
df_items = pd.DataFrame(items)

con = duckdb.connect(str(DB_PATH))
for name, df in [("customers", df_customers), ("products", df_products),
                 ("orders", df_orders), ("order_items", df_items)]:
    con.register("tmp_df", df)
    con.execute(f"CREATE TABLE {name} AS SELECT * FROM tmp_df")
    con.unregister("tmp_df")
con.close()
print(f"Created {DB_PATH}")
print("Tables: customers, products, orders, order_items")
