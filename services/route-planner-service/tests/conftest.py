import os
import sys
from pathlib import Path

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TWOGIS_API_KEY", "test-twogis-key")
os.environ.setdefault("NAVITIA_API_KEY", "test-navitia-key")

ROOT_DIR = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT_DIR / "services" / "route-planner-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))
