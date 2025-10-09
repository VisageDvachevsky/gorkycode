from datetime import time
from typing import List, Optional
from sqlalchemy import JSON, Float, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class POI(Base):
    __tablename__ = "pois"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(255))
    
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    description: Mapped[str] = mapped_column(Text)
    description_en: Mapped[Optional[str]] = mapped_column(Text)
    
    photo_tip: Mapped[Optional[str]] = mapped_column(Text)
    local_tip: Mapped[Optional[str]] = mapped_column(Text)
    
    avg_visit_minutes: Mapped[int] = mapped_column(Integer, default=30)
    
    open_time: Mapped[Optional[time]] = mapped_column(Time)
    close_time: Mapped[Optional[time]] = mapped_column(Time)
    
    social_mode: Mapped[str] = mapped_column(String(50), default="any")
    intensity_level: Mapped[str] = mapped_column(String(50), default="medium")
    
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON)