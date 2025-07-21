import pandas as pd
from sqlalchemy import create_engine
import os

# Path to your CSV file (adjust if needed)
csv_path = "Manual_Stock_Data_Inserts.csv"

# SQLite DB path (same as session.py)
db_url = "sqlite:///stock_data.db"
engine = create_engine(db_url)

# Load CSV into DataFrame
df = pd.read_csv(csv_path)

# Insert all rows safely into the stock_data table
df.to_sql("stock_data", con=engine, if_exists="append", index=False)

print("✅ All rows inserted from CSV into stock_data table.")
