from sqlalchemy import Column, Integer, String, Float, ARRAY, Text, Time
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class POI(Base):
    __tablename__ = "pois"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    tags = Column(ARRAY(String), default=[])
    description = Column(Text)
    avg_visit_minutes = Column(Integer, default=30)
    rating = Column(Float, default=0.0)
    embedding = Column(ARRAY(Float))
    local_tip = Column(Text)
    photo_tip = Column(Text)
    address = Column(String)
    social_mode = Column(String, default="any")
    intensity_level = Column(String, default="medium")
    open_time = Column(Time)
    close_time = Column(Time)