import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# SQLite DB path
DB_URL = "sqlite:///stock_data.db"
engine = create_engine(DB_URL, echo=True)
Session = sessionmaker(bind=engine)
