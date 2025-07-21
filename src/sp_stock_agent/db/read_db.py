import pandas as pd
from sqlalchemy import create_engine

# Same path you used in session.py
db_url = "sqlite:///stock_data.db"
engine = create_engine(db_url)

# Load all records from the stock_data table
df = pd.read_sql("SELECT * FROM stock_data", con=engine)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
# Display the first few rows
print(df.head())
