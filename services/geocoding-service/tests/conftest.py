import os
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = SERVICE_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

os.environ.setdefault("TWOGIS_API_KEY", "test-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
