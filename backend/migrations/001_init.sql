-- Initial database setup for AI-Tourist

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- POIs table will be created by SQLAlchemy on startup
-- This file is for any additional setup needed

CREATE INDEX IF NOT EXISTS idx_pois_category ON pois(category);
CREATE INDEX IF NOT EXISTS idx_pois_location ON pois(lat, lon);