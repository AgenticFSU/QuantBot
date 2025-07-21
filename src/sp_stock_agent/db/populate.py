from datetime import date
from models import StockData, Base
from session import engine, Session

# Create table (run once)
Base.metadata.create_all(engine)

def insert_prediction(prediction_dict):
    session = Session()
    try:
        entry = StockData(**prediction_dict)
        session.add(entry)
        session.commit()
        print("Inserted:", prediction_dict['ticker'])
    except Exception as e:
        print("Error:", e)
        session.rollback()
    finally:
        session.close()
