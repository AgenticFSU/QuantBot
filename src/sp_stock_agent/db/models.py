from sqlalchemy import Column, String, Float, Date, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class StockData(Base):
    __tablename__ = 'stock_data'
    
    ticker = Column(String(10), primary_key=True)           # e.g., "AAPL"
    date = Column(Date, nullable=False, primary_key=True)   # e.g., 2025-07-17
    company_name = Column(String(100), nullable=False)      # e.g., "Apple Inc."
    industry = Column(String(30), nullable=True)            # e.g., "Technology"
    market_cap = Column(Float, nullable=True)               # e.g., 2.8e12
    price = Column(Float, nullable=True)                    # e.g., yesterday’s price
    volume = Column(Float, nullable=True)                   # e.g., 45000000
    summary = Column(Text, nullable=True)                   # e.g., brief reasoning, news summary
    todays_prediction = Column(String(50), nullable=False)  # e.g., "Buy", "Hold", "Avoid"
    todays_price = Column(Float, nullable=True)             # e.g., predicted price

    def __repr__(self):
        return (
            f"<StockData(ticker={self.ticker}, date={self.date}, "
            f"company_name={self.company_name}, industry={self.industry}, "
            f"market_cap={self.market_cap}, price={self.price}, volume={self.volume}, "
            f"summary={self.summary}, todays_prediction={self.todays_prediction}, "
            f"todays_price={self.todays_price})>"
        )
